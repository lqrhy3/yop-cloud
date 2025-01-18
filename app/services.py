"""
services.py

This module contains the business logic and service functions for the FastAPI application.
It acts as an intermediary layer between the API routes and the underlying data layer (e.g., database).

Purpose:
--------
The `services.py` file is designed to:
1. Encapsulate business logic and complex operations.
2. Provide reusable functions for API route handlers to reduce redundancy.
3. Interact with database models, third-party APIs, or other external services.
4. Handle error cases, validations, and transformations before returning data to the API layer.

Functions:
----------
This file may include functions such as:
- CRUD operations for interacting with database models.
- Validation or transformation of input and output data.
- Calls to external APIs or services.
- Implementation of core application logic.
"""
import os
import re
import shutil
import psutil
from typing import Annotated

import aiofiles
import asyncio

from fastapi import (
    BackgroundTasks,
    Request,
    HTTPException,
    Depends,
    status,
)

from app import settings
from app.exceptions import FileNotFound
from app.logger import get_logger
from app.models import File, FileType, SIZE_UNITS


logger = get_logger(__name__)


def validate_file_name(file_name: str):
    """
    Validate the uploaded file name to ensure it meets security and naming standards.

    :param file_name: Name of the uploaded file.
    :return:
    """
    pattern = r"^[\w\-. ]+$"

    # Check if the file name is empty or None
    if not file_name:
        raise FileNotFound

    if not re.match(pattern, file_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid file name. Only alphanumeric characters, underscores, hyphens, "
                "dots, and spaces are allowed."
            ),
        )

    # Check for dangerous file names (e.g., path traversal attempts)
    if ".." in file_name or file_name.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file name. Directory traversal is not allowed."
        )


def resolve_paths(file_path: str, is_archive: bool = False) -> tuple[str, str]:
    """
    Create folder structure based on file name.

    :param file_path: File path to create folder structure for.
    :param is_archive: Boolean flag indicating if file is archived.
    :return: tuple[str, str] file_name, dir_path
    """
    dir_path, file_name = os.path.split(file_path)
    dir_path = os.path.join(settings.UPLOAD_DIR, dir_path)
    os.makedirs(os.path.join(dir_path, '' if not is_archive else file_name), exist_ok=True)

    if is_archive:
        file_name = f".{file_name}.tar.gz"

    file_path = os.path.join(dir_path, file_name)
    return file_name, file_path


def clean_file(file_path: str) -> None:
    """
    Deletes a file from disk if it exists.

    :param file_path:
    :return: None
    """
    file_name = os.path.basename(file_path)
    validate_file_name(file_name)

    if not file_path.startswith(settings.UPLOAD_DIR):
        file_path = os.path.join(settings.UPLOAD_DIR, file_path)

    if not os.path.exists(file_path):
        raise FileNotFound

    if os.path.isfile(file_path):
        os.remove(file_path)
        logger.info(f"Removed {file_path}")
    elif os.path.isdir(file_path):
        shutil.rmtree(file_path)
        logger.info(f"Removed {file_path}")
    else:
        logger.info(f"The path '{file_path}' is neither a file nor a directory. What is it?")


async def unzip_folder(path: str) -> tuple[bytes, bytes]:
    """
    Unzip uploaded folder into specified directory.

    :param path: Path to unzip folder.
    :return: tuple[bytes, bytes] stdout and stderr
    """
    parent_dir_path, dir_name = os.path.split(path)
    dir_name = dir_name.replace(".tar.gz", "")[1:]
    dir_path = os.path.join(parent_dir_path, dir_name)

    unzip_command = f"tar -xf {path} -C {dir_path}"

    try:
        unzip_task = await asyncio.create_subprocess_shell(
            cmd=unzip_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await unzip_task.communicate()
        return stdout, stderr
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to unzip uploaded folder.")
    finally:
        clean_file(file_path=path)


def check_disk_space(file_size: int) -> bool:
    """
    Check if there's enough disk space for the upload.
    
    :param file_size: Size of file to be uploaded in bytes
    :return: True if enough space, raises HTTPException if not
    """
    try:
        _, _, free = shutil.disk_usage(settings.UPLOAD_DIR)
        # Keep 1GB buffer space on disk
        buffer_space = 1024 * 1024 * 1024  
        if free - buffer_space < file_size:
            raise HTTPException(
                status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                detail=f"Not enough disk space. Available: {format_file_size(free - buffer_space, human=True)}, "
                       f"Required: {format_file_size(file_size, human=True)}"
            )
        return True
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check disk space"
        )


async def save_file(request: Request, background_tasks: BackgroundTasks) -> str:
    """
    Save file from request stream to disk.

    :param request: FastAPI Request object. See https://fastapi.tiangolo.com/reference/request/#request-class
    :param background_tasks: FastAPI BackgroundTasks object. See https://fastapi.tiangolo.com/tutorial/background-tasks/#using-backgroundtasks
    :return: str: File name of saved file.
    """
    content_disposition = request.headers.get("content-disposition")
    content_length = request.headers.get("content-length")

    if content_disposition is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Content-Disposition header",
        )
    if content_length is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Content-Length header",
        )

    file_size = int(content_length)
    check_disk_space(file_size)

    # Parse filename (assumes standard format)
    file_path = content_disposition.split("filename=")[-1].strip('"')
    file_name = os.path.basename(file_path)
    validate_file_name(file_name)

    # Get archive header
    is_archive = request.headers.get(settings.ARCHIVE_HEADER, "false").lower() == "true"

    # Allocate folders
    file_name, file_path = resolve_paths(file_path, is_archive)

    # Write file directly to disk
    try:
        async with aiofiles.open(file_path, "wb") as f:
            async for chunk in request.stream():
                await f.write(chunk)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="There was an error saving your file.")

    if is_archive:
        background_tasks.add_task(unzip_folder, file_path)
        # stdout, stderr = await unzip_folder(file_path)

        # if stderr:
        #     logger.warning(f"Unzipping failed: {stderr}")
        #     raise HTTPException(
        #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #         detail="Unzipping failed",
        #     )

    return file_name


async def archive_file(file_path: str) -> str:
    """
    Create a .tar.gz archive.

    :param file_path: Path to the source file.
    :return: str: Path to the created archive file.
    """
    file_name = os.path.basename(file_path)
    tmp_archive_path = os.path.join(settings.TMP_DIR, f".{file_name}.tar.gz")
    zip_command = f"tar -cz --no-xattrs -f {tmp_archive_path} "
    
    options = file_path

    if os.path.isdir(file_path):
        options = f"-C {options} ."

    zip_command += options

    try:
        zip_task = await asyncio.create_subprocess_shell(
            cmd=zip_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await zip_task.communicate()

        if stderr:
            logger.warning(f"{zip_command}")
            logger.warning(f"Failed to archive folder: {stderr}")
            raise Exception

    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to zip folder for downloading")

    return file_path


async def download_file(file_name: str, background_tasks: BackgroundTasks) -> str:
    """
    Download a file from our 10TB storage YOP service.

    :param file_name: File to download.
    :param background_tasks: FastAPI BackgroundTasks object. See https://fastapi.tiangolo.com/tutorial/background-tasks/#using-backgroundtasks
    :return: file_path: Path to the downloaded file.
    """
    validate_file_name(file_name)

    file_path = os.path.join(settings.UPLOAD_DIR, file_name)

    if not os.path.exists(file_path):
        raise FileNotFound

    if needs_to_be_archived(file_path):
        file_path = await archive_file(file_path)
        background_tasks.add_task(clean_file, file_path)

    return file_path


def format_file_size(file_size: int, human: bool = False) -> int | str:
    """
    Get size of file in bytes or human readable format.

    :param file_size: Size of file in bytes.
    :param human: Boolean flag indicating if size should be human readable.
    :return: int | str: Size of file in bytes or human readable format.
    """
    if not human:
        return file_size

    i = 0
    while file_size > 1024:
        i += 1
        file_size = file_size / 1024
    return f"{int(file_size) if i == 0 else f"{file_size:.2f}"} {SIZE_UNITS[i]}"


async def ls(file_path: str) -> list[File]:
    """
    Show directory contents.

    :param file_path:
    :return:
    """
    base_path = os.path.join(settings.UPLOAD_DIR, file_path)

    if not os.path.exists(base_path):
        raise FileNotFound

    if os.path.isdir(base_path):
        listdir = os.listdir(base_path)
        return [
            File(
                name=file,
                type=FileType.FOLDER if os.path.isdir(os.path.join(base_path, file)) else FileType.FILE,
                # size=get_size(os.path.join(base_path, file)),
                # size_human=get_size(os.path.join(base_path, file), human=True),
            )
            for file in listdir
        ]
    else:
        return [
            File(
                name=os.path.basename(file_path),
                type=FileType.FILE,
                # size=get_size(base_path),
                # size_human=get_size(base_path, human=True)
            )
        ]


def needs_to_be_archived(file_path: str) -> bool:
    """
    TODO: write logic

    :param file_path:
    :return:
    """
    if os.path.isdir(file_path):
        return True

    return False


def health_check():
    disk_total, disk_used, disk_free = shutil.disk_usage(settings.UPLOAD_DIR)
    memory = psutil.virtual_memory()
    return {
        "status": "healthy",
        "disk": {
            "total": format_file_size(disk_total, human=True),
            "used": format_file_size(disk_used, human=True),
            "free": format_file_size(disk_free, human=True),
            "percent_used": f"{(disk_used / disk_total) * 100:.2f}%",
        },
        "memory": {
            "total": format_file_size(memory.total, human=True),
            "available": format_file_size(memory.available, human=True),
            "percent_used": f"{memory.percent:.2f}%",
        }
    }

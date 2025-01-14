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
from typing import Annotated

import aiofiles
import asyncio

from fastapi import Request, HTTPException, Depends, status

from app import settings
from app.logger import get_logger
from app.models import User


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name cannot be empty.")

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
    :param is_archive: Boolean flag indicating if file is archived folder.
    :return: tuple[str, str] file_name, dir_path
    """
    dir_path, file_name = os.path.split(file_path)
    dir_path = os.path.join(settings.UPLOAD_DIR, dir_path)
    os.makedirs(os.path.join(dir_path, '' if not is_archive else file_name), exist_ok=True)

    if is_archive:
        file_name = f".{file_name}.tar.gz"

    file_path = os.path.join(dir_path, file_name)
    return file_name, file_path


def clean_file(path_to_file: str) -> None:
    if os.path.exists(path_to_file):
        os.remove(path_to_file)


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
        clean_file(path_to_file=path)


async def save_file(request: Request) -> str:
    """
    This function saves a file of any content-type to our 10TB storage YOP service.
    Sanjar mustn't get a token for our service.

    :param request: FastAPI Request object. See https://fastapi.tiangolo.com/reference/request/#request-class
    :return: str: File name of saved file.
    """
    # TODO: check capacity on disk to save file
    content_disposition = request.headers.get("content-disposition")
    if not content_disposition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No content-disposition header",
        )

    # Parse filename (assumes standard format)
    file_path = content_disposition.split("filename=")[-1].strip('"')
    validate_file_name(file_path)

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

    # TODO: move to background task unzip_folder
    if is_archive:
        stdout, stderr = await unzip_folder(file_path)

        if stderr:
            logger.warning(f"Unzipping failed: {stderr}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unzipping failed",
            )

    return file_name


async def get_current_user(token: Annotated[str, Depends(User)]) -> User:
    """
    Asynchronously reads the file tokens.json to validate user credentials.

    :param token: str
    :return: User: pydantic model
    """

    return User(username="@backspace3")


async def archive_directory(dir_path: str) -> str:
    """
    Create a tar.gz archive from a directory.

    :param dir_path: Path to the source directory.
    :return: str: Path to the created archive tar.gz file.
    """
    _, dir_name = os.path.split(dir_path)
    file_path = os.path.join(settings.TMP_DIR, f".{dir_name}.tar.gz")
    zip_command = f"tar -cz --no-xattrs -f {file_path} -C {dir_path} ."

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

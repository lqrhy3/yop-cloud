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
import time
from pathlib import Path

import aiofiles
import asyncio

from fastapi import (
    BackgroundTasks, Request,
    HTTPException,
    status,
)

from app.logger import get_logger
from app.models import File, FileType, SIZE_UNITS
from app.settings import Settings

logger = get_logger(__name__)


class FileService:
    def __init__(self, settings: Settings):
        self._storage_data_path = Path(settings.STORAGE_DATA_PATH)
        self._temp_data_path = Path(settings.TEMP_DATA_PATH)

        self._is_archive_header = settings.IS_ARCHIVE_HEADER
        self._archive_extension = settings.ARCHIVE_EXTENSION
        self._max_file_name_length = settings.MAX_FILE_NAME_LENGTH

        self._valid_file_name_pattern = re.compile(r"^[a-zA-Z0-9._\-\s]+$")

    async def save_file(self, request: Request, background_tasks: BackgroundTasks) -> str:
        """
        Save the file from the request to the disk.
        Returns the file name, file path, and whether it is an archive.
        """
        content_disposition = request.headers.get("content-disposition")
        if not content_disposition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Content-Disposition header",
            )

        save_path = Path(content_disposition.split("filename=")[-1].strip('"'))
        self._validate_file_path(save_path)

        is_archive = request.headers.get(self._is_archive_header, "false").lower() == "true"

        temp_file_path, temp_dir_path, temp_file_name = self._prepare_paths(
            self._temp_data_path, save_path, is_archive
        )

        try:
            async with aiofiles.open(temp_file_path, "wb") as f:
                async for chunk in request.stream():
                    await f.write(chunk)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error writing file to the disk: {str(e)}"
            )

        file_path, dir_path, file_name = self._prepare_paths(
            self._storage_data_path, save_path, is_archive
        )

        logger.debug(f"Moving file from {temp_file_path} to {file_path}")
        try:
            os.rename(temp_file_path, file_path)
            os.removedirs(temp_dir_path)
        except OSError as e:
            logger.error(f"Failed to move and clean temp file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error moving and cleaning temp file: {str(e)}"
            )

        if is_archive:
            background_tasks.add_task(self._unzip_file, file_path)
        
        return temp_file_name

    async def download_file(self, download_path: str, background_tasks: BackgroundTasks) -> str:
        download_path = Path(download_path)
        self._validate_file_path(download_path)

        file_path = (self._storage_data_path / download_path).resolve()
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {download_path}"
            )

        if file_path.is_dir():
            file_path = await self._archive_file(file_path)
            background_tasks.add_task(self._delete_file, file_path)

        return str(file_path)

    async def list_files(self, list_path: str) -> list[File]:
        list_path = Path(list_path)
        self._validate_file_path(list_path)
        path = (self._storage_data_path / list_path).resolve()

        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {list_path}"
            )

        if path.is_dir():
            listdir = path.glob("*")
            return [
                File(
                    name=file.name,
                    type=FileType.FOLDER if file.is_dir() else FileType.FILE,
                    size=get_size(str(file)),
                    size_human=get_size(str(file), human=True),
                )
                for file in listdir
            ]
        else:
            return [
                File(
                    name=path.name,
                    type=FileType.FILE,
                    size=get_size(str(path)),
                    size_human=get_size(str(path), human=True)
                )
            ]

    async def _archive_file(self, file_path: Path) -> Path:
        temp_archive_path = self._temp_data_path / f"{file_path.name}_{hash(time.time())}.tar.gz"

        zip_command = f"tar -cz --no-xattrs -f {temp_archive_path} -C {file_path} ."
        try:
            process = await asyncio.create_subprocess_shell(
                cmd=zip_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"Failed to archive folder: {stderr}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Archiving failed"
                )

            logger.debug(f"Archived file successfully: {temp_archive_path}")
        except Exception as e:
            logger.error(f"Failed to archive folder: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error archiving file: {str(e)}"
            )

        return temp_archive_path

    def delete_file(self, delete_path: str | Path, background_tasks: BackgroundTasks):
        background_tasks.add_task(self._delete_file, delete_path)

    def _delete_file(self, delete_path: str | Path):
        """
        Deletes a file from disk if it exists.
        """
        delete_path = Path(delete_path) if isinstance(delete_path, str) else delete_path
        self._validate_file_path(delete_path)

        file_path = (self._storage_data_path / delete_path).resolve()

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {delete_path}"
            )

        try:
            if file_path.is_file():
                os.remove(file_path)
                logger.info(f"Removed {file_path}")
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                logger.info(f"Removed {file_path}")
            else:
                logger.info(f"The path '{file_path}' is neither a file nor a directory. What is it?")
        except OSError as e:
            logger.error(f"Failed to delete file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting file: {str(e)}"
            )

    def _prepare_paths(self, root_dir: Path, path: Path, is_archive: bool) -> tuple[Path, Path, str]:
        file_path = (root_dir / path).resolve()
        if is_archive:
            file_path = file_path / f".{file_path.name}{self._archive_extension}"

        dir_path, file_name = file_path.parent, file_path.name
        if not dir_path.exists():
            os.makedirs(dir_path)

        return file_path, dir_path, file_name

    async def _unzip_file(self, file_path: Path):
        """
        Unzips a tar.gz archive asynchronously and removes it after successful extraction.

        :param file_path: Path to the archive file
        """
        try:
            process = await asyncio.create_subprocess_shell(
                f"tar -xzf {file_path} -C {file_path.parent}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"Unzipping failed: {stderr.decode()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Unzipping failed"
                )

            logger.debug(f"Unzipped file successfully: {file_path}")

            try:
                os.remove(file_path)
                logger.debug(f"Removed archive file: {file_path}")
            except OSError as e:
                logger.error(f"Failed to remove archive file {file_path}: {str(e)}")
                # Do not throw an exception here, as it is not critical to the uploading process
                # TODO: consider potential problems because of this?

        except Exception as e:
            logger.error(f"Unzipping failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing archive: {str(e)}"
            )

    def _validate_file_path(self, file_path: Path):
        """
        Validate the user-provided file path to ensure it is safe, secure, and relative to the storage root.

        :param file_path: User-provided file path (relative).
        :return: The resolved full path where the file will be stored.
        """
        if not file_path or str(file_path).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File path cannot be empty."
            )

        if file_path.is_absolute():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Absolute paths are not allowed. Provide a relative file path."
            )

        full_path = (self._storage_data_path / file_path).resolve()

        if not full_path.is_relative_to(self._storage_data_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path. Path traversal is not allowed."
            )

        file_name = full_path.name

        if not file_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File path must include a valid file name."
            )

        if not self._valid_file_name_pattern.match(file_name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Invalid file name. Only alphanumeric characters, underscores, "
                    "hyphens, dots, and spaces are allowed."
                ),
            )

        reserved_chars = r'<>:"/\\|?*'
        invalid_chars = [char for char in reserved_chars if char in file_name]
        if invalid_chars:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File name contains invalid characters: {''.join(invalid_chars)}"
            )

        if len(file_name) > self._max_file_name_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File name is too long. Maximum length is {self._max_file_name_length} characters."
            )

        return full_path


def needs_to_be_archived(file_path: str) -> bool:
    """
    TODO: write logic

    :param file_path:
    :return:
    """
    if os.path.isdir(file_path):
        return True

    return False


def get_size(path: str, human: bool = False) -> int | str:
    file_size = os.path.getsize(path)
    if not human:
        return file_size

    i = 0
    while file_size > 1024:
        i += 1
        file_size = file_size / 1024
    return f"{int(file_size) if i == 0 else f'{file_size:.2f}'} {SIZE_UNITS[i]}"


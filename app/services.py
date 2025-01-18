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
from pathlib import Path

import aiofiles
import asyncio

from fastapi import (
    Request,
    HTTPException,
    Depends,
    status,
)

from app.logger import get_logger
from app.settings import Settings

logger = get_logger(__name__)


class FileService:
    def __init__(self, settings: Settings):
        self._storage_data_path = Path(settings.STORAGE_DATA_PATH)
        self._archive_extension = settings.ARCHIVE_EXTENSION
        self._max_file_name_length = settings.MAX_FILE_NAME_LENGTH

        self._valid_file_name_pattern = re.compile(r"^[a-zA-Z0-9._\-\s]+$")

    async def save_file(self, request: Request) -> tuple[str, Path, bool]:
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

        is_archive = request.headers.get("X-Is-Archive", "false").lower() == "true"

        file_path = (self._storage_data_path / save_path).resolve()
        if is_archive:
            file_path = file_path / f".{file_path.name}{self._archive_extension}"

        dir_path, file_name = file_path.parent, file_path.name
        if not dir_path.exists():
            os.makedirs(dir_path)


        try:
            async with aiofiles.open(file_path, "wb") as f:
                async for chunk in request.stream():
                    await f.write(chunk)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error writing file to the disk: {str(e)}"
            )

        return file_name, file_path, is_archive

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


class ArchiveService:

    def __init__(self, settings: Settings):
        pass

    async def unzip_file(self, file_path: Path):
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


def needs_to_be_archived(file_path: str) -> bool:
    """
    TODO: write logic

    :param file_path:
    :return:
    """
    if os.path.isdir(file_path):
        return True

    return False

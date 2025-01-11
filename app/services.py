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

import aiofiles
from fastapi import Request, HTTPException, status

from app import settings


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


def allocate_folders(file_path: str) -> tuple[str, str]:
    """
    Create folder structure based on file name.

    :param file_path: File path to create folder structure for.
    :return: tuple[str, str] file_name, dir_path
    """
    dir_path, file_name = os.path.split(file_path)
    dir_path = os.path.join(settings.UPLOAD_DIR, dir_path)
    os.makedirs(dir_path, exist_ok=True)
    file_path = os.path.join(dir_path, file_name)
    return file_name, file_path


async def save_file(request: Request) -> str:
    """
    This function saves a file of any content-type to our 10TB storage YOP service.
    Sanjar mustn't get a token for our service.

    :param request: FastAPI Request object. See https://fastapi.tiangolo.com/reference/request/#request-class
    :return:
    """
    content_disposition = request.headers.get("content-disposition")
    if not content_disposition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "No content-disposition header"},
        )

    # Parse filename (assumes standard format)
    file_path = content_disposition.split("filename=")[-1].strip('"')

    # Allocate folders
    file_name, file_path = allocate_folders(file_path)

    # Validate file_name
    validate_file_name(file_name)

    # Write file directly to disk
    async with aiofiles.open(file_path, "wb") as f:
        async for chunk in request.stream():
            await f.write(chunk)

    return file_name


async def get_file():
    ...

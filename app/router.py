"""
router.py

This module defines the API routes for the FastAPI application. It serves as a central place for managing
endpoints, ensuring clear organization and separation of concerns within the project.

The file typically includes:
1. Importing FastAPI's APIRouter for defining routes.
2. Grouping and organizing related routes for specific functionalities or resources.
3. Dependency injection for shared logic (e.g., database sessions, authentication).
4. Route definitions with proper request methods, request validation, and response handling.
5. Error handling and response customization for specific endpoints.

Classes and Functions:
----------------------
- router: An instance of `APIRouter` that groups and registers API endpoints.
- Individual route handlers for various API actions, such as CRUD operations.
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, FileResponse

from app.logger import get_logger
from app import services
from app import settings
from app.exceptions import FileNotFound

logger = get_logger(__name__)
router = APIRouter(tags=["files"])


@router.post("/upload/")
async def upload_file(request: Request):
    """
    Upload a file to disk. It can store file of any type.
    If the header X-Is-Folder is specified, tmp tar.gz archive will be created and unzipped

    :param request: FastAPI Request object. See https://fastapi.tiangolo.com/reference/request/#request-class
    :return:
    200:
        {
            "file_name": "sanjar's dickpick",
            "message": "Upload successful"
        }
    """
    logger.info("Called /upload")
    file_name = await services.save_file(request)
    return JSONResponse({"file_name": file_name, "message": "Upload successful"})


@router.get("/download/{file_name:path}", response_class=FileResponse)
async def download_file(file_name: str):
    """
    Download a file from disk.

    :param file_name: File to download.
    :return: Asynchronously streams a file as the response.
    404:
        {
            "detail": "File not found"
        }
    """
    logger.info("Called /download", extra={"file_name": file_name})
    file_path = os.path.join(settings.UPLOAD_DIR, file_name)

    if not os.path.exists(file_path):
        raise FileNotFound

    if os.path.isdir(file_path):
        file_path = await services.archive_directory(file_path)

    return FileResponse(file_path)


@router.get("/{file_path:path}")
def ls(file_path: str):
    """
    :param file_path: File to ls.
    :return: list[str]: List of file paths.
    """
    base_path = os.path.join(settings.UPLOAD_DIR, file_path)
    logger.info('Called /ls', extra={"file_path": file_path})

    if not os.path.exists(base_path):
        raise FileNotFound

    if os.path.isdir(base_path):
        listdir = os.listdir(base_path)
        return [
            {'file_name': file, 'file_type': 'folder' if os.path.isdir(os.path.join(base_path, file)) else 'file'}
            for file in listdir
        ]
    else:
        return [{'file_name': os.path.basename(file_path), 'file_type': 'file'}]

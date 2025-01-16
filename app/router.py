"""
router.py

This module defines the API routes for the FastAPI application. It serves as a central place for managing
endpoints, ensuring clear organization and separation of concerns within the project.

The file typically includes:
1. Importing FastAPI"s APIRouter for defining routes.
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

from fastapi import APIRouter, Request, Response, BackgroundTasks, status
from fastapi.responses import JSONResponse, FileResponse

from app.logger import get_logger
from app import (services, settings, models)
from app.exceptions import FileNotFound

logger = get_logger(__name__)
router = APIRouter(tags=["files"])


@router.post("/upload/")
async def upload_file(request: Request):
    """
    Upload a file to disk. It can store file of any type.
    If the header X-Is-Archive is specified, tmp tar.gz archive will be created and unzipped

    :param request: FastAPI Request object. See https://fastapi.tiangolo.com/reference/request/#request-class
    :return:
    200:
        {
            "file_name": "sanjar"s dickpick",
            "message": "Upload successful"
        }
    """
    logger.info("Called /upload")
    file_name = await services.save_file(request)
    return JSONResponse({"file_name": file_name, "message": "Upload successful"})


@router.get("/download/{file_name:path}", response_class=FileResponse)
async def download_file(file_name: str, background_tasks: BackgroundTasks):
    """
    Download a file from disk. Creates .tar.gz archive if downloaded file is folder.

    :param file_name: File to download.
    :param background_tasks: FastAPI BackgroundTasks object. See https://fastapi.tiangolo.com/tutorial/background-tasks/#using-backgroundtasks
    :return: Asynchronously streams a file as the response.
    404:
        {
            "detail": "File not found"
        }
    """
    logger.info("Called /download", extra={"file_name": file_name})
    file_path = await services.download_file(file_name, background_tasks)
    return FileResponse(file_path)


@router.delete("/delete/{file_path:path}")
def delete_file(file_path: str, background_tasks: BackgroundTasks):
    """
    God help me.

    :param file_path: File to delete.
    :param background_tasks: FastAPI BackgroundTasks object.
    :return: no content
    """
    logger.info("Called /delete", extra={"file_path": file_path})
    background_tasks.add_task(services.clean_file, file_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{file_path:path}", response_model=list[models.File])
async def ls(file_path: str) -> list[models.File]:
    """
    :param file_path: File to ls.
    :return: list[File]: List of file paths.
    """
    logger.info("Called /ls", extra={"file_path": file_path})
    return await services.ls(file_path)

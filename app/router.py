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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, BackgroundTasks, status
from fastapi.responses import JSONResponse, FileResponse

from app.dependencies import FileServiceDep
from app.logger import get_logger
from app import (services, settings, models)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint to verify that the service is running.

    :return: JSON response indicating the health status of the service.
    """
    logger.info("Called /health")
    return JSONResponse({"status": "ok", "message": "Service is running"})


@router.post("/upload/")
async def upload_file(
        request: Request,
        background_tasks: BackgroundTasks,
        file_service: FileServiceDep,
        force: bool = Query(
            default=False, description="Force file overwrite if it already exists"
        ),
):
    """
    Upload a file to disk and optionally unzip it.
    """
    logger.info("Called /upload")

    try:
        file_name = await file_service.save_file(request, background_tasks, force)
    except HTTPException as e:
        logger.error(f"Error saving file: {e.detail}")
        raise

    return JSONResponse({
        "file_name": file_name,
        "message": "Upload successful"
    })


@router.get("/download/{file_name:path}", response_class=FileResponse)
async def download_file(file_name: str, background_tasks: BackgroundTasks, file_service: FileServiceDep):
    """
    Download a file from disk. Creates .tar.gz archive if downloaded file is folder.

    :param file_name: File to download.
    :param background_tasks: FastAPI BackgroundTasks object. See https://fastapi.tiangolo.com/tutorial/background-tasks/#using-backgroundtasks
    :param file_service: FileService dependency.
    :return: Asynchronously streams a file as the response.
    404:
        {
            "detail": "File not found"
        }
    """
    logger.info("Called /download", extra={"file_name": file_name})
    file_path = await file_service.download_file(file_name, background_tasks)
    return FileResponse(file_path)


@router.delete("/delete/{file_path:path}")
def delete_file(file_path: str, background_tasks: BackgroundTasks, file_service: FileServiceDep):
    """
    God help me.

    :param file_path: File to delete.
    :param background_tasks: FastAPI BackgroundTasks object.
    :return: no content
    """
    logger.info("Called /delete", extra={"file_path": file_path})
    file_service.delete_file(file_path, background_tasks)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/ls/{file_path:path}", response_model=list[models.File])
async def ls(
        file_path: str,
        file_service: FileServiceDep,
        verbose: bool = Query(
            efault=False, description="Return file type and size or not"
        ),

) -> list[models.File]:
    """
    :param file_path: File to ls.
    :param file_service: FileService dependency.
    :param verbose: Return file type and size or not.
    :return: list[File]: List of file paths.
    """
    logger.info("Called /ls", extra={"file_path": file_path, "verbose": verbose})
    return await file_service.list_files(file_path, verbose)


@router.get("/disk_usage/")
async def disk_usage(file_service: FileServiceDep):
    """
    :param file_service: FileService dependency.
    :return: list[File]: List of file paths.
    """
    logger.info("Called /disk_usage")
    disk_usage = await file_service.disk_usage()
    return JSONResponse(disk_usage)

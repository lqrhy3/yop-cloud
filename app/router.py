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
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import services


router = APIRouter(tags=["files"])


@router.post("/upload/")
async def upload_file(request: Request):
    """
    Upload a file to disk. It can stores file of any type.
    TODO: Add docstring
    TODO: Add auth (Create a token for Sanjar which doesn't work)

    :param request: FastAPI Request object. See https://fastapi.tiangolo.com/reference/request/#request-class
    :return:
    200:
        {
            "file_name": "sanjar's dickpick",
            "message": "Upload successful",
            "status_code": 200
        }
    400:
        {
            "message": "No content-disposition header",
            "status_code": 400
        }
    500:
        {
            "message": "Internal Server Error",
            "status_code": 500
        }
    """
    file_name = await services.save_file(request)
    return JSONResponse({"filename": file_name, "message": "Upload successful"})

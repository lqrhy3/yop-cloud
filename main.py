import json
import aiofiles
from typing import Union

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, status
from fastapi.responses import JSONResponse

from app.router import router
from app.exceptions import Unauthorized


@asynccontextmanager
async def lifespan(app: FastAPI):
    """

    :param app: FastAPI application
    :return:
    """
    async with aiofiles.open("tokens.json", mode="r") as f:
        data = await f.read()
        json_data = json.loads(data)
        app.state.tokens = json_data.get("users")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Authenticate request token from Authorization header

    :param request: FastAPI request object
    :param call_next: FastAPI request handler
    :return:
    """
    if "authorization" not in request.headers:
        return Unauthorized

    token = request.headers["authorization"].split(" ")[-1]

    for creds in request.app.state.tokens:
        if token == creds.get("token"):
            response = await call_next(request)
            return response
    else:
        return Unauthorized


@app.get("/")
async def root():
    return {"Hello": "World"}

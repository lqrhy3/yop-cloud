import json
import aiofiles

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.logger import get_logger
from app.router import router
from app.exceptions import Unauthorized

from slowapi import Limiter
from slowapi.util import get_remote_address


logger = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)


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


app = FastAPI(debug=True, lifespan=lifespan)
app.include_router(router)


@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    """
    Authenticate request token from Authorization header

    :param request: FastAPI request object
    :param call_next: FastAPI request handler
    :return:
    """
    try:
        if "authorization" not in request.headers:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "No authorization header provided"},
            )
        
        auth_header = request.headers["authorization"]
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authorization header format"},
            )

        token = auth_header.split(" ")[-1]

        for creds in request.app.state.tokens:
            if token == creds.get("token"):
                response = await call_next(request)
                return response
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid token"}
        )
    except Exception as e:
        logger.error(str(e))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error"}
        )

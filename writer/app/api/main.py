from fastapi import APIRouter, Request


api_router = APIRouter(prefix="/upload", tags=["writer"])


@api_router.post("/")
async def upload(*, request: Request):
    ...
    return {"message": "OK"}

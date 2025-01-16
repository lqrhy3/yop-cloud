from enum import Enum

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str


class User(BaseModel):
    username: str


class File(BaseModel):
    name: str
    type: str
    size: int
    size_human: str


class FileType(Enum):
    FOLDER = "folder"
    FILE = "file"


SIZE_UNITS = [
    "bytes",
    "KB",
    "MB",
    "GB",
]

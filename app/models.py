from enum import Enum
from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str


class User(BaseModel):
    username: str


class File(BaseModel):
    name: str
    type: Optional[str] = None
    size: Optional[int] = None
    size_human: Optional[str] = None


class FileType(Enum):
    FOLDER = "folder"
    FILE = "file"


SIZE_UNITS = [
    "bytes",
    "KB",
    "MB",
    "GB",
]

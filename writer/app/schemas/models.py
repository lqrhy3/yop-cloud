from typing import Literal
from uuid import UUID


class File:
    id: int
    name: str
    user_id: UUID
    parent_id: int = -1
    file_type: Literal["FILE", "DIRECTORY"]
    is_ready: bool


class ChunkPerFile:
    id: int
    user_id: UUID
    file_id: int
    chunk_hash: str
    index: int

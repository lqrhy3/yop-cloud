from pydantic import BaseModel


class Token(BaseModel):
    access_token: str


class User(BaseModel):
    username: str

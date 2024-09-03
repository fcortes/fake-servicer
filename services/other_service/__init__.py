from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class User(BaseModel):
    username: str

@router.get("/users")
def read_users() -> list[User]:
    return [
        User(username="Dennis"),
        User(username="Brian"),
        User(username="Ken"),
    ]

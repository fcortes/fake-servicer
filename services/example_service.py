import random

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()


class User(BaseModel):
    username: str

class Error(BaseModel):
    detail: str

@router.get(
    "/users",
    response_model=list[User],
    responses={500: {"model": Error}},
)
def read_users():
    if random.random() < 0.1:
        return JSONResponse(status_code=500, content={"detail": "‽"})

    return [
        User(username="Ron"),
        User(username="Adi"),
        User(username="Leonard"),
    ]

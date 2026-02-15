from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models import User
from app.schemas import RandomPersonResponse
from app.services.generators import generator_in, generator_sk, random_person

router = APIRouter()


@router.get("/random-person", response_model=RandomPersonResponse)
def get_random_person(current_user: User = Depends(get_current_user)) -> RandomPersonResponse:
    _ = current_user
    return RandomPersonResponse(**random_person())


@router.get("/generator/in")
def get_in_generator(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    _ = current_user
    return generator_in()


@router.get("/generator/sk")
def get_sk_generator(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    _ = current_user
    return generator_sk()

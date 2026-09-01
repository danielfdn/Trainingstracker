from fastapi import APIRouter, HTTPException, status

from app.api.deps import UserRepoDep
from app.entities.user import User
from app.schemas.user import UserCreate, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, repo: UserRepoDep) -> User:
    # model_dump() macht aus dem Pydantic-Schema ein Dict, das direkt als
    # Konstruktor-Argumente ins ORM-Modell passt.
    return repo.create(User(**user_in.model_dump()))


@router.get("", response_model=list[UserPublic])
def read_users(repo: UserRepoDep, skip: int = 0, limit: int = 100) -> list[User]:
    return repo.list(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserPublic)
def read_user(user_id: int, repo: UserRepoDep) -> User:
    user = repo.get(user_id)
    if user is None:
        # f-String! Ohne das f landet die geschweifte Klammer woertlich
        # in der Fehlermeldung.
        raise HTTPException(status_code=404, detail=f"User {user_id} nicht gefunden")
    return user


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user_in: UserUpdate, repo: UserRepoDep) -> User:
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} nicht gefunden")
    # exclude_unset=True: nur die Felder, die der Client wirklich geschickt hat.
    # Ohne das wuerden nicht gesendete Felder faelschlich auf None gesetzt.
    return repo.update(user, user_in.model_dump(exclude_unset=True))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, repo: UserRepoDep) -> None:
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} nicht gefunden")
    repo.delete(user)

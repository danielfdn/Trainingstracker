"""Dependencies fuer die Endpunkte.

FastAPI ruft diese Funktionen pro Request auf und reicht das Ergebnis an den
Endpunkt weiter. So bekommt jeder Request seine eigene DB-Session und seine
eigenen Repo-Instanzen - und im Test kann man sie per dependency_overrides
durch Attrappen ersetzen.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.repositories.exercise_repo import ExerciseRepo
from app.repositories.set_repo import SetRepo
from app.repositories.user_repo import UserRepo
from app.repositories.workout_plan_repo import WorkoutPlanRepo
from app.repositories.workout_repo import WorkoutRepo


def get_session() -> Generator[Session, None, None]:
    """Leiht eine Session aus dem Pool und gibt sie danach garantiert zurueck.

    Das "yield ... finally close" ersetzt die alte Situation, in der jede
    Repo-Instanz eine Verbindung aufmachte, die nie geschlossen wurde.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]


def get_user_repo(session: SessionDep) -> UserRepo:
    return UserRepo(session)


def get_workout_plan_repo(session: SessionDep) -> WorkoutPlanRepo:
    return WorkoutPlanRepo(session)


def get_exercise_repo(session: SessionDep) -> ExerciseRepo:
    return ExerciseRepo(session)


def get_set_repo(session: SessionDep) -> SetRepo:
    return SetRepo(session)


def get_workout_repo(session: SessionDep) -> WorkoutRepo:
    return WorkoutRepo(session)


# Abkuerzungen, damit die Endpunkte kurz bleiben:
# def read_user(repo: UserRepoDep) -> ...
UserRepoDep = Annotated[UserRepo, Depends(get_user_repo)]
WorkoutPlanRepoDep = Annotated[WorkoutPlanRepo, Depends(get_workout_plan_repo)]
ExerciseRepoDep = Annotated[ExerciseRepo, Depends(get_exercise_repo)]
SetRepoDep = Annotated[SetRepo, Depends(get_set_repo)]
WorkoutRepoDep = Annotated[WorkoutRepo, Depends(get_workout_repo)]

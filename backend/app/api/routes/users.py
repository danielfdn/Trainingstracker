from fastapi import APIRouter, HTTPException, status

from app.api.deps import UserRepoDep, WorkoutPlanRepoDep
from app.entities.user import User
from app.entities.workout_plan import WorkoutPlan
from app.schemas.user import ActivePlanUpdate, UserCreate, UserPublic, UserUpdate
from app.schemas.workout_plan import WorkoutPlanWithDays

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


@router.put("/{user_id}/active-plan", response_model=UserPublic)
def set_active_plan(
    user_id: int,
    auswahl: ActivePlanUpdate,
    repo: UserRepoDep,
    plan_repo: WorkoutPlanRepoDep,
) -> User:
    """Waehlt den aktiven Trainingsplan. workout_plan_id=null hebt die Wahl auf.

    PUT statt PATCH: es gibt genau einen aktiven Plan, der Aufruf setzt ihn
    vollstaendig - zweimal derselbe Aufruf hat dasselbe Ergebnis.
    """
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} nicht gefunden")

    if auswahl.workout_plan_id is not None:
        plan = plan_repo.get(auswahl.workout_plan_id)
        if plan is None:
            raise HTTPException(
                status_code=404,
                detail=f"Trainingsplan {auswahl.workout_plan_id} nicht gefunden",
            )
        # Ein fremder Plan waere in der DB erlaubt (der Fremdschluessel sagt
        # nur "irgendein Plan"), fachlich aber Unsinn.
        if plan.user_id != user_id:
            raise HTTPException(
                status_code=422,
                detail=f"Trainingsplan {plan.id} gehoert zu User {plan.user_id}, nicht zu User {user_id}",
            )

    return repo.update(user, {"active_workout_plan_id": auswahl.workout_plan_id})


@router.get("/{user_id}/active-plan", response_model=WorkoutPlanWithDays)
def read_active_plan(
    user_id: int, repo: UserRepoDep, plan_repo: WorkoutPlanRepoDep
) -> WorkoutPlan:
    """Der aktive Plan samt Trainingstagen - das laedt das Hauptmenue."""
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} nicht gefunden")
    if user.active_workout_plan_id is None:
        raise HTTPException(
            status_code=404, detail=f"User {user_id} hat keinen aktiven Trainingsplan"
        )
    plan = plan_repo.get_with_days(user.active_workout_plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trainingsplan {user.active_workout_plan_id} nicht gefunden",
        )
    return plan

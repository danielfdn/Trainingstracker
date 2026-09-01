from fastapi import APIRouter, HTTPException, status

from app.api.deps import UserRepoDep, WorkoutPlanRepoDep
from app.entities.workout_plan import WorkoutPlan
from app.schemas.workout_plan import (
    WorkoutPlanCreate,
    WorkoutPlanPublic,
    WorkoutPlanUpdate,
    WorkoutPlanWithExercises,
)

router = APIRouter(prefix="/workout-plans", tags=["workout-plans"])


@router.post("", response_model=WorkoutPlanPublic, status_code=status.HTTP_201_CREATED)
def create_workout_plan(
    plan_in: WorkoutPlanCreate, repo: WorkoutPlanRepoDep, user_repo: UserRepoDep
) -> WorkoutPlan:
    # Existenz des Users pruefen, bevor die DB einen Fremdschluesselfehler wirft -
    # so bekommt der Client eine verstaendliche 404 statt einer 500.
    if user_repo.get(plan_in.user_id) is None:
        raise HTTPException(
            status_code=404, detail=f"User {plan_in.user_id} nicht gefunden"
        )
    return repo.create(WorkoutPlan(**plan_in.model_dump()))


@router.get("", response_model=list[WorkoutPlanPublic])
def read_workout_plans(
    repo: WorkoutPlanRepoDep,
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[WorkoutPlan]:
    if user_id is not None:
        return repo.list_by_user(user_id, skip=skip, limit=limit)
    return repo.list(skip=skip, limit=limit)


@router.get("/{plan_id}", response_model=WorkoutPlanWithExercises)
def read_workout_plan(plan_id: int, repo: WorkoutPlanRepoDep) -> WorkoutPlan:
    """Plan inklusive Uebungen und Saetzen - das braucht die PWA fuer die Detailansicht."""
    plan = repo.get_with_exercises(plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404, detail=f"Trainingsplan {plan_id} nicht gefunden"
        )
    return plan


@router.patch("/{plan_id}", response_model=WorkoutPlanPublic)
def update_workout_plan(
    plan_id: int, plan_in: WorkoutPlanUpdate, repo: WorkoutPlanRepoDep
) -> WorkoutPlan:
    plan = repo.get(plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404, detail=f"Trainingsplan {plan_id} nicht gefunden"
        )
    return repo.update(plan, plan_in.model_dump(exclude_unset=True))


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_plan(plan_id: int, repo: WorkoutPlanRepoDep) -> None:
    plan = repo.get(plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404, detail=f"Trainingsplan {plan_id} nicht gefunden"
        )
    repo.delete(plan)

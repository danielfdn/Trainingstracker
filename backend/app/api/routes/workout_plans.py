from fastapi import APIRouter, HTTPException, status

from app.api.deps import ExerciseRepoDep, UserRepoDep, WorkoutPlanRepoDep
from app.entities.training_day import TrainingDay
from app.entities.training_day_exercise import TrainingDayExercise
from app.entities.workout_plan import WorkoutPlan
from app.schemas.workout_plan import (
    WorkoutPlanCreate,
    WorkoutPlanPublic,
    WorkoutPlanUpdate,
    WorkoutPlanWithDays,
)

router = APIRouter(prefix="/workout-plans", tags=["workout-plans"])


@router.post("", response_model=WorkoutPlanPublic, status_code=status.HTTP_201_CREATED)
def create_workout_plan(
    plan_in: WorkoutPlanCreate,
    repo: WorkoutPlanRepoDep,
    user_repo: UserRepoDep,
    exercise_repo: ExerciseRepoDep,
) -> WorkoutPlan:
    """Legt einen Plan an, optional gleich mit seinen Trainingstagen.

    Die Tage lassen sich mitschicken, weil beim Anlegen ohnehin feststeht,
    an wie vielen Tagen pro Woche was trainiert wird. Ein leerer Plan ist
    ebenfalls erlaubt - die Tage kommen dann ueber /training-days dazu.
    """
    # Existenz des Users pruefen, bevor die DB einen Fremdschluesselfehler wirft -
    # so bekommt der Client eine verstaendliche 404 statt einer 500.
    if user_repo.get(plan_in.user_id) is None:
        raise HTTPException(
            status_code=404, detail=f"User {plan_in.user_id} nicht gefunden"
        )

    daten = plan_in.model_dump(exclude={"training_days"})
    plan = WorkoutPlan(**daten)
    for tag_in in plan_in.training_days:
        tag = TrainingDay(position=tag_in.position, workout_type=tag_in.workout_type)
        for eintrag in tag_in.exercises:
            uebung = exercise_repo.get(eintrag.exercise_id)
            if uebung is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Uebung {eintrag.exercise_id} nicht gefunden",
                )
            if uebung.user_id != plan_in.user_id:
                raise HTTPException(
                    status_code=422,
                    detail=f"Uebung '{uebung.title}' gehoert nicht zu User {plan_in.user_id}",
                )
            tag.exercise_links.append(TrainingDayExercise(**eintrag.model_dump()))
        plan.training_days.append(tag)
    return repo.create(plan)


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


@router.get("/{plan_id}", response_model=WorkoutPlanWithDays)
def read_workout_plan(plan_id: int, repo: WorkoutPlanRepoDep) -> WorkoutPlan:
    """Plan inklusive Trainingstage, Uebungen und Vorgaben - Detailansicht der PWA."""
    plan = repo.get_with_days(plan_id)
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

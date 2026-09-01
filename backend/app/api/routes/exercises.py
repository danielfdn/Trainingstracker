from fastapi import APIRouter, HTTPException, status

from app.api.deps import ExerciseRepoDep, WorkoutPlanRepoDep
from app.entities.exercise import Exercise
from app.schemas.exercise import (
    ExerciseCreate,
    ExercisePublic,
    ExerciseUpdate,
    ExerciseWithSets,
)

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.post("", response_model=ExercisePublic, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_in: ExerciseCreate, repo: ExerciseRepoDep, plan_repo: WorkoutPlanRepoDep
) -> Exercise:
    if plan_repo.get(exercise_in.workout_plan_id) is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trainingsplan {exercise_in.workout_plan_id} nicht gefunden",
        )
    return repo.create(Exercise(**exercise_in.model_dump()))


@router.get("", response_model=list[ExercisePublic])
def read_exercises(
    repo: ExerciseRepoDep,
    workout_plan_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Exercise]:
    if workout_plan_id is not None:
        return repo.list_by_plan(workout_plan_id)
    return repo.list(skip=skip, limit=limit)


@router.get("/{exercise_id}", response_model=ExerciseWithSets)
def read_exercise(exercise_id: int, repo: ExerciseRepoDep) -> Exercise:
    exercise = repo.get_with_sets(exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=404, detail=f"Uebung {exercise_id} nicht gefunden"
        )
    return exercise


@router.patch("/{exercise_id}", response_model=ExercisePublic)
def update_exercise(
    exercise_id: int, exercise_in: ExerciseUpdate, repo: ExerciseRepoDep
) -> Exercise:
    exercise = repo.get(exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=404, detail=f"Uebung {exercise_id} nicht gefunden"
        )
    return repo.update(exercise, exercise_in.model_dump(exclude_unset=True))


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, repo: ExerciseRepoDep) -> None:
    exercise = repo.get(exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=404, detail=f"Uebung {exercise_id} nicht gefunden"
        )
    repo.delete(exercise)

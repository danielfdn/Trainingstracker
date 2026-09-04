from fastapi import APIRouter, HTTPException, status

from app.api.deps import ExerciseRepoDep, UserRepoDep
from app.entities.exercise import Exercise
from app.schemas.exercise import (
    ExerciseCreate,
    ExercisePublic,
    ExerciseUpdate,
    ExerciseWithSets,
)

router = APIRouter(prefix"/exer=cises", tags=["exercises"])


@router.post("", response_model=ExercisePublic, status_code=status.HTTP_201_CREATED)
def create_exercise(
    exercise_in: ExerciseCreate, repo: ExerciseRepoDep, user_repo: UserRepoDep
) -> Exercise:
    """Legt eine Uebung im Katalog des Users an."""
    if user_repo.get(exercise_in.user_id) is None:
        raise HTTPException(
            status_code=404, detail=f"User {exercise_in.user_id} nicht gefunden"
        )
    # Vor dem Insert pruefen: der Unique-Constraint wuerde sonst als 500
    # durchschlagen. Ein zweites "Bankdruecken" wuerde den Verlauf teilen.
    vorhanden = repo.get_by_title(exercise_in.user_id, exercise_in.title)
    if vorhanden is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Uebung '{vorhanden.title}' gibt es bereits (id {vorhanden.id})",
        )
    return repo.create(Exercise(**exercise_in.model_dump()))


@router.get("", response_model=list[ExercisePublic])
def read_exercises(
    repo: ExerciseRepoDep,
    user_id: int | None = None,
    workout_plan_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Exercise]:
    """Der Katalog eines Users, oder die Uebungen, die in einem Plan vorkommen."""
    if workout_plan_id is not None:
        return repo.list_by_plan(workout_plan_id)
    if user_id is not None:
        return repo.list_by_user(user_id, skip=skip, limit=limit)
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
    daten = exercise_in.model_dump(exclude_unset=True)
    neuer_titel = daten.get("title")
    if neuer_titel is not None:
        kollision = repo.get_by_title(exercise.user_id, neuer_titel)
        if kollision is not None and kollision.id != exercise.id:
            raise HTTPException(
                status_code=409,
                detail=f"Uebung '{kollision.title}' gibt es bereits (id {kollision.id})",
            )
    return repo.update(exercise, daten)


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, repo: ExerciseRepoDep) -> None:
    """Loescht die Uebung samt ihrer protokollierten Saetze.

    Achtung: damit verschwindet auch der Verlauf dieser Uebung aus der
    Auswertung - das Frontend sollte davor warnen.
    """
    exercise = repo.get(exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=404, detail=f"Uebung {exercise_id} nicht gefunden"
        )
    repo.delete(exercise)

from fastapi import APIRouter, HTTPException, status

from app.api.deps import (
    ExerciseRepoDep,
    SetRepoDep,
    WorkoutPlanRepoDep,
    WorkoutRepoDep,
)
from app.entities.set import Set
from app.schemas.set import SetCreate, SetPublic, SetUpdate

router = APIRouter(prefix="/sets", tags=["sets"])


@router.post("", response_model=SetPublic, status_code=status.HTTP_201_CREATED)
def create_set(
    set_in: SetCreate,
    repo: SetRepoDep,
    exercise_repo: ExerciseRepoDep,
    workout_repo: WorkoutRepoDep,
    plan_repo: WorkoutPlanRepoDep,
) -> Set:
    """Protokolliert einen absolvierten Satz innerhalb einer Trainingseinheit."""
    exercise = exercise_repo.get(set_in.exercise_id)
    if exercise is None:
        raise HTTPException(
            status_code=404, detail=f"Uebung {set_in.exercise_id} nicht gefunden"
        )
    workout = workout_repo.get(set_in.workout_id)
    if workout is None:
        raise HTTPException(
            status_code=404, detail=f"Workout {set_in.workout_id} nicht gefunden"
        )
    # Die Uebung gehoert jetzt zum User, nicht mehr zum Plan - genau das
    # macht den Vergleich ueber Planwechsel hinweg moeglich. Geprueft wird
    # deshalb, ob Uebung und Einheit demselben User gehoeren: ein Satz mit
    # Bankdruecken von Anna, protokolliert in Bens Einheit, waere Unsinn.
    # Ein freies Training (training_day_id=None) darf jede eigene Uebung
    # enthalten - das ist der Sinn der Sache.
    plan = plan_repo.get(workout.workout_plan_id)
    if plan is not None and exercise.user_id != plan.user_id:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Uebung '{exercise.title}' gehoert zu User {exercise.user_id}, "
                f"das Workout aber zu User {plan.user_id}"
            ),
        )
    # Fachliche Regel: eine Uebung ohne Zusatzgewicht darf kein Gewicht tragen.
    if not exercise.weighted and set_in.weight is not None:
        raise HTTPException(
            status_code=422,
            detail=f"Uebung '{exercise.title}' ist nicht gewichtsbasiert - weight muss leer bleiben",
        )
    return repo.create(Set(**set_in.model_dump()))


@router.get("", response_model=list[SetPublic])
def read_sets(
    repo: SetRepoDep,
    exercise_id: int | None = None,
    workout_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Set]:
    """Saetze filterbar nach Uebung (Verlauf) und/oder Einheit (Tagesprotokoll)."""
    if exercise_id is not None and workout_id is not None:
        return repo.list_by_exercise_and_workout(exercise_id, workout_id)
    if exercise_id is not None:
        return repo.list_by_exercise(exercise_id)
    if workout_id is not None:
        return repo.list_by_workout(workout_id)
    return repo.list(skip=skip, limit=limit)


@router.get("/{set_id}", response_model=SetPublic)
def read_set(set_id: int, repo: SetRepoDep) -> Set:
    set_ = repo.get(set_id)
    if set_ is None:
        raise HTTPException(status_code=404, detail=f"Satz {set_id} nicht gefunden")
    return set_


@router.patch("/{set_id}", response_model=SetPublic)
def update_set(set_id: int, set_in: SetUpdate, repo: SetRepoDep) -> Set:
    set_ = repo.get(set_id)
    if set_ is None:
        raise HTTPException(status_code=404, detail=f"Satz {set_id} nicht gefunden")
    return repo.update(set_, set_in.model_dump(exclude_unset=True))


@router.delete("/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_set(set_id: int, repo: SetRepoDep) -> None:
    set_ = repo.get(set_id)
    if set_ is None:
        raise HTTPException(status_code=404, detail=f"Satz {set_id} nicht gefunden")
    repo.delete(set_)

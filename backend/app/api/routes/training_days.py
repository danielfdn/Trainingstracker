from fastapi import APIRouter, HTTPException, status

from app.api.deps import ExerciseRepoDep, TrainingDayRepoDep, WorkoutPlanRepoDep
from app.entities.training_day import TrainingDay
from app.entities.training_day_exercise import TrainingDayExercise
from app.schemas.training_day import (
    TrainingDayCreate,
    TrainingDayExerciseCreate,
    TrainingDayExercisePublic,
    TrainingDayExerciseUpdate,
    TrainingDayPublic,
    TrainingDayUpdate,
    TrainingDayWithExercises,
)

router = APIRouter(prefix="/training-days", tags=["training-days"])


def _hole_tag(training_day_id: int, repo: TrainingDayRepoDep) -> TrainingDay:
    tag = repo.get(training_day_id)
    if tag is None:
        raise HTTPException(
            status_code=404, detail=f"Trainingstag {training_day_id} nicht gefunden"
        )
    return tag


def _hole_platz(
    training_day_id: int, link_id: int, repo: TrainingDayRepoDep
) -> TrainingDayExercise:
    """Der Platz, samt Pruefung dass er wirklich zu diesem Tag gehoert.

    Ohne die Pruefung koennte man mit der id eines fremden Platzes die
    Vorgabe eines anderen Trainingstages aendern.
    """
    link = repo.get_link(link_id)
    if link is None or link.training_day_id != training_day_id:
        raise HTTPException(
            status_code=404,
            detail=f"Platz {link_id} gehoert nicht zu Trainingstag {training_day_id}",
        )
    return link


@router.post("", response_model=TrainingDayPublic, status_code=status.HTTP_201_CREATED)
def create_training_day(
    day_in: TrainingDayCreate,
    repo: TrainingDayRepoDep,
    plan_repo: WorkoutPlanRepoDep,
    exercise_repo: ExerciseRepoDep,
) -> TrainingDay:
    plan = plan_repo.get(day_in.workout_plan_id)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trainingsplan {day_in.workout_plan_id} nicht gefunden",
        )
    if any(tag.position == day_in.position for tag in repo.list_by_plan(plan.id)):
        raise HTTPException(
            status_code=409,
            detail=f"Position {day_in.position} ist in diesem Plan schon belegt",
        )

    tag = TrainingDay(
        position=day_in.position,
        workout_type=day_in.workout_type,
        workout_plan_id=plan.id,
    )
    for eintrag in day_in.exercises:
        uebung = exercise_repo.get(eintrag.exercise_id)
        if uebung is None:
            raise HTTPException(
                status_code=404, detail=f"Uebung {eintrag.exercise_id} nicht gefunden"
            )
        # Die Uebung muss dem Besitzer des Plans gehoeren - sonst haette man
        # fremde Katalogeintraege im eigenen Plan.
        if uebung.user_id != plan.user_id:
            raise HTTPException(
                status_code=422,
                detail=f"Uebung '{uebung.title}' gehoert nicht zu User {plan.user_id}",
            )
        tag.exercise_links.append(TrainingDayExercise(**eintrag.model_dump()))
    return repo.create(tag)


@router.get("", response_model=list[TrainingDayPublic])
def read_training_days(
    repo: TrainingDayRepoDep,
    workout_plan_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[TrainingDay]:
    if workout_plan_id is not None:
        return repo.list_by_plan(workout_plan_id)
    return repo.list(skip=skip, limit=limit)


@router.get("/{training_day_id}", response_model=TrainingDayWithExercises)
def read_training_day(training_day_id: int, repo: TrainingDayRepoDep) -> TrainingDay:
    """Tag samt Uebungen und Vorgaben - das laedt der Workout-Screen beim Start."""
    tag = repo.get_with_exercises(training_day_id)
    if tag is None:
        raise HTTPException(
            status_code=404, detail=f"Trainingstag {training_day_id} nicht gefunden"
        )
    return tag


@router.patch("/{training_day_id}", response_model=TrainingDayPublic)
def update_training_day(
    training_day_id: int, day_in: TrainingDayUpdate, repo: TrainingDayRepoDep
) -> TrainingDay:
    tag = _hole_tag(training_day_id, repo)
    daten = day_in.model_dump(exclude_unset=True)
    neue_position = daten.get("position")
    if neue_position is not None and neue_position != tag.position:
        belegt = [
            anderer
            for anderer in repo.list_by_plan(tag.workout_plan_id)
            if anderer.position == neue_position and anderer.id != tag.id
        ]
        if belegt:
            raise HTTPException(
                status_code=409,
                detail=f"Position {neue_position} ist in diesem Plan schon belegt",
            )
    return repo.update(tag, daten)


@router.delete("/{training_day_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_training_day(training_day_id: int, repo: TrainingDayRepoDep) -> None:
    """Loescht den Tag. Bereits absolvierte Einheiten bleiben erhalten und
    gelten danach als freies Training (training_day_id wird NULL)."""
    repo.delete(_hole_tag(training_day_id, repo))


@router.post(
    "/{training_day_id}/exercises",
    response_model=TrainingDayExercisePublic,
    status_code=status.HTTP_201_CREATED,
)
def add_exercise_to_day(
    training_day_id: int,
    link_in: TrainingDayExerciseCreate,
    repo: TrainingDayRepoDep,
    exercise_repo: ExerciseRepoDep,
    plan_repo: WorkoutPlanRepoDep,
) -> TrainingDayExercise:
    """Setzt eine Katalog-Uebung mit Vorgabe ("3x8-10") auf den Trainingstag."""
    tag = _hole_tag(training_day_id, repo)
    uebung = exercise_repo.get(link_in.exercise_id)
    if uebung is None:
        raise HTTPException(
            status_code=404, detail=f"Uebung {link_in.exercise_id} nicht gefunden"
        )
    plan = plan_repo.get(tag.workout_plan_id)
    if plan is not None and uebung.user_id != plan.user_id:
        raise HTTPException(
            status_code=422,
            detail=f"Uebung '{uebung.title}' gehoert nicht zu User {plan.user_id}",
        )
    # Bewusst keine Duplikatspruefung: dieselbe Uebung darf an einem Tag
    # mehrfach stehen (schwer am Anfang, leicht am Ende). Jeder Eintrag ist
    # ein eigener Platz mit eigener Vorgabe.
    return repo.add_exercise(
        TrainingDayExercise(training_day_id=tag.id, **link_in.model_dump())
    )


@router.patch(
    "/{training_day_id}/exercises/{link_id}",
    response_model=TrainingDayExercisePublic,
)
def update_day_exercise(
    training_day_id: int,
    link_id: int,
    link_in: TrainingDayExerciseUpdate,
    repo: TrainingDayRepoDep,
) -> TrainingDayExercise:
    """Aendert die Vorgabe, z.B. von 3x8-10 auf 4x6-8.

    Adressiert wird der Platz ueber seine id, nicht ueber die Uebung: an
    einem Tag koennen mehrere Plaetze dieselbe Uebung tragen.
    """
    link = _hole_platz(training_day_id, link_id, repo)
    daten = link_in.model_dump(exclude_unset=True)
    minimum = daten.get("target_reps_min", link.target_reps_min)
    maximum = daten.get("target_reps_max", link.target_reps_max)
    if minimum is not None and maximum is not None and maximum < minimum:
        raise HTTPException(
            status_code=422,
            detail="target_reps_max darf nicht kleiner als target_reps_min sein",
        )
    return repo.update_exercise_link(link, daten)


@router.delete(
    "/{training_day_id}/exercises/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_exercise_from_day(
    training_day_id: int, link_id: int, repo: TrainingDayRepoDep
) -> None:
    """Nimmt den Platz vom Plan. Der Katalogeintrag und die bereits
    protokollierten Saetze bleiben bestehen - die Saetze verlieren nur ihren
    Bezug auf diesen Platz."""
    repo.remove_exercise(_hole_platz(training_day_id, link_id, repo))

"""Tests der Repo-Schicht - ohne HTTP, direkt gegen die Session."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.entities import Exercise, Set, User, Workout, WorkoutPlan
from app.repositories import (
    ExerciseRepo,
    SetRepo,
    UserRepo,
    WorkoutPlanRepo,
    WorkoutRepo,
)


def _make_user(session: Session) -> User:
    return UserRepo(session).create(User(name="Daniel", age=30, weight=80.5))


def test_create_setzt_id(session: Session) -> None:
    user = _make_user(session)
    assert user.id is not None


def test_get_liefert_none_statt_fehler(session: Session) -> None:
    assert UserRepo(session).get(9999) is None


def test_update_aendert_nur_uebergebene_felder(session: Session) -> None:
    repo = UserRepo(session)
    user = _make_user(session)
    repo.update(user, {"weight": 82.0})
    assert user.weight == 82.0
    assert user.name == "Daniel"  # unveraendert
    assert user.age == 30


def test_get_with_exercises_laedt_verschachtelt(session: Session) -> None:
    user = _make_user(session)
    plan = WorkoutPlanRepo(session).create(
        WorkoutPlan(title="Push/Pull", training_days=4, user_id=user.id)
    )
    exercise = ExerciseRepo(session).create(
        Exercise(title="Bankdruecken", weighted=True, workout_plan_id=plan.id)
    )
    workout = WorkoutRepo(session).create(
        Workout(date=datetime.now(timezone.utc), workout_plan_id=plan.id)
    )
    SetRepo(session).create(
        Set(repetitions=8, weight=60, exercise_id=exercise.id, workout_id=workout.id)
    )
    SetRepo(session).create(
        Set(repetitions=6, weight=70, exercise_id=exercise.id, workout_id=workout.id)
    )

    loaded = WorkoutPlanRepo(session).get_with_exercises(plan.id)
    assert loaded is not None
    assert len(loaded.exercises) == 1
    assert len(loaded.exercises[0].sets) == 2


def test_workout_traegt_seine_saetze(session: Session) -> None:
    """Der neue Pfad Workout -> Saetze: das Protokoll einer Einheit."""
    user = _make_user(session)
    plan = WorkoutPlanRepo(session).create(
        WorkoutPlan(title="Ganzkoerper", training_days=3, user_id=user.id)
    )
    exercise = ExerciseRepo(session).create(
        Exercise(title="Kniebeuge", weighted=True, workout_plan_id=plan.id)
    )
    montag = WorkoutRepo(session).create(
        Workout(date=datetime(2026, 8, 24, tzinfo=timezone.utc), workout_plan_id=plan.id)
    )
    donnerstag = WorkoutRepo(session).create(
        Workout(date=datetime(2026, 8, 27, tzinfo=timezone.utc), workout_plan_id=plan.id)
    )
    SetRepo(session).create(
        Set(repetitions=8, weight=60, exercise_id=exercise.id, workout_id=montag.id)
    )
    SetRepo(session).create(
        Set(repetitions=8, weight=70, exercise_id=exercise.id, workout_id=donnerstag.id)
    )

    # Tagesprotokoll: nur die Saetze der jeweiligen Einheit
    assert len(SetRepo(session).list_by_workout(montag.id)) == 1
    assert SetRepo(session).list_by_workout(montag.id)[0].weight == 60

    # Verlauf: beide Saetze derselben Uebung ueber die Einheiten hinweg
    assert len(SetRepo(session).list_by_exercise(exercise.id)) == 2

    geladen = WorkoutRepo(session).get_with_sets(donnerstag.id)
    assert geladen is not None
    assert len(geladen.sets) == 1
    assert geladen.sets[0].weight == 70


def test_delete_workout_loescht_nur_dessen_saetze(session: Session) -> None:
    """Eine Einheit zu loeschen darf den Plan und die Uebung nicht mitreissen."""
    user = _make_user(session)
    plan = WorkoutPlanRepo(session).create(
        WorkoutPlan(title="Plan", training_days=3, user_id=user.id)
    )
    exercise = ExerciseRepo(session).create(
        Exercise(title="Kniebeuge", workout_plan_id=plan.id)
    )
    workout = WorkoutRepo(session).create(
        Workout(date=datetime.now(timezone.utc), workout_plan_id=plan.id)
    )
    SetRepo(session).create(
        Set(repetitions=5, weight=100, exercise_id=exercise.id, workout_id=workout.id)
    )

    WorkoutRepo(session).delete(workout)

    assert SetRepo(session).count() == 0
    assert ExerciseRepo(session).count() == 1
    assert WorkoutPlanRepo(session).count() == 1


def test_list_by_user_findet_workouts_ueber_join(session: Session) -> None:
    user = _make_user(session)
    plan = WorkoutPlanRepo(session).create(
        WorkoutPlan(title="Ganzkoerper", training_days=3, user_id=user.id)
    )
    WorkoutRepo(session).create(
        Workout(date=datetime.now(timezone.utc), workout_plan_id=plan.id)
    )

    assert len(WorkoutRepo(session).list_by_user(user.id)) == 1
    assert WorkoutRepo(session).list_by_user(9999) == []


def test_delete_user_raeumt_abhaengige_daten_auf(session: Session) -> None:
    user = _make_user(session)
    plan = WorkoutPlanRepo(session).create(
        WorkoutPlan(title="Plan", training_days=3, user_id=user.id)
    )
    exercise = ExerciseRepo(session).create(
        Exercise(title="Kniebeuge", workout_plan_id=plan.id)
    )
    workout = WorkoutRepo(session).create(
        Workout(date=datetime.now(timezone.utc), workout_plan_id=plan.id)
    )
    SetRepo(session).create(
        Set(repetitions=5, weight=100, exercise_id=exercise.id, workout_id=workout.id)
    )

    UserRepo(session).delete(user)

    assert WorkoutPlanRepo(session).count() == 0
    assert ExerciseRepo(session).count() == 0
    assert WorkoutRepo(session).count() == 0
    assert SetRepo(session).count() == 0

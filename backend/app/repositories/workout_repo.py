from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.time import as_utc
from app.entities.workout import Workout
from app.entities.workout_plan import WorkoutPlan
from app.repositories.base_repo import BaseRepo


class WorkoutRepo(BaseRepo[Workout]):
    def __init__(self, session: Session):
        super().__init__(session, Workout)

    def list_by_plan(self, workout_plan_id: int, *, skip: int = 0, limit: int = 100) -> list[Workout]:
        statement = (
            select(Workout)
            .where(Workout.workout_plan_id == workout_plan_id)
            .order_by(Workout.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def list_by_user(
        self,
        user_id: int,
        *,
        since: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Workout]:
        """Trainingshistorie eines Users ueber alle seine Plaene hinweg.

        join verbindet workout und workout_plan, um ueber user_id filtern zu
        koennen - workout selbst kennt den User ja nicht direkt.
        """
        statement = (
            select(Workout)
            .join(WorkoutPlan, Workout.workout_plan_id == WorkoutPlan.id)
            .where(WorkoutPlan.user_id == user_id)
        )
        if since is not None:
            statement = statement.where(Workout.date >= since)
        statement = statement.order_by(Workout.date.desc()).offset(skip).limit(limit)
        return list(self.session.scalars(statement).all())

    def get_with_sets(self, id: int) -> Workout | None:
        """Einheit samt absolvierter Saetze - eine Query statt N+1."""
        statement = (
            select(Workout)
            .where(Workout.id == id)
            .options(selectinload(Workout.sets))
        )
        return self.session.scalars(statement).first()

    def auto_close_stale(self, max_duration: timedelta) -> int:
        """Schliesst Einheiten, die zu lange offen sind.

        Wer /finish vergisst, haette sonst eine Einheit, die ewig als
        "laeuft gerade" gilt. Das Ende wird auf start + max_duration
        gesetzt, nicht auf "jetzt" - die gemessene Dauer bleibt damit die
        Obergrenze und wird nicht durch die Vergesslichkeit aufgeblasen.

        Bewusst in Python statt als ein grosses UPDATE mit Datums-Arithmetik:
        so verhaelt es sich auf PostgreSQL und dem SQLite der Tests gleich.
        Es sind ohnehin nur die wenigen offenen Einheiten betroffen.
        """
        grenze = datetime.now(timezone.utc) - max_duration
        offen = self.session.scalars(
            select(Workout).where(
                Workout.started_at.is_not(None),
                Workout.finished_at.is_(None),
            )
        ).all()

        geschlossen = 0
        for workout in offen:
            start = as_utc(workout.started_at)
            if start is not None and start < grenze:
                workout.finished_at = start + max_duration
                geschlossen += 1
        if geschlossen:
            self.session.commit()
        return geschlossen

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.entities.set import Set
from app.entities.workout import Workout
from app.entities.workout_plan import WorkoutPlan
from app.repositories.base_repo import BaseRepo


class SetRepo(BaseRepo[Set]):
    def __init__(self, session: Session):
        super().__init__(session, Set)

    def list_by_exercise(self, exercise_id: int) -> list[Set]:
        statement = select(Set).where(Set.exercise_id == exercise_id).order_by(Set.id)
        return list(self.session.scalars(statement).all())

    def list_by_workout(self, workout_id: int) -> list[Set]:
        """Alle Saetze einer Trainingseinheit - das Protokoll eines Tages."""
        statement = select(Set).where(Set.workout_id == workout_id).order_by(Set.id)
        return list(self.session.scalars(statement).all())

    def list_by_exercise_and_workout(self, exercise_id: int, workout_id: int) -> list[Set]:
        statement = (
            select(Set)
            .where(Set.exercise_id == exercise_id, Set.workout_id == workout_id)
            .order_by(Set.id)
        )
        return list(self.session.scalars(statement).all())

    def list_for_analysis(self, user_id: int) -> list[Set]:
        """Alle Saetze, die in die Auswertung zaehlen.

        Zwei Filter:
          - attended: eine ausgefallene Einheit hat ohnehin keine Saetze,
            der Filter schuetzt aber vor nachtraeglich eingetragenen.
          - training_day_id IS NOT NULL: freie Trainings ("Custom") bleiben
            draussen. Sie entstehen aus Mangel an Geraeten und wuerden den
            Trend verzerren - in der Historie tauchen sie trotzdem auf.

        Die Monatszuordnung passiert danach in Python: date_trunc und
        AT TIME ZONE gibt es nur in PostgreSQL, die Tests laufen aber auf
        SQLite. Bei den Datenmengen eines einzelnen Users kostet das nichts.
        """
        statement = (
            select(Set)
            .join(Workout, Set.workout_id == Workout.id)
            .join(WorkoutPlan, Workout.workout_plan_id == WorkoutPlan.id)
            .where(
                WorkoutPlan.user_id == user_id,
                Workout.training_day_id.is_not(None),
                Workout.attended.is_(True),
            )
            .options(selectinload(Set.exercise), selectinload(Set.workout))
        )
        return list(self.session.scalars(statement).all())

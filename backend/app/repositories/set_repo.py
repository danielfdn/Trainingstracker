from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.set import Set
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

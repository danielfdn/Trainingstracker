from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.entities.exercise import Exercise
from app.repositories.base_repo import BaseRepo


class ExerciseRepo(BaseRepo[Exercise]):
    def __init__(self, session: Session):
        super().__init__(session, Exercise)

    def list_by_plan(self, workout_plan_id: int) -> list[Exercise]:
        statement = (
            select(Exercise)
            .where(Exercise.workout_plan_id == workout_plan_id)
            .order_by(Exercise.id)
        )
        return list(self.session.scalars(statement).all())

    def get_with_sets(self, id: int) -> Exercise | None:
        statement = (
            select(Exercise)
            .where(Exercise.id == id)
            .options(selectinload(Exercise.sets))
        )
        return self.session.scalars(statement).first()

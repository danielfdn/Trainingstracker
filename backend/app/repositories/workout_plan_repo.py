from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.entities.exercise import Exercise
from app.entities.workout_plan import WorkoutPlan
from app.repositories.base_repo import BaseRepo


class WorkoutPlanRepo(BaseRepo[WorkoutPlan]):
    def __init__(self, session: Session):
        super().__init__(session, WorkoutPlan)

    def list_by_user(self, user_id: int, *, skip: int = 0, limit: int = 100) -> list[WorkoutPlan]:
        statement = (
            select(WorkoutPlan)
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.starting_date.desc().nulls_last(), WorkoutPlan.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def get_with_exercises(self, id: int) -> WorkoutPlan | None:
        """Plan mit Uebungen UND deren Saetzen - genau eine Abfrage pro Ebene."""
        statement = (
            select(WorkoutPlan)
            .where(WorkoutPlan.id == id)
            .options(selectinload(WorkoutPlan.exercises).selectinload(Exercise.sets))
        )
        return self.session.scalars(statement).first()

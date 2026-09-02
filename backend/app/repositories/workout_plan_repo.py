from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.entities.training_day import TrainingDay
from app.entities.training_day_exercise import TrainingDayExercise
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

    def get_with_days(self, id: int) -> WorkoutPlan | None:
        """Plan mit Trainingstagen, deren Uebungen und Vorgaben.

        Drei Ebenen, aber dank selectinload drei Abfragen statt einer pro Tag
        und einer pro Uebung.
        """
        statement = (
            select(WorkoutPlan)
            .where(WorkoutPlan.id == id)
            .options(
                selectinload(WorkoutPlan.training_days)
                .selectinload(TrainingDay.exercise_links)
                .selectinload(TrainingDayExercise.exercise)
            )
        )
        return self.session.scalars(statement).first()

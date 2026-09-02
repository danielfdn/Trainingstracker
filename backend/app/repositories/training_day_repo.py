from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.entities.training_day import TrainingDay
from app.entities.training_day_exercise import TrainingDayExercise
from app.repositories.base_repo import BaseRepo


class TrainingDayRepo(BaseRepo[TrainingDay]):
    def __init__(self, session: Session):
        super().__init__(session, TrainingDay)

    def list_by_plan(self, workout_plan_id: int) -> list[TrainingDay]:
        statement = (
            select(TrainingDay)
            .where(TrainingDay.workout_plan_id == workout_plan_id)
            .order_by(TrainingDay.position)
        )
        return list(self.session.scalars(statement).all())

    def get_with_exercises(self, id: int) -> TrainingDay | None:
        """Tag samt Uebungen und Vorgaben - eine Abfrage pro Ebene statt N+1."""
        statement = (
            select(TrainingDay)
            .where(TrainingDay.id == id)
            .options(
                selectinload(TrainingDay.exercise_links).selectinload(
                    TrainingDayExercise.exercise
                )
            )
        )
        return self.session.scalars(statement).first()

    def get_link(self, training_day_id: int, exercise_id: int) -> TrainingDayExercise | None:
        return self.session.get(TrainingDayExercise, (training_day_id, exercise_id))

    def add_exercise(self, link: TrainingDayExercise) -> TrainingDayExercise:
        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link

    def update_exercise_link(
        self, link: TrainingDayExercise, data: dict
    ) -> TrainingDayExercise:
        """Eigene Methode statt BaseRepo.update: das Link-Objekt ist ein
        anderer Typ als TrainingDay, ueber den dieses Repo generisch ist."""
        for field, value in data.items():
            setattr(link, field, value)
        self.session.add(link)
        self.session.commit()
        self.session.refresh(link)
        return link

    def remove_exercise(self, link: TrainingDayExercise) -> None:
        self.session.delete(link)
        self.session.commit()

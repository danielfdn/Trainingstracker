from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.entities.exercise import Exercise
from app.repositories.base_repo import BaseRepo


class ExerciseRepo(BaseRepo[Exercise]):
    def __init__(self, session: Session):
        super().__init__(session, Exercise)

    def list_by_user(self, user_id: int, *, skip: int = 0, limit: int = 100) -> list[Exercise]:
        """Der persoenliche Uebungskatalog, alphabetisch fuer die Auswahlliste."""
        statement = (
            select(Exercise)
            .where(Exercise.user_id == user_id)
            .order_by(Exercise.title)
            .offset(skip)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def get_by_title(self, user_id: int, title: str) -> Exercise | None:
        """Sucht ohne Ruecksicht auf Gross-/Kleinschreibung.

        "Bankdruecken" und "bankdruecken" sind dieselbe Uebung - wuerden sie
        als zwei Eintraege landen, zerfiele der Verlauf in zwei Haelften.
        """
        statement = select(Exercise).where(
            Exercise.user_id == user_id,
            func.lower(Exercise.title) == title.lower(),
        )
        return self.session.scalars(statement).first()

    def get_or_create(self, user_id: int, title: str, *, weighted: bool = True) -> Exercise:
        """Fuer das freie Training: vorhandene Uebung nehmen oder neu anlegen.

        Damit kann der User im Custom-Workout einfach einen Namen tippen,
        ohne vorher in die Katalogverwaltung zu wechseln.
        """
        vorhanden = self.get_by_title(user_id, title)
        if vorhanden is not None:
            return vorhanden
        return self.create(Exercise(title=title, weighted=weighted, user_id=user_id))

    def list_by_plan(self, workout_plan_id: int) -> list[Exercise]:
        """Alle Uebungen, die in irgendeinem Trainingstag dieses Plans vorkommen.

        Geht ueber zwei Joins, weil eine Uebung dem Plan nicht mehr direkt
        gehoert - sie haengt am Trainingstag. distinct, weil dieselbe Uebung
        an mehreren Tagen stehen darf.
        """
        from app.entities.training_day import TrainingDay
        from app.entities.training_day_exercise import TrainingDayExercise

        statement = (
            select(Exercise)
            .join(TrainingDayExercise, TrainingDayExercise.exercise_id == Exercise.id)
            .join(TrainingDay, TrainingDay.id == TrainingDayExercise.training_day_id)
            .where(TrainingDay.workout_plan_id == workout_plan_id)
            .order_by(Exercise.title)
            .distinct()
        )
        return list(self.session.scalars(statement).all())

    def get_with_sets(self, id: int) -> Exercise | None:
        statement = (
            select(Exercise)
            .where(Exercise.id == id)
            .options(selectinload(Exercise.sets))
        )
        return self.session.scalars(statement).first()

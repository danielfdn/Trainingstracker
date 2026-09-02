from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.training_day import TrainingDay
    from app.entities.user import User
    from app.entities.workout import Workout


class WorkoutPlan(Base):
    __tablename__ = "workout_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    starting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ending_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("appuser.id", ondelete="CASCADE"), nullable=False
    )

    # foreign_keys: appuser.active_workout_plan_id ist der zweite Weg zwischen
    # den beiden Tabellen - ohne die Angabe waere die Beziehung mehrdeutig.
    user: Mapped["User"] = relationship(
        back_populates="workout_plans",
        foreign_keys=[user_id],
    )
    # Frueher lag hier eine flache Uebungsliste und daneben eine Zahl
    # "training_days". Beides zusammen konnte sich widersprechen (Plan sagt 4,
    # hat aber 3 Tage) und konnte nicht ausdruecken, welche Uebung an welchem
    # Tag drankommt. Jetzt IST die Anzahl der Trainingstage die Zahl.
    training_days: Mapped[list["TrainingDay"]] = relationship(
        back_populates="workout_plan",
        cascade="all, delete-orphan",
        order_by="TrainingDay.position",
    )
    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="workout_plan",
        cascade="all, delete-orphan",
    )

    @property
    def training_days_per_week(self) -> int:
        """Abgeleitet statt gespeichert - kann so nicht von der Realitaet abweichen."""
        return len(self.training_days)

    def __repr__(self) -> str:
        return f"WorkoutPlan(id={self.id!r}, title={self.title!r})"

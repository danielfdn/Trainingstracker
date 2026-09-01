from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.exercise import Exercise
    from app.entities.user import User
    from app.entities.workout import Workout


class WorkoutPlan(Base):
    __tablename__ = "workout_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    training_days: Mapped[int] = mapped_column(Integer, nullable=False)
    starting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ending_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("appuser.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="workout_plans")
    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="workout_plan",
        cascade="all, delete-orphan",
    )
    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="workout_plan",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"WorkoutPlan(id={self.id!r}, title={self.title!r})"

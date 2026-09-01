from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.set import Set
    from app.entities.workout_plan import WorkoutPlan


class Exercise(Base):
    __tablename__ = "exercise"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    weighted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan.id", ondelete="CASCADE"), nullable=False
    )

    workout_plan: Mapped["WorkoutPlan"] = relationship(back_populates="exercises")
    sets: Mapped[list["Set"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Exercise(id={self.id!r}, title={self.title!r}, weighted={self.weighted!r})"

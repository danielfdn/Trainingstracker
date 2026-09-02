from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.training_day_exercise import TrainingDayExercise
    from app.entities.workout import Workout
    from app.entities.workout_plan import WorkoutPlan


class TrainingDay(Base):
    """Ein Trainingstag innerhalb eines Plans, z.B. "Tag 1 - Push".

    Ein Plan besteht nicht aus einer flachen Uebungsliste, sondern aus so
    vielen Trainingstagen, wie pro Woche trainiert wird. Jeder Tag hat einen
    Typ ("Push", "Pull", "Legs") und seine eigenen Uebungen.
    """

    __tablename__ = "training_day"
    __table_args__ = (
        # Zwei Tage an derselben Position waeren nicht sortierbar.
        UniqueConstraint("workout_plan_id", "position", name="training_day_position_einmalig"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Reihenfolge im Plan (1..n). Der Typ darf sich wiederholen - ein 4er-Split
    # kann zweimal "Push" enthalten, mit unterschiedlichen Uebungen.
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Freitext statt Enum: Splits sind zu verschieden (Push/Pull/Legs,
    # Oberkoerper/Unterkoerper, Ganzkoerper, Arme), um sie fest zu verdrahten.
    workout_type: Mapped[str] = mapped_column(String(50), nullable=False)

    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan.id", ondelete="CASCADE"), nullable=False
    )

    workout_plan: Mapped["WorkoutPlan"] = relationship(back_populates="training_days")
    exercise_links: Mapped[list["TrainingDayExercise"]] = relationship(
        back_populates="training_day",
        cascade="all, delete-orphan",
        order_by="TrainingDayExercise.position",
    )
    workouts: Mapped[list["Workout"]] = relationship(back_populates="training_day")

    def __repr__(self) -> str:
        return (
            f"TrainingDay(id={self.id!r}, position={self.position!r}, "
            f"workout_type={self.workout_type!r})"
        )

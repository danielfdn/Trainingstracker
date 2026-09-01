from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.exercise import Exercise
    from app.entities.workout import Workout


class Set(Base):
    # "set" ist in SQL ein reserviertes Wort (SET-Klausel im UPDATE),
    # deshalb heisst die Tabelle "exercise_set".
    __tablename__ = "exercise_set"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False)
    # nullable, weil Koerpergewichtsuebungen (weighted=False) kein Gewicht haben
    weight: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), nullable=False
    )
    # Ein Satz ist immer etwas, das in einer konkreten Trainingseinheit
    # tatsaechlich gemacht wurde - ohne Workout gibt es ihn nicht.
    # exercise_id sagt "welche Uebung", workout_id sagt "an welchem Tag".
    workout_id: Mapped[int] = mapped_column(
        # Index, weil "alle Saetze dieser Einheit" die haeufigste Abfrage wird.
        ForeignKey("workout.id", ondelete="CASCADE"), nullable=False, index=True
    )

    exercise: Mapped["Exercise"] = relationship(back_populates="sets")
    workout: Mapped["Workout"] = relationship(back_populates="sets")

    def __repr__(self) -> str:
        return (
            f"Set(id={self.id!r}, repetitions={self.repetitions!r}, "
            f"weight={self.weight!r}, workout_id={self.workout_id!r})"
        )

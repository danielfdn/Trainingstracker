from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.exercise import Exercise
    from app.entities.set import Set
    from app.entities.training_day import TrainingDay


class TrainingDayExercise(Base):
    """Verbindet einen Trainingstag mit einer Uebung aus dem Katalog.

    Kein reines Zuordnungspaar, sondern ein Assoziationsobjekt: Hier stehen
    zusaetzlich die Vorgaben ("Bankdruecken 3x8-10"). Die Vorgabe gehoert
    weder zum Tag noch zur Uebung allein, sondern genau zu dieser Kombination -
    dieselbe Uebung kann an einem schweren Tag 5x5 und an einem leichten
    3x12-15 vorgeben.

    Eine Uebung darf an einem Tag MEHRFACH stehen - z.B. Bankdruecken schwer
    am Anfang und leicht am Ende. Deshalb ist der Primaerschluessel eine
    eigene id und nicht das Paar (Tag, Uebung): jeder Eintrag ist ein eigener
    Platz im Ablauf des Tages, mit eigener Vorgabe und eigenen Saetzen.
    """

    __tablename__ = "training_day_exercise"
    __table_args__ = (
        CheckConstraint(
            "target_reps_max IS NULL OR target_reps_min IS NULL "
            "OR target_reps_max >= target_reps_min",
            name="rep_range_richtig_herum",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    training_day_id: Mapped[int] = mapped_column(
        ForeignKey("training_day.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercise.id", ondelete="CASCADE"), nullable=False
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_sets: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # Eine Spanne statt einer festen Zahl: "8-10" ist die uebliche Vorgabe.
    # Beide nullable, damit ein Plan auch ohne Wiederholungsvorgabe auskommt.
    target_reps_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps_max: Mapped[int | None] = mapped_column(Integer, nullable=True)

    training_day: Mapped["TrainingDay"] = relationship(back_populates="exercise_links")
    exercise: Mapped["Exercise"] = relationship(back_populates="training_day_links")
    # Die Saetze, die auf genau diesen Platz protokolliert wurden. Faellt der
    # Platz aus dem Plan, bleiben die Saetze bestehen und verlieren nur den
    # Bezug (ondelete=SET NULL in Set) - Trainingshistorie wird nie geloescht.
    sets: Mapped[list["Set"]] = relationship(back_populates="training_day_exercise")

    def __repr__(self) -> str:
        return (
            f"TrainingDayExercise(id={self.id!r}, "
            f"training_day_id={self.training_day_id!r}, "
            f"exercise_id={self.exercise_id!r}, target_sets={self.target_sets!r})"
        )

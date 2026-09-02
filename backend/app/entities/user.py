from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.exercise import Exercise
    from app.entities.workout_plan import WorkoutPlan


class User(Base):
    # "user" ist in PostgreSQL ein reserviertes Wort - daher "appuser"
    # (so hiess die Tabelle auch schon im alten SQL-Code).
    __tablename__ = "appuser"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    # Numeric statt Float: exakte Dezimalwerte, keine Rundungsfehler beim Gewicht
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Genau ein aktiver Plan - als Fremdschluessel, nicht als Flag am Plan.
    # Ein "is_active"-Flag koennte bei zwei Plaenen gleichzeitig True sein;
    # eine einzelne Spalte kann das strukturell nicht.
    #
    # use_alter: appuser zeigt auf workout_plan und workout_plan zeigt zurueck
    # auf appuser. Ohne use_alter gaebe es keine Reihenfolge, in der sich die
    # beiden Tabellen anlegen liessen - so wird der Fremdschluessel per
    # nachtraeglichem ALTER TABLE ergaenzt.
    active_workout_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "workout_plan.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_appuser_active_workout_plan",
        ),
        nullable=True,
    )

    # Ein User sammelt ueber die Zeit mehrere Plaene an (Trainingshistorie).
    # Loeschen des Users loescht seine Plaene mit.
    # foreign_keys ist noetig, weil es zwei Wege zwischen appuser und
    # workout_plan gibt (user_id und active_workout_plan_id) - SQLAlchemy
    # kann sonst nicht wissen, welcher gemeint ist.
    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="WorkoutPlan.user_id",
    )
    active_workout_plan: Mapped["WorkoutPlan | None"] = relationship(
        foreign_keys=[active_workout_plan_id],
        post_update=True,
    )
    # Der persoenliche Uebungskatalog - planuebergreifend.
    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, age={self.age!r})"

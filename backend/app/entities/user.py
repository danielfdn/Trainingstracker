from typing import TYPE_CHECKING

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
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

    # Ein User sammelt ueber die Zeit mehrere Plaene an (Trainingshistorie).
    # Loeschen des Users loescht seine Plaene mit.
    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, age={self.age!r})"

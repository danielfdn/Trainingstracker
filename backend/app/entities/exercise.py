from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.set import Set
    from app.entities.training_day_exercise import TrainingDayExercise
    from app.entities.user import User


class Exercise(Base):
    """Eine Uebung im persoenlichen Katalog des Users.

    Bewusst NICHT an einen Plan gehaengt: Die Auswertung vergleicht Monate,
    die verschiedenen Plaenen angehoeren (z.B. 09/25 gegen 04/26). Waere
    "Bankdruecken" pro Plan eine eigene Zeile mit eigener id, gaebe es nichts,
    worueber sich die beiden Monate verbinden liessen - der Vergleich bliebe
    still leer. Ein Katalogeintrag ueberlebt den Planwechsel.
    """

    __tablename__ = "exercise"
    __table_args__ = (
        # Zwei Eintraege "Bankdruecken" beim selben User wuerden den Verlauf
        # in zwei Haelften zerlegen.
        UniqueConstraint("user_id", "title", name="exercise_titel_je_user_einmalig"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    weighted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("appuser.id", ondelete="CASCADE"), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="exercises")
    # In welchen Trainingstagen diese Uebung vorkommt (samt Vorgaben).
    training_day_links: Mapped[list["TrainingDayExercise"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
    sets: Mapped[list["Set"]] = relationship(
        back_populates="exercise",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Exercise(id={self.id!r}, title={self.title!r}, weighted={self.weighted!r})"

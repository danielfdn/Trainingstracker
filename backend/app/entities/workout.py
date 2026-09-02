from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import as_utc
from app.entities.base import Base

if TYPE_CHECKING:
    from app.entities.set import Set
    from app.entities.training_day import TrainingDay
    from app.entities.workout_plan import WorkoutPlan


class Workout(Base):
    """Eine einzelne, tatsaechlich stattgefundene Trainingseinheit."""

    __tablename__ = "workout"
    __table_args__ = (
        # Die Regeln stehen zusaetzlich in der DB, nicht nur in Pydantic:
        # so kann auch ein Skript oder DataGrip keinen unmoeglichen
        # Zeitraum hinterlegen.
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="workout_finish_braucht_start",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="workout_ende_nach_start",
        ),
        # Benannt, nicht unique=True an der Spalte: ein unbenannter Constraint
        # laesst sich in downgrade() nicht wieder loeschen.
        UniqueConstraint("client_uuid", name="workout_client_uuid_einmalig"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # timezone=True: speichert den Zeitpunkt eindeutig, unabhaengig davon,
    # in welcher Zeitzone das iPhone gerade steht
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Beide bewusst nullable und getrennt von "date":
    #   started_at is None                  -> Einheit noch nicht begonnen
    #   started_at gesetzt, finished_at None -> laeuft gerade
    #   beide gesetzt                        -> abgeschlossen, Dauer bekannt
    # Eine ausgefallene Einheit (attended=False) hat schlicht keine Zeiten.
    # Die Dauer wird NICHT gespeichert, sondern aus der Differenz berechnet -
    # ein gespeicherter Wert koennte sonst von den Zeitstempeln abweichen.
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Koerpergewicht am Tag der Einheit. Bewusst hier kopiert und nicht ueber
    # appuser.weight gelesen: dort steht nur der AKTUELLE Wert, den ein PATCH
    # ueberschreibt. Wuerde das Log ihn nachschlagen, stuende neben einer
    # Einheit vom Maerz das Gewicht von heute - das saehe aus wie Historie,
    # waere aber keine. Der Wert wird beim Anlegen der Einheit aus dem
    # Benutzerprofil uebernommen; eingeben muss ihn niemand.
    # nullable, weil Einheiten aus der Zeit vor dieser Spalte keinen
    # ehrlichen Wert haben - erfinden waere schlimmer als leer lassen.
    body_weight: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Vom Client vergebene Kennung fuer die Offline-Synchronisation.
    # Wenn der Server schreibt, die Antwort aber im Funkloch verloren geht,
    # wiederholt das Handy den Aufruf - ohne diese Kennung stuende die
    # Einheit danach zweimal im Log. UNIQUE macht die Wiederholung wirkungslos.
    client_uuid: Mapped[str | None] = mapped_column(String(36), nullable=True)

    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan.id", ondelete="CASCADE"), nullable=False
    )
    # NULL bedeutet: freies Training ("Custom"), z.B. weil im Urlaubshotel
    # die Geraete fehlten. Bewusst kein zusaetzliches is_custom-Flag - zwei
    # Spalten koennten sich widersprechen (custom=True und trotzdem ein Tag).
    # Die Auswertung filtert diese Einheiten heraus, die Historie zeigt sie.
    training_day_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_day.id", ondelete="SET NULL"), nullable=True, index=True
    )

    workout_plan: Mapped["WorkoutPlan"] = relationship(back_populates="workouts")
    training_day: Mapped["TrainingDay | None"] = relationship(back_populates="workouts")
    # Die in dieser Einheit tatsaechlich absolvierten Saetze.
    sets: Mapped[list["Set"]] = relationship(
        back_populates="workout",
        cascade="all, delete-orphan",
    )

    @property
    def is_custom(self) -> bool:
        """Freies Training ohne Vorgabe - zaehlt nicht in die Auswertung."""
        return self.training_day_id is None

    @property
    def duration_seconds(self) -> int | None:
        """Dauer der Einheit, oder None solange sie nicht abgeschlossen ist."""
        if self.started_at is None or self.finished_at is None:
            return None
        return int((as_utc(self.finished_at) - as_utc(self.started_at)).total_seconds())

    def __repr__(self) -> str:
        return f"Workout(id={self.id!r}, date={self.date!r}, attended={self.attended!r})"

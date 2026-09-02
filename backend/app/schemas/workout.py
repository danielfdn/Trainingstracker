from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.core.time import as_utc
from app.schemas.set import SetPublic


class WorkoutBase(BaseModel):
    date: datetime
    attended: bool = True
    comment: str = Field(default="", max_length=2000)
    # Normalerweise setzt man die beiden ueber /start und /finish. Beim
    # Anlegen sind sie trotzdem erlaubt, damit man eine vergangene Einheit
    # samt Zeiten nachtragen kann.
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @model_validator(mode="after")
    def check_zeitraum(self):
        if self.finished_at is not None:
            if self.started_at is None:
                raise ValueError(
                    "finished_at ohne started_at - eine Einheit kann nicht enden, "
                    "ohne begonnen zu haben"
                )
            if as_utc(self.finished_at) < as_utc(self.started_at):
                raise ValueError("finished_at darf nicht vor started_at liegen")
        return self


class WorkoutCreate(WorkoutBase):
    workout_plan_id: int
    # None = freies Training ("Custom"): der User stellt sich die Uebungen
    # selbst zusammen, weil z.B. Geraete fehlen.
    training_day_id: int | None = None


class WorkoutUpdate(BaseModel):
    """Alle Felder optional - die Pruefung der Zeitlogik passiert im Router,
    weil dort erst feststeht, wie der Datensatz nach dem PATCH aussieht."""

    date: datetime | None = None
    attended: bool | None = None
    comment: str | None = Field(default=None, max_length=2000)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    training_day_id: int | None = None


class WorkoutPublic(WorkoutBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_plan_id: int
    training_day_id: int | None = None

    @computed_field
    @property
    def is_custom(self) -> bool:
        """Freies Training - erscheint in der Historie, nicht in der Auswertung."""
        return self.training_day_id is None

    @computed_field
    @property
    def duration_seconds(self) -> int | None:
        """Abgeleitet, nicht gespeichert - None solange die Einheit laeuft."""
        if self.started_at is None or self.finished_at is None:
            return None
        return int((as_utc(self.finished_at) - as_utc(self.started_at)).total_seconds())

    @computed_field
    @property
    def duration(self) -> str | None:
        """Dauer als "01:43:32" - fertig zum Anzeigen, ohne Rechnerei im Frontend."""
        sekunden = self.duration_seconds
        if sekunden is None:
            return None
        stunden, rest = divmod(sekunden, 3600)
        minuten, sekunden = divmod(rest, 60)
        return f"{stunden:02d}:{minuten:02d}:{sekunden:02d}"

    @computed_field
    @property
    def is_running(self) -> bool:
        """True zwischen /start und /finish - das Frontend zeigt dann die
        laufende Uhr statt der Enddauer."""
        return self.started_at is not None and self.finished_at is None


class WorkoutWithSets(WorkoutPublic):
    """Einheit inklusive der Saetze, die darin absolviert wurden."""

    sets: list[SetPublic] = []

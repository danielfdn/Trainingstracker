from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.schemas.training_day import TrainingDayNested, TrainingDayWithExercises


class WorkoutPlanBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    starting_date: date | None = None
    ending_date: date | None = None

    @model_validator(mode="after")
    def check_date_order(self):
        if (
            self.starting_date is not None
            and self.ending_date is not None
            and self.ending_date < self.starting_date
        ):
            raise ValueError("ending_date darf nicht vor starting_date liegen")
        return self


class WorkoutPlanCreate(WorkoutPlanBase):
    user_id: int
    # Die Trainingstage lassen sich gleich mitschicken - beim Anlegen eines
    # Plans legt man ohnehin fest, an wie vielen Tagen was trainiert wird.
    training_days: list[TrainingDayNested] = []

    @model_validator(mode="after")
    def check_positions_einmalig(self):
        positionen = [tag.position for tag in self.training_days]
        if len(positionen) != len(set(positionen)):
            raise ValueError("zwei Trainingstage teilen sich dieselbe position")
        return self


class WorkoutPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    starting_date: date | None = None
    ending_date: date | None = None


class WorkoutPlanDuplicate(BaseModel):
    """Optionale Angaben beim Kopieren eines Plans."""

    # Ohne Angabe haengt der Endpunkt " (Copy)" an den Titel.
    title: str | None = Field(default=None, min_length=1, max_length=100)
    starting_date: date | None = None
    ending_date: date | None = None


class WorkoutPlanPublic(WorkoutPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class WorkoutPlanWithDays(WorkoutPlanPublic):
    """Plan inklusive Trainingstage und deren Uebungen - Detailansicht der PWA."""

    training_days: list[TrainingDayWithExercises] = []

    @computed_field
    @property
    def training_days_per_week(self) -> int:
        """Abgeleitet aus der Anzahl der Tage, nicht separat gespeichert."""
        return len(self.training_days)

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.exercise import ExerciseWithSets


class WorkoutPlanBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    training_days: int = Field(gt=0, le=7)
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


class WorkoutPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    training_days: int | None = Field(default=None, gt=0, le=7)
    starting_date: date | None = None
    ending_date: date | None = None


class WorkoutPlanPublic(WorkoutPlanBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int


class WorkoutPlanWithExercises(WorkoutPlanPublic):
    """Plan inklusive seiner Uebungen - fuer die Detailansicht in der PWA."""

    exercises: list[ExerciseWithSets] = []

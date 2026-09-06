from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.exercise import ExercisePublic


class TrainingDayExerciseBase(BaseModel):
    position: int = Field(default=1, ge=1)
    target_sets: int = Field(default=3, ge=1, le=20)
    target_reps_min: int | None = Field(default=None, ge=1, le=1000)
    target_reps_max: int | None = Field(default=None, ge=1, le=1000)

    @model_validator(mode="after")
    def check_rep_range(self):
        if (
            self.target_reps_min is not None
            and self.target_reps_max is not None
            and self.target_reps_max < self.target_reps_min
        ):
            raise ValueError("target_reps_max darf nicht kleiner als target_reps_min sein")
        return self


class TrainingDayExerciseCreate(TrainingDayExerciseBase):
    """Haengt eine Katalog-Uebung mit Vorgabe an einen Trainingstag."""

    exercise_id: int


class TrainingDayExerciseUpdate(BaseModel):
    position: int | None = Field(default=None, ge=1)
    target_sets: int | None = Field(default=None, ge=1, le=20)
    target_reps_min: int | None = Field(default=None, ge=1, le=1000)
    target_reps_max: int | None = Field(default=None, ge=1, le=1000)


class TrainingDayExercisePublic(TrainingDayExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    # Eigene id, weil dieselbe Uebung an einem Tag mehrfach stehen darf -
    # (training_day_id, exercise_id) ist dann nicht mehr eindeutig.
    id: int
    training_day_id: int
    exercise_id: int
    exercise: ExercisePublic

    @property
    def target_text(self) -> str:
        """"3x8-10" - fertig zum Anzeigen."""
        if self.target_reps_min is None:
            return f"{self.target_sets}x"
        if self.target_reps_max is None or self.target_reps_max == self.target_reps_min:
            return f"{self.target_sets}x{self.target_reps_min}"
        return f"{self.target_sets}x{self.target_reps_min}-{self.target_reps_max}"


class TrainingDayBase(BaseModel):
    position: int = Field(ge=1, le=7)
    workout_type: str = Field(min_length=1, max_length=50)


class TrainingDayCreate(TrainingDayBase):
    workout_plan_id: int
    exercises: list[TrainingDayExerciseCreate] = []


class TrainingDayNested(TrainingDayBase):
    """Trainingstag beim Anlegen eines Plans - die plan-id steht dann schon fest."""

    exercises: list[TrainingDayExerciseCreate] = []


class TrainingDayUpdate(BaseModel):
    position: int | None = Field(default=None, ge=1, le=7)
    workout_type: str | None = Field(default=None, min_length=1, max_length=50)


class TrainingDayPublic(TrainingDayBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_plan_id: int


class TrainingDayWithExercises(TrainingDayPublic):
    """Trainingstag samt Uebungen und Vorgaben - das braucht der Workout-Screen."""

    exercise_links: list[TrainingDayExercisePublic] = []

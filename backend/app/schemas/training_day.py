from pydantic import BaseModel, ConfigDict, Field

from app.schemas.exercise import ExercisePublic


class TrainingDayExerciseBase(BaseModel):
    position: int = Field(default=1, ge=1)
    target_sets: int = Field(default=3, ge=1, le=20)


class TrainingDayExerciseCreate(TrainingDayExerciseBase):
    """Haengt eine Katalog-Uebung mit Vorgabe an einen Trainingstag."""

    exercise_id: int


class TrainingDayExerciseUpdate(BaseModel):
    position: int | None = Field(default=None, ge=1)
    target_sets: int | None = Field(default=None, ge=1, le=20)


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
        """"3x" - fertig zum Anzeigen."""
        return f"{self.target_sets}x"


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

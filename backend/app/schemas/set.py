from pydantic import BaseModel, ConfigDict, Field


class SetBase(BaseModel):
    repetitions: int = Field(gt=0, le=1000)
    # None fuer Koerpergewichtsuebungen
    weight: float | None = Field(default=None, ge=0, le=1000)


class SetCreate(SetBase):
    exercise_id: int
    workout_id: int
    # Auf welchem Platz des Trainingstages der Satz gemacht wurde. None bei
    # freiem Training und bei Uebungen, die nicht auf dem Plan standen.
    training_day_exercise_id: int | None = None


class SetUpdate(BaseModel):
    repetitions: int | None = Field(default=None, gt=0, le=1000)
    weight: float | None = Field(default=None, ge=0, le=1000)


class SetPublic(SetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise_id: int
    workout_id: int
    training_day_exercise_id: int | None = None

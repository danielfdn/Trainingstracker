from pydantic import BaseModel, ConfigDict, Field

from app.schemas.set import SetPublic


class ExerciseBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    weighted: bool = True


class ExerciseCreate(ExerciseBase):
    workout_plan_id: int


class ExerciseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    weighted: bool | None = None


class ExercisePublic(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_plan_id: int


class ExerciseWithSets(ExercisePublic):
    """Uebung inklusive ihrer Saetze."""

    sets: list[SetPublic] = []

from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # gt=0 ersetzt die Validierung, die sonst haendisch im Service stehen muesste
    age: int = Field(gt=0, lt=130)
    weight: float = Field(gt=0, lt=500)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    """Alle Felder optional - fuer PATCH, das nur einzelne Felder aendert."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, gt=0, lt=130)
    weight: float | None = Field(default=None, gt=0, lt=500)


class UserPublic(UserBase):
    # from_attributes erlaubt Pydantic, direkt aus einem ORM-Objekt zu lesen
    # (User.name statt user["name"])
    model_config = ConfigDict(from_attributes=True)

    id: int
    # Nur lesbar: gesetzt wird der aktive Plan ueber PUT /users/{id}/active-plan,
    # damit die Existenz des Plans geprueft werden kann.
    active_workout_plan_id: int | None = None


class ActivePlanUpdate(BaseModel):
    """Body fuer PUT /users/{id}/active-plan. None hebt die Auswahl auf."""

    workout_plan_id: int | None = None

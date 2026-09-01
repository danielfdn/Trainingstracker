"""Pydantic-Schemas (DTOs) fuer die API.

Trennung von den ORM-Modellen in app/entities/: Die Entities beschreiben,
wie Daten in der Datenbank liegen. Die Schemas beschreiben, was ueber HTTP
rein- und rausgeht. Dadurch bestimmst du selbst, welche Felder die API
preisgibt, und aenderst dein DB-Schema, ohne die API zu brechen.

Namensschema pro Ressource:
  *Create   - Eingabedaten beim Anlegen (ohne id)
  *Update   - alle Felder optional, fuer PATCH
  *Public   - Ausgabedaten (mit id)
"""

from app.schemas.exercise import (
    ExerciseCreate,
    ExercisePublic,
    ExerciseUpdate,
    ExerciseWithSets,
)
from app.schemas.set import SetCreate, SetPublic, SetUpdate
from app.schemas.user import UserCreate, UserPublic, UserUpdate
from app.schemas.workout import (
    WorkoutCreate,
    WorkoutPublic,
    WorkoutUpdate,
    WorkoutWithSets,
)
from app.schemas.workout_plan import (
    WorkoutPlanCreate,
    WorkoutPlanPublic,
    WorkoutPlanUpdate,
    WorkoutPlanWithExercises,
)

__all__ = [
    "ExerciseCreate",
    "ExercisePublic",
    "ExerciseUpdate",
    "ExerciseWithSets",
    "SetCreate",
    "SetPublic",
    "SetUpdate",
    "UserCreate",
    "UserPublic",
    "UserUpdate",
    "WorkoutCreate",
    "WorkoutPublic",
    "WorkoutUpdate",
    "WorkoutWithSets",
    "WorkoutPlanCreate",
    "WorkoutPlanPublic",
    "WorkoutPlanUpdate",
    "WorkoutPlanWithExercises",
]

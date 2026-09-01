"""Sammelpunkt aller ORM-Modelle.

Wichtig fuer Alembic: Ein Modell landet nur dann in Base.metadata, wenn sein
Modul tatsaechlich importiert wurde. Dieses __init__ importiert alle Modelle,
sodass ein einziges "from app.entities import Base" ausreicht, damit Alembic
das komplette Schema sieht.
"""

from app.entities.base import Base
from app.entities.exercise import Exercise
from app.entities.set import Set
from app.entities.user import User
from app.entities.workout import Workout
from app.entities.workout_plan import WorkoutPlan

__all__ = ["Base", "Exercise", "Set", "User", "Workout", "WorkoutPlan"]

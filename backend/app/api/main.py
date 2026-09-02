"""Sammel-Router der API.

Bindet die Router der einzelnen Ressourcen zusammen. app/main.py haengt dann
nur noch diesen einen Router ein - neue Ressourcen brauchen deshalb nur hier
eine Zeile.
"""

from fastapi import APIRouter

from app.api.routes import (
    exercises,
    sets,
    training_days,
    training_log,
    users,
    workout_plans,
    workouts,
)

api_router = APIRouter()
api_router.include_router(users.router)
# Vor den generischen /users-Routen unkritisch: die Pfade unterscheiden sich
# in der Segmentzahl (/users/{id} gegen /users/{id}/log/...).
api_router.include_router(training_log.router)
api_router.include_router(workout_plans.router)
api_router.include_router(training_days.router)
api_router.include_router(exercises.router)
api_router.include_router(sets.router)
api_router.include_router(workouts.router)

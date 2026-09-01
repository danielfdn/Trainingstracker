"""Sammel-Router der API.

Bindet die Router der einzelnen Ressourcen zusammen. app/main.py haengt dann
nur noch diesen einen Router ein - neue Ressourcen brauchen deshalb nur hier
eine Zeile.
"""

from fastapi import APIRouter

from app.api.routes import exercises, sets, users, workout_plans, workouts

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(workout_plans.router)
api_router.include_router(exercises.router)
api_router.include_router(sets.router)
api_router.include_router(workouts.router)

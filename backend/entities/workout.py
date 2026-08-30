# workout-Objects
from datetime import datetime

from ENTITIES.workout_plan import WorkoutPlan

class Workout:
    def __init__(self, workout_plan: WorkoutPlan, date: datetime, attended: bool = True, comment: str = ""):
        self.workout_plan = workout_plan
        self.date = date
        self.attended = attended
        self.comment = comment


# workout-plan
from datetime import date

from ENTITIES.exercise import Exercise

class WorkoutPlan:
    def __init__(self, exercises: list[Exercise], title: str, training_days: int, starting_date: date = None, ending_date: date = None):
        self.exercises = exercises
        self.title = title
        self.training_days = training_days
        self.starting_date = starting_date
        self.ending_date = ending_date


    def __str__(self):
        return (f"Übung:{self.exercises}\nTrainingstage:{self.training_days}\nStartdatum:{self.starting_date}\nEnddatum:{self.ending_date}")
from ENTITIES.workout_plan import WorkoutPlan


class User:
    def __init__(self, name: str, age: int, weight: float, workout_plan: WorkoutPlan = None, id: int = None):
        self.id = id
        self.name = name
        self.age = age
        self.weight = weight
        self.workout_plan = workout_plan

    def __str__(self): return (f"{self.id}, {self.name}, {self.age}, {self.weight}, {self.workout_plan}")
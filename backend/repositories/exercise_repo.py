from REPOSITORIES.base_repo import BaseRepo
from ENTITIES.exercise import Exercise

class ExerciseRepo(BaseRepo):
    def create_exercise(self, exercise: Exercise):
        exercise.id = self.fetchone("INSERT INTO exercise (title, weighted) VALUES (%s, %s) RETURNING id"
                                    ,(exercise.title, exercise.weighted))[0]
        self.connection.commit()

    def read_one_exercise(self, id: int) -> str:
       return self.fetchone("SELECT * FROM exercise WHERE id = %s", (id,))

    def read_all_exercises(self) -> str:
        return self.fetchall("SELECT * FROM exercise")

    def delete_exercise(self, id: int):
        self.execute("DELETE FROM exercise WHERE id = %s", (id,))

    def update_exercise(self, exercise: Exercise): #TODO (eigentlich auch eine Operation für den Service): welche Operationen sollen für die Änderung von Exercises (speziell bzgl. sets ausgeführt werden können?
        while True:
            user_command = input("Which user Attribute do you want to change?\n(1) title\n(2) weighted \n(3) user-weight\n")
            match user_command:
                case "1":
                    new_name = input("New username: ")
                    self.execute(f"UPDATE appuser SET name = '{new_name}' WHERE id = %s", (id,))
                    break
                case "2":
                    new_age = input("New age: ")
                    self.execute(f"UPDATE appuser SET name = '{new_age}' WHERE id = %s", (id,))
                    break
                case "3":
                    new_weight = input("New weight: ")
                    self.execute(f"UPDATE appuser SET name = '{new_weight}' WHERE id = %s", (id,))
                    break
                case _:
                    print("Please make a valid choice\n")

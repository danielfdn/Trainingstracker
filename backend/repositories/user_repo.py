#User CRUD Operationen
from REPOSITORIES.base_repo import BaseRepo
from ENTITIES.user import User

class UserRepo(BaseRepo):

    def create_user(self, user: User):
        user.id = self.fetchone("INSERT INTO appuser (name, age, weight) VALUES (%s, %s, %s) RETURNING id",
                     (user.name, user.age, user.weight))[0]
        self.connection.commit()
        #%s sind Platzhalter, die durch die Parameter ersetzt werden -> verhindert SQL Injection

    def delete_user(self, id: int):
        self.execute("DELETE FROM appuser WHERE id = %s", (id,))

    def read_one_user(self, id: int) -> User:
        result = self.fetchone("SELECT * FROM appuser WHERE id = %s", (id,))
        return User(id=result[0], name=result[1], age=result[2], weight=result[3])

    def read_all_users(self):
        result = self.fetchall("SELECT * FROM appuser")
        return list(map(lambda row: User(id=row[0], name=row[1], age=row[2], weight=row[3]), result))

    def update_user(self, id: int): # TODO: Service- & Repo-Funktionalitäten klar trennen -> z.B gehört die Endlosschleife & 'switch case' Logik nicht ins user_repo
        while True:
            user_command = input("Which user Attribute do you want to change?\n(1) username\n(2) user-age\n(3) user-weight\n")
            match user_command:
                case "1":
                    new_name = input("New username: ")
                    self.execute("UPDATE appuser SET name = %s WHERE id = %s", (id,))
                    break
                case "2":
                    new_age = input("New age: ")
                    self.execute("UPDATE appuser SET age = %s WHERE id = %s", (id,))
                    break
                case "3":
                    new_weight = input("New weight: ")
                    self.execute("UPDATE appuser SET weight = %s WHERE id = %s", (id,))
                    break
                case _:
                    print("Please make a valid choice\n")




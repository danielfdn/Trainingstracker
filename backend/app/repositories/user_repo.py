from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.entities.user import User
from app.repositories.base_repo import BaseRepo


class UserRepo(BaseRepo[User]):
    """CRUD fuer User.

    get/list/create/update/delete kommen komplett aus BaseRepo. Hier stehen
    nur noch die Abfragen, die es so nur fuer User gibt.
    """

    def __init__(self, session: Session):
        super().__init__(session, User)

    def get_by_name(self, name: str) -> User | None:
        return self.session.scalars(select(User).where(User.name == name)).first()

    def get_with_plans(self, id: int) -> User | None:
        """User samt seiner Trainingsplaene in einer Abfrage.

        selectinload laedt die Plaene mit - ohne das wuerde SQLAlchemy pro
        User eine eigene Nachfrage stellen (N+1-Problem).
        """
        statement = (
            select(User).where(User.id == id).options(selectinload(User.workout_plans))
        )
        return self.session.scalars(statement).first()

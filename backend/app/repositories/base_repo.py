"""Generisches Basis-Repository.

Vorher: BaseRepo hat selbst eine psycopg2-Verbindung aufgemacht und rohe
SQL-Strings ausgefuehrt. Beides uebernimmt jetzt SQLAlchemy.

Was bleibt, ist der Zweck der Schicht: alle Datenbankzugriffe zu einer
Ressource an einem Ort buendeln. Die Session wird von aussen hereingegeben
(Dependency Injection) - dadurch teilen sich alle Repos innerhalb eines
Requests dieselbe Transaktion und lassen sich im Test leicht ersetzen.

Generic[ModelType] sorgt dafuer, dass z.B. UserRepo.get(1) fuer den
Type-Checker ein User | None zurueckgibt und nicht irgendein Objekt.
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.entities.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepo(Generic[ModelType]):
    def __init__(self, session: Session, model: type[ModelType]):
        self.session = session
        self.model = model

    def get(self, id: int) -> ModelType | None:
        """Einen Datensatz per Primaerschluessel holen, None wenn es ihn nicht gibt."""
        return self.session.get(self.model, id)

    def list(self, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Datensaetze seitenweise holen - ohne limit waechst die Antwort unbegrenzt."""
        statement = select(self.model).offset(skip).limit(limit)
        return list(self.session.scalars(statement).all())

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(self.model)) or 0

    def create(self, obj: ModelType) -> ModelType:
        self.session.add(obj)
        self.session.commit()
        # holt die von der DB vergebenen Werte (vor allem die id) ins Objekt
        self.session.refresh(obj)
        return obj

    def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        """Setzt nur die uebergebenen Felder.

        Das Aufloesen von "welche Felder wurden geschickt?" passiert im Router
        ueber model_dump(exclude_unset=True) - hier kommt bereits ein fertiges
        Dict an. Damit gibt es kein input() und keine Endlosschleife mehr im Repo.
        """
        for field, value in data.items():
            setattr(obj, field, value)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        self.session.delete(obj)
        self.session.commit()

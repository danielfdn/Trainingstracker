"""Datenbank-Anbindung: Engine und Session-Factory.

Frueher hat jede Repo-Instanz ihre eigene psycopg2-Verbindung aufgemacht.
Jetzt gibt es genau eine Engine fuer die gesamte Anwendung; die verwaltet
intern einen Connection-Pool. Pro HTTP-Request wird daraus eine Session
geliehen (siehe app/api/deps.py) und danach wieder zurueckgegeben.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    # prueft geliehene Verbindungen vor Gebrauch - verhindert Fehler durch
    # Verbindungen, die die Datenbank zwischenzeitlich geschlossen hat
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

"""Gemeinsame Test-Fixtures.

Die Tests laufen gegen eine SQLite-Datenbank im Arbeitsspeicher - dadurch
brauchst du zum Testen keinen laufenden PostgreSQL-Server, und jeder Test
startet mit einer frischen, leeren DB.

Moeglich wird das durch die Dependency Injection: app.dependency_overrides
ersetzt get_session durch eine Session auf die Test-DB. Genau dafuer war es
wichtig, dass die Repos ihre Session von aussen bekommen, statt sich selbst
eine Verbindung aufzumachen.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_session
from app.entities import Base
from app.main import app


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        # StaticPool: alle Zugriffe teilen sich dieselbe In-Memory-DB
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)
    with testing_session() as s:
        yield s
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

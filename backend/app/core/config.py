"""Zentrale Konfiguration.

Alle Einstellungen kommen aus Umgebungsvariablen bzw. der .env-Datei.
pydantic-settings liest sie ein und validiert sie beim Start - dadurch
scheitert die App sofort mit einer klaren Meldung, wenn z.B. DB_HOST fehlt,
statt erst beim ersten Datenbankzugriff.
"""

from pathlib import Path

from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> app -> backend -> Projekt-Root
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Absoluter Pfad, damit die .env unabhaengig davon gefunden wird,
        # aus welchem Ordner du uvicorn oder alembic startest.
        env_file=PROJECT_ROOT / ".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Trainingstracker"
    API_V1_STR: str = "/api/v1"

    # Origins, die per CORS auf die API zugreifen duerfen (spaeter die PWA).
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Eine Einheit, die nach so vielen Stunden noch laeuft, wurde
    # vergessen zu beenden und wird automatisch geschlossen.
    MAX_WORKOUT_HOURS: int = 6

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "trainingstracker"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""

    @computed_field
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        """Baut aus den Einzelwerten die Verbindungs-URL fuer SQLAlchemy."""
        return PostgresDsn.build(
            scheme="postgresql+psycopg2",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            path=self.DB_NAME,
        )


settings = Settings()

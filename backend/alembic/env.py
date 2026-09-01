"""Alembic-Konfiguration.

Zwei Anpassungen gegenueber der Standardvorlage:
1. Die Verbindungs-URL kommt aus app/core/config.py (also aus der .env) statt
   aus alembic.ini - so gibt es genau eine Quelle fuer die Zugangsdaten und
   keine Passwoerter in einer eingecheckten Datei.
2. target_metadata zeigt auf Base.metadata. Nur dadurch kann
   "alembic revision --autogenerate" dein Modell mit der DB vergleichen.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.entities import Base  # importiert alle Modelle -> fuellt Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL zur Laufzeit setzen, statt sie in alembic.ini zu hinterlegen
config.set_main_option("sqlalchemy.url", str(settings.SQLALCHEMY_DATABASE_URI))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Erzeugt nur das SQL, ohne sich zur DB zu verbinden."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Verbindet sich zur DB und fuehrt die Migrationen aus."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # erkennt auch geaenderte Spaltentypen, nicht nur neue/entfernte Spalten
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

"""Gemeinsame Basisklasse aller ORM-Modelle.

Jedes Modell, das von Base erbt, traegt sich automatisch in
Base.metadata ein. Genau diese Sammlung liest Alembic aus, um
Migrationen zu generieren.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass

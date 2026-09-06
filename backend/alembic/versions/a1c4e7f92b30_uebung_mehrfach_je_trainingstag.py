"""uebung mehrfach je trainingstag

Revision ID: a1c4e7f92b30
Revises: 88d6bbc62c6c
Create Date: 2026-09-06

Bisher war (training_day_id, exercise_id) der Primaerschluessel von
training_day_exercise - eine Uebung konnte pro Tag also genau einmal auf dem
Plan stehen. Gewollt ist aber z.B. Bankdruecken schwer am Anfang und leicht
am Ende. Deshalb bekommt die Tabelle eine eigene id, und jeder Satz merkt
sich ueber training_day_exercise_id, auf welchen dieser Plaetze er gehoert.

Postgres-spezifisch (Sequenz von Hand): die Tabelle enthaelt bereits Zeilen,
die eine id brauchen, bevor sie Primaerschluessel werden kann. Die Tests
laufen auf SQLite ueber create_all und beruehren diese Datei nicht.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e7f92b30'
down_revision: Union[str, Sequence[str], None] = '88d6bbc62c6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- training_day_exercise: id statt zusammengesetztem Schluessel ------
    op.drop_constraint(
        'training_day_exercise_pkey', 'training_day_exercise', type_='primary'
    )
    op.add_column(
        'training_day_exercise', sa.Column('id', sa.Integer(), nullable=True)
    )
    op.execute(
        'CREATE SEQUENCE training_day_exercise_id_seq '
        'OWNED BY training_day_exercise.id'
    )
    # Bestehende Zeilen durchnummerieren - in der Reihenfolge, in der sie im
    # Tag stehen, damit die Plaetze ihre Anzeigereihenfolge behalten.
    op.execute(
        'UPDATE training_day_exercise SET id = nextval(\'training_day_exercise_id_seq\')'
    )
    op.alter_column(
        'training_day_exercise',
        'id',
        nullable=False,
        server_default=sa.text("nextval('training_day_exercise_id_seq')"),
    )
    op.create_primary_key(
        'training_day_exercise_pkey', 'training_day_exercise', ['id']
    )
    op.create_index(
        op.f('ix_training_day_exercise_training_day_id'),
        'training_day_exercise',
        ['training_day_id'],
    )

    # --- exercise_set: auf welchem Platz wurde der Satz protokolliert ------
    op.add_column(
        'exercise_set',
        sa.Column('training_day_exercise_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f('ix_exercise_set_training_day_exercise_id'),
        'exercise_set',
        ['training_day_exercise_id'],
    )
    op.create_foreign_key(
        'exercise_set_training_day_exercise_id_fkey',
        'exercise_set',
        'training_day_exercise',
        ['training_day_exercise_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # Bereits protokollierte Saetze bekommen ihren Platz nachtraeglich - aber
    # nur dort, wo er eindeutig ist: die Uebung stand an dem Tag genau einmal.
    # Mehrdeutige Faelle gibt es zu diesem Zeitpunkt nicht, weil Duplikate
    # bisher gar nicht anlegbar waren. Saetze aus freien Trainings bleiben
    # bewusst ohne Platz.
    op.execute(
        """
        UPDATE exercise_set AS s
           SET training_day_exercise_id = tde.id
          FROM workout AS w, training_day_exercise AS tde
         WHERE s.workout_id = w.id
           AND w.training_day_id = tde.training_day_id
           AND s.exercise_id = tde.exercise_id
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'exercise_set_training_day_exercise_id_fkey',
        'exercise_set',
        type_='foreignkey',
    )
    op.drop_index(
        op.f('ix_exercise_set_training_day_exercise_id'), table_name='exercise_set'
    )
    op.drop_column('exercise_set', 'training_day_exercise_id')

    # Zurueck auf den zusammengesetzten Schluessel. Doppelte Plaetze muessen
    # vorher weichen, sonst scheitert der Primaerschluessel - es bleibt je
    # Tag und Uebung der erste Eintrag stehen.
    op.execute(
        """
        DELETE FROM training_day_exercise AS a
         USING training_day_exercise AS b
         WHERE a.training_day_id = b.training_day_id
           AND a.exercise_id = b.exercise_id
           AND a.id > b.id
        """
    )
    op.drop_index(
        op.f('ix_training_day_exercise_training_day_id'),
        table_name='training_day_exercise',
    )
    op.drop_constraint(
        'training_day_exercise_pkey', 'training_day_exercise', type_='primary'
    )
    op.drop_column('training_day_exercise', 'id')
    op.create_primary_key(
        'training_day_exercise_pkey',
        'training_day_exercise',
        ['training_day_id', 'exercise_id'],
    )

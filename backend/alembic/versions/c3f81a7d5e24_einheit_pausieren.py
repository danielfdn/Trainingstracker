"""einheit pausieren

Revision ID: c3f81a7d5e24
Revises: b7e35c1d40aa
Create Date: 2026-09-13

Eine laufende Einheit kann angehalten und fortgesetzt werden. Der Anlass war
ein Verbindungsfehler mitten im Training: beenden ging nicht, und die Uhr lief
zwei Stunden weiter - im Log stand danach eine Trainingszeit, die es nie gab.

Zwei Spalten statt einer Pausen-Tabelle:
  paused_at      - Beginn der gerade laufenden Pause, NULL wenn keine laeuft
  paused_seconds - Summe aller bereits beendeten Pausen
Fuer die Dauer zaehlt nur die Summe; eine Historie einzelner Pausen wuerde
nirgends angezeigt und muesste trotzdem gepflegt werden.

server_default '0' fuer die Bestandsdaten: eine Einheit von vor dieser
Aenderung hatte keine Pause, 0 ist fuer sie kein geratener, sondern der
richtige Wert. Das Default bleibt anschliessend stehen, damit auch ein INSERT
per Hand die Spalte nicht leer laesst.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f81a7d5e24'
down_revision: Union[str, Sequence[str], None] = 'b7e35c1d40aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'workout',
        sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'workout',
        sa.Column(
            'paused_seconds',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )
    # Dieselben Regeln wie in den Schemas, nur eine Ebene tiefer: auch ein
    # Skript oder DataGrip soll keine Einheit hinterlassen koennen, die
    # zugleich beendet ist und pausiert.
    op.create_check_constraint(
        'workout_pause_braucht_start',
        'workout',
        'paused_at IS NULL OR started_at IS NOT NULL',
    )
    op.create_check_constraint(
        'workout_pause_nicht_nach_ende',
        'workout',
        'paused_at IS NULL OR finished_at IS NULL',
    )
    op.create_check_constraint(
        'workout_pause_nicht_negativ',
        'workout',
        'paused_seconds >= 0',
    )


def downgrade() -> None:
    # Erst die Bedingungen, dann die Spalten - Postgres laesst eine Spalte
    # nicht fallen, solange ein Check sie noch nennt.
    op.drop_constraint('workout_pause_nicht_negativ', 'workout', type_='check')
    op.drop_constraint('workout_pause_nicht_nach_ende', 'workout', type_='check')
    op.drop_constraint('workout_pause_braucht_start', 'workout', type_='check')
    op.drop_column('workout', 'paused_seconds')
    op.drop_column('workout', 'paused_at')

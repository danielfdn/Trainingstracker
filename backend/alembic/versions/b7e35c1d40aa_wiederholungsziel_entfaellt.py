"""wiederholungsziel entfaellt

Revision ID: b7e35c1d40aa
Revises: a1c4e7f92b30
Create Date: 2026-09-12

Ein Plan gibt nur noch die Anzahl der Saetze vor. Die Wiederholungsspanne
("3x8-10") war eine Vorgabe, die im Training ohnehin nie eingehalten wurde:
wie viele Wiederholungen es geworden sind, steht danach im Log - dort ist es
eine Tatsache und keine Absicht. Damit fallen target_reps_min, target_reps_max
und der Check, der die Spanne richtig herum haelt, weg.

Die Spalten werden wirklich geloescht, nicht nur ausgeblendet: sie stehen in
keinem Bericht und in keiner Auswertung, es haengt also nichts daran.

Der Downgrade legt sie leer wieder an. Die alten Werte sind dann weg - sie
lassen sich nicht rekonstruieren, und ein Downgrade ist hier der Rueckweg
eines fehlgeschlagenen Updates, nicht eine Wiederherstellung.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e35c1d40aa'
down_revision: Union[str, Sequence[str], None] = 'a1c4e7f92b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Erst der Check, dann die Spalten: Postgres laesst eine Spalte nicht
    # fallen, solange eine Bedingung sie noch nennt.
    op.drop_constraint(
        'rep_range_richtig_herum', 'training_day_exercise', type_='check'
    )
    op.drop_column('training_day_exercise', 'target_reps_max')
    op.drop_column('training_day_exercise', 'target_reps_min')


def downgrade() -> None:
    op.add_column(
        'training_day_exercise',
        sa.Column('target_reps_min', sa.Integer(), nullable=True),
    )
    op.add_column(
        'training_day_exercise',
        sa.Column('target_reps_max', sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        'rep_range_richtig_herum',
        'training_day_exercise',
        'target_reps_max IS NULL OR target_reps_min IS NULL '
        'OR target_reps_max >= target_reps_min',
    )

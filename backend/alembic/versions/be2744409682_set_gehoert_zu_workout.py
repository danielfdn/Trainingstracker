"""set gehoert zu workout

Ein Satz war bisher nur an eine Uebung gehaengt und beschrieb damit die
Planvorgabe ("Bankdruecken 3x8"). Es gab keinen Weg, festzuhalten, was an
einem konkreten Tag tatsaechlich gehoben wurde - ein PATCH auf den Satz hat
die alte Zahl einfach ueberschrieben, die Historie war weg.

Mit dieser Migration bekommt exercise_set zusaetzlich workout_id (NOT NULL):
Ein Satz existiert nur noch innerhalb einer Trainingseinheit. exercise_id
sagt weiterhin "welche Uebung", workout_id neu "an welchem Tag".

Bestandsdaten: Die vorhandenen Saetze werden der juengsten Einheit des Plans
zugeordnet, zu dem ihre Uebung gehoert. Saetze, deren Plan ueberhaupt keine
Einheit hat, lassen sich nicht sinnvoll zuordnen und werden geloescht - erst
danach kann die Spalte NOT NULL werden.

Revision ID: be2744409682
Revises: 9b7ad37694a6
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be2744409682'
down_revision: Union[str, Sequence[str], None] = '9b7ad37694a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Spalte zunaechst nullable anlegen, sonst scheitert sie an den
    #    vorhandenen Zeilen.
    op.add_column('exercise_set', sa.Column('workout_id', sa.Integer(), nullable=True))

    # 2. Bestandsdaten zuordnen: juengste Einheit des passenden Plans.
    op.execute("""
        UPDATE exercise_set AS s
        SET workout_id = (
            SELECT w.id
            FROM workout AS w
            JOIN exercise AS e ON e.workout_plan_id = w.workout_plan_id
            WHERE e.id = s.exercise_id
            ORDER BY w.date DESC
            LIMIT 1
        )
    """)

    # 3. Was sich nicht zuordnen liess (Plan ohne jede Einheit), entfaellt.
    op.execute("DELETE FROM exercise_set WHERE workout_id IS NULL")

    # 4. Jetzt erst die eigentliche Regel durchsetzen.
    op.alter_column('exercise_set', 'workout_id', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        op.f('exercise_set_workout_id_fkey'),
        'exercise_set', 'workout', ['workout_id'], ['id'],
        ondelete='CASCADE',
    )
    # Index, weil "alle Saetze einer Einheit" die haeufigste Abfrage wird.
    op.create_index(op.f('ix_exercise_set_workout_id'), 'exercise_set', ['workout_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_exercise_set_workout_id'), table_name='exercise_set')
    op.drop_constraint(op.f('exercise_set_workout_id_fkey'), 'exercise_set', type_='foreignkey')
    op.drop_column('exercise_set', 'workout_id')

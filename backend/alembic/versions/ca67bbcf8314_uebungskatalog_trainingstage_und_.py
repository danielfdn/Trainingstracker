"""uebungskatalog, trainingstage und aktiver plan

Revision ID: ca67bbcf8314
Revises: 418fec70b608
Create Date: 2026-09-02 10:57:00.863263

Drei Aenderungen in einer Revision:

1. Uebungen gehoeren jetzt dem User statt einem Plan. Nur so bleibt
   "Bankdruecken" ueber einen Planwechsel hinweg dieselbe Zeile - und nur
   dann findet der Monatsvergleich (z.B. 09/25 gegen 04/26) etwas zum
   Vergleichen.
2. Ein Plan besteht aus Trainingstagen ("Push", "Pull", "Legs") mit eigenen
   Uebungen und Vorgaben ("3x8-10"). Die Zahl workout_plan.training_days
   entfaellt: die Anzahl der Tage IST die Anzahl der Zeilen.
3. Ein User hat genau einen aktiven Plan (appuser.active_workout_plan_id).

Zu den Daten: exercise.user_id ist NOT NULL, laesst sich fuer vorhandene
Zeilen aber nicht aus dem Plan ableiten, ohne Duplikate zusammenzufuehren.
Die Datenbank enthielt zu diesem Zeitpunkt ausschliesslich Seed-Daten
(pruefbar an den Namen "Seed Anna/Ben/Clara"), deshalb werden die
Uebungen samt ihrer Saetze geleert statt migriert. Danach neu befuellen mit:

    uv run python -m scripts.seed
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca67bbcf8314'
down_revision: Union[str, Sequence[str], None] = '418fec70b608'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- 2. Trainingstage und ihre Uebungen ------------------------------
    op.create_table(
        'training_day',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('workout_type', sa.String(length=50), nullable=False),
        sa.Column('workout_plan_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['workout_plan_id'], ['workout_plan.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workout_plan_id', 'position', name='training_day_position_einmalig'),
    )
    op.create_table(
        'training_day_exercise',
        sa.Column('training_day_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('target_sets', sa.Integer(), nullable=False),
        sa.Column('target_reps_min', sa.Integer(), nullable=True),
        sa.Column('target_reps_max', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            'target_reps_max IS NULL OR target_reps_min IS NULL '
            'OR target_reps_max >= target_reps_min',
            name='rep_range_richtig_herum',
        ),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['training_day_id'], ['training_day.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('training_day_id', 'exercise_id'),
    )

    # --- 3. Genau ein aktiver Plan ---------------------------------------
    # use_alter: appuser zeigt auf workout_plan und workout_plan zurueck auf
    # appuser - der Fremdschluessel muss deshalb nachtraeglich per ALTER
    # TABLE kommen, sonst gaebe es keine gueltige Anlege-Reihenfolge.
    op.add_column('appuser', sa.Column('active_workout_plan_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_appuser_active_workout_plan',
        'appuser', 'workout_plan',
        ['active_workout_plan_id'], ['id'],
        ondelete='SET NULL', use_alter=True,
    )

    # --- 1. Uebungen wandern vom Plan zum User ---------------------------
    # Zuerst leeren: user_id ist NOT NULL und liesse sich fuer bestehende
    # Zeilen nur raten. exercise_set haengt per ON DELETE CASCADE daran und
    # wird dabei mit geleert.
    op.execute('DELETE FROM exercise')
    op.add_column('exercise', sa.Column('user_id', sa.Integer(), nullable=False))
    op.drop_constraint(op.f('exercise_workout_plan_id_fkey'), 'exercise', type_='foreignkey')
    op.create_foreign_key(
        'fk_exercise_user', 'exercise', 'appuser', ['user_id'], ['id'], ondelete='CASCADE'
    )
    op.create_unique_constraint(
        'exercise_titel_je_user_einmalig', 'exercise', ['user_id', 'title']
    )
    op.drop_column('exercise', 'workout_plan_id')

    # --- Workout kennt seinen Trainingstag (NULL = freies Training) ------
    op.add_column('workout', sa.Column('training_day_id', sa.Integer(), nullable=True))
    op.create_index(
        op.f('ix_workout_training_day_id'), 'workout', ['training_day_id'], unique=False
    )
    op.create_foreign_key(
        'fk_workout_training_day', 'workout', 'training_day',
        ['training_day_id'], ['id'], ondelete='SET NULL',
    )

    # Die Anzahl der Trainingstage ergibt sich jetzt aus den Zeilen.
    op.drop_column('workout_plan', 'training_days')


def downgrade() -> None:
    """Downgrade schema.

    Hinweis: Die Zuordnung Uebung -> Plan ist beim Upgrade verloren gegangen
    und laesst sich nicht rekonstruieren. Der Downgrade leert die Uebungen
    deshalb ebenfalls, statt eine falsche Zuordnung zu erfinden.
    """
    # server_default, weil die Spalte NOT NULL ist und bestehende Plaene
    # sonst keinen Wert haetten. Danach wieder entfernt, damit das Schema
    # dem Stand vor der Migration entspricht.
    op.add_column(
        'workout_plan',
        sa.Column('training_days', sa.INTEGER(), nullable=False, server_default='3'),
    )
    op.alter_column('workout_plan', 'training_days', server_default=None)

    op.drop_constraint('fk_workout_training_day', 'workout', type_='foreignkey')
    op.drop_index(op.f('ix_workout_training_day_id'), table_name='workout')
    op.drop_column('workout', 'training_day_id')

    op.execute('DELETE FROM exercise')
    op.add_column('exercise', sa.Column('workout_plan_id', sa.INTEGER(), nullable=False))
    op.drop_constraint('exercise_titel_je_user_einmalig', 'exercise', type_='unique')
    op.drop_constraint('fk_exercise_user', 'exercise', type_='foreignkey')
    op.create_foreign_key(
        op.f('exercise_workout_plan_id_fkey'), 'exercise', 'workout_plan',
        ['workout_plan_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_column('exercise', 'user_id')

    op.drop_constraint('fk_appuser_active_workout_plan', 'appuser', type_='foreignkey')
    op.drop_column('appuser', 'active_workout_plan_id')

    op.drop_table('training_day_exercise')
    op.drop_table('training_day')

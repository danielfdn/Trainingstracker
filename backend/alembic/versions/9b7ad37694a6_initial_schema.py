"""initial schema

Revision ID: 9b7ad37694a6
Revises: 
Create Date: 2026-09-01 11:32:52.779119

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b7ad37694a6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Zuerst alle Fremdschluessel loesen, die noch auf die alte Tabelle
    # "workoutplan" zeigen - sonst laesst Postgres sie nicht loeschen.
    op.drop_constraint(op.f('appuser_workout_plan_id_fkey'), 'appuser', type_='foreignkey')
    op.drop_constraint(op.f('exercise_workout_plan_id_fkey'), 'exercise', type_='foreignkey')
    op.drop_constraint(op.f('workout_workout_plan_id_fkey'), 'workout', type_='foreignkey')
    op.drop_constraint(op.f('workout_app_user_id_fkey'), 'workout', type_='foreignkey')

    op.drop_table('set')
    op.drop_table('workoutplan')

    op.create_table('workout_plan',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('training_days', sa.Integer(), nullable=False),
    sa.Column('starting_date', sa.Date(), nullable=True),
    sa.Column('ending_date', sa.Date(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['appuser.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('exercise_set',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('repetitions', sa.Integer(), nullable=False),
    sa.Column('weight', sa.Numeric(precision=6, scale=2), nullable=True),
    sa.Column('exercise_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    op.alter_column('appuser', 'name',
               existing_type=sa.VARCHAR(length=30),
               type_=sa.String(length=100),
               existing_nullable=False)
    op.alter_column('appuser', 'weight',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               type_=sa.Numeric(precision=5, scale=2),
               existing_nullable=False)
    op.drop_column('appuser', 'workout_plan_id')

    op.alter_column('exercise', 'title',
               existing_type=sa.VARCHAR(length=30),
               type_=sa.String(length=100),
               existing_nullable=False)
    op.alter_column('exercise', 'workout_plan_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.create_foreign_key(op.f('exercise_workout_plan_id_fkey'), 'exercise', 'workout_plan', ['workout_plan_id'], ['id'], ondelete='CASCADE')

    op.add_column('workout', sa.Column('attended', sa.Boolean(), nullable=False))
    op.alter_column('workout', 'date',
               existing_type=sa.DATE(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)
    op.alter_column('workout', 'comment',
               existing_type=sa.VARCHAR(length=200),
               type_=sa.Text(),
               nullable=False)
    op.alter_column('workout', 'workout_plan_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.create_foreign_key(op.f('workout_workout_plan_id_fkey'), 'workout', 'workout_plan', ['workout_plan_id'], ['id'], ondelete='CASCADE')
    op.drop_column('workout', 'app_user_id')


def downgrade() -> None:
    """Downgrade schema."""
    # Erst die neuen Fremdschluessel und Tabellen abbauen ...
    op.drop_constraint(op.f('workout_workout_plan_id_fkey'), 'workout', type_='foreignkey')
    op.drop_constraint(op.f('exercise_workout_plan_id_fkey'), 'exercise', type_='foreignkey')
    op.drop_table('exercise_set')
    op.drop_table('workout_plan')

    # ... dann die alten Tabellen wiederherstellen ...
    op.create_table('workoutplan',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('title', sa.VARCHAR(length=30), autoincrement=False, nullable=False),
    sa.Column('traningdays', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('startingdate', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('endingdate', sa.DATE(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('workoutplan_pkey'))
    )
    op.create_table('set',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('weight', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('exercise_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('repetitions', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercise.id'], name=op.f('set_exercise_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('set_pkey'))
    )

    # ... und zuletzt die alten Spalten/Fremdschluessel.
    op.add_column('workout', sa.Column('app_user_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.alter_column('workout', 'workout_plan_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('workout', 'comment',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=200),
               nullable=True)
    op.alter_column('workout', 'date',
               existing_type=sa.DateTime(timezone=True),
               type_=sa.DATE(),
               existing_nullable=False)
    op.drop_column('workout', 'attended')
    op.create_foreign_key(op.f('workout_workout_plan_id_fkey'), 'workout', 'workoutplan', ['workout_plan_id'], ['id'])
    op.create_foreign_key(op.f('workout_app_user_id_fkey'), 'workout', 'appuser', ['app_user_id'], ['id'])

    op.alter_column('exercise', 'workout_plan_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('exercise', 'title',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=30),
               existing_nullable=False)
    op.create_foreign_key(op.f('exercise_workout_plan_id_fkey'), 'exercise', 'workoutplan', ['workout_plan_id'], ['id'])

    op.alter_column('appuser', 'weight',
               existing_type=sa.Numeric(precision=5, scale=2),
               type_=sa.DOUBLE_PRECISION(precision=53),
               existing_nullable=False)
    op.alter_column('appuser', 'name',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=30),
               existing_nullable=False)
    op.add_column('appuser', sa.Column('workout_plan_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key(op.f('appuser_workout_plan_id_fkey'), 'appuser', 'workoutplan', ['workout_plan_id'], ['id'])

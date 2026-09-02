"""koerpergewicht je einheit und offline-sync

Revision ID: 92d47e8a52d8
Revises: ca67bbcf8314
Create Date: 2026-09-02 19:31:35.721793

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92d47e8a52d8'
down_revision: Union[str, Sequence[str], None] = 'ca67bbcf8314'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # body_weight ist nullable und wird NICHT nachtraeglich gefuellt:
    # bestehende Einheiten haben kein ehrliches Gewicht von damals, und der
    # heutige Profilwert waere eine Erfindung, die im Log wie Historie aussaehe.
    op.add_column(
        "workout",
        sa.Column("body_weight", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column("workout", sa.Column("client_uuid", sa.String(length=36), nullable=True))
    # Benannt, damit downgrade() ihn wieder loeschen kann - autogenerate
    # setzt hier None ein, womit drop_constraint nie laufen koennte.
    op.create_unique_constraint(
        "workout_client_uuid_einmalig", "workout", ["client_uuid"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("workout_client_uuid_einmalig", "workout", type_="unique")
    op.drop_column("workout", "client_uuid")
    op.drop_column("workout", "body_weight")

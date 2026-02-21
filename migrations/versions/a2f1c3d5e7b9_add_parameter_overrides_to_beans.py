"""add parameter_overrides to beans

Revision ID: a2f1c3d5e7b9
Revises: 87c4e18a3be4
Create Date: 2026-02-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2f1c3d5e7b9"
down_revision: Union[str, Sequence[str], None] = "87c4e18a3be4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add parameter_overrides JSON column to beans table."""
    with op.batch_alter_table("beans", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parameter_overrides", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove parameter_overrides column from beans table."""
    with op.batch_alter_table("beans", schema=None) as batch_op:
        batch_op.drop_column("parameter_overrides")

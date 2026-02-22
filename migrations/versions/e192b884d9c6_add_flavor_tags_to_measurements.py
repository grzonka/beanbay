"""add_flavor_tags_to_measurements

Revision ID: e192b884d9c6
Revises: a2f1c3d5e7b9
Create Date: 2026-02-22 14:04:39.262878

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e192b884d9c6"
down_revision: Union[str, Sequence[str], None] = "a2f1c3d5e7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("measurements", sa.Column("flavor_tags", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("measurements", "flavor_tags")

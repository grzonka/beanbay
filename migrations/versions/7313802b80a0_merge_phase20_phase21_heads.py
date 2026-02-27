"""merge_phase20_phase21_heads

Revision ID: 7313802b80a0
Revises: 6d76407e7f4e, f3a2b1c8d9e0
Create Date: 2026-02-26 21:30:31.669346

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "7313802b80a0"
down_revision: Union[str, Sequence[str], None] = ("6d76407e7f4e", "f3a2b1c8d9e0")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

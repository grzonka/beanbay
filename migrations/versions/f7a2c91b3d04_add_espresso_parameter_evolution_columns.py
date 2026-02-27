"""add_espresso_parameter_evolution_columns

Revision ID: f7a2c91b3d04
Revises: 4500e5aafecb
Create Date: 2026-02-26 00:00:00.000000

Phase 20 changes:
  1. Add 8 new nullable columns to measurements table:
       preinfusion_time, preinfusion_pressure, brew_pressure, pressure_profile,
       bloom_pause, flow_rate, temp_profile, brew_mode
  2. Make preinfusion_pct and saturation nullable (they were NOT NULL before).
     SQLite batch-mode ALTER TABLE is used for the constraint relaxation.

Note: preinfusion_pct was always pump pressure percentage (55-100%), NOT a time proxy.
No data migration between preinfusion_pct and preinfusion_time — they measure different things.
The column is renamed to preinfusion_pressure_pct in the next migration (rename_preinfusion_pct_add_saturation_flow_rate).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "f7a2c91b3d04"
down_revision: Union[str, Sequence[str], None] = "4500e5aafecb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(inspector, table_name: str) -> set:
    """Return set of column names for table, or empty set if table absent."""
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema — add new parameter columns; relax nullability on preinfusion_pct/saturation."""
    conn = op.get_bind()
    inspector = inspect(conn)
    m_cols = _get_column_names(inspector, "measurements")

    # ------------------------------------------------------------------ #
    # 1. Add new nullable columns (idempotent — skip if already present)  #
    # ------------------------------------------------------------------ #
    new_cols = [
        ("preinfusion_time", sa.Float()),
        ("preinfusion_pressure", sa.Float()),
        ("brew_pressure", sa.Float()),
        ("pressure_profile", sa.String()),
        ("bloom_pause", sa.Float()),
        ("flow_rate", sa.Float()),
        ("temp_profile", sa.String()),
        ("brew_mode", sa.String()),
    ]
    for col_name, col_type in new_cols:
        if col_name not in m_cols:
            with op.batch_alter_table("measurements", schema=None) as batch_op:
                batch_op.add_column(sa.Column(col_name, col_type, nullable=True))

    # ------------------------------------------------------------------ #
    # 2. Relax NOT NULL constraints on preinfusion_pct and saturation     #
    #    SQLite requires batch mode (full table rebuild) for this.        #
    # ------------------------------------------------------------------ #
    # Re-inspect after column additions to get current state
    inspector2 = inspect(conn)
    m_cols2 = _get_column_names(inspector2, "measurements")

    if "preinfusion_pct" in m_cols2 or "saturation" in m_cols2:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            if "preinfusion_pct" in m_cols2:
                batch_op.alter_column("preinfusion_pct", existing_type=sa.Float(), nullable=True)
            if "saturation" in m_cols2:
                batch_op.alter_column("saturation", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    """Downgrade schema — drop new parameter columns."""
    conn = op.get_bind()
    inspector = inspect(conn)
    m_cols = _get_column_names(inspector, "measurements")

    drop_cols = [
        "brew_mode",
        "temp_profile",
        "flow_rate",
        "bloom_pause",
        "pressure_profile",
        "brew_pressure",
        "preinfusion_pressure",
        "preinfusion_time",
    ]
    cols_to_drop = [c for c in drop_cols if c in m_cols]
    if cols_to_drop:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)

    # Restore NOT NULL constraints on preinfusion_pct and saturation
    if "preinfusion_pct" in m_cols:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            batch_op.alter_column("preinfusion_pct", existing_type=sa.Float(), nullable=False)
    if "saturation" in m_cols:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            batch_op.alter_column("saturation", existing_type=sa.String(), nullable=False)

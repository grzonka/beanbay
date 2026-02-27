"""rename_preinfusion_pct_add_saturation_flow_rate

Revision ID: 6d76407e7f4e
Revises: f7a2c91b3d04
Create Date: 2026-02-26 00:01:00.000000

Phase 20 changes:
  1. Rename column `preinfusion_pct` → `preinfusion_pressure_pct` on measurements table.
     preinfusion_pct was always pump pressure percentage (55-100%), NOT a time proxy.
     This rename clarifies the column's true meaning. No data conversion.
  2. Add `saturation_flow_rate` (Float, nullable) to brewers table.
     This is a fixed brewer-level setting (ml/s), not a per-shot BayBE optimization parameter.

SQLite batch mode is required for column renames.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "6d76407e7f4e"
down_revision: Union[str, Sequence[str], None] = "f7a2c91b3d04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(inspector, table_name: str) -> set:
    """Return set of column names for table, or empty set if table absent."""
    if table_name not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Rename preinfusion_pct → preinfusion_pressure_pct; add saturation_flow_rate to brewers."""
    conn = op.get_bind()
    inspector = inspect(conn)
    m_cols = _get_column_names(inspector, "measurements")
    b_cols = _get_column_names(inspector, "brewers")

    # ------------------------------------------------------------------ #
    # 1. Rename preinfusion_pct → preinfusion_pressure_pct                #
    #    SQLite requires batch mode (full table rebuild) for column renames.
    # ------------------------------------------------------------------ #
    if "preinfusion_pct" in m_cols and "preinfusion_pressure_pct" not in m_cols:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            batch_op.alter_column(
                "preinfusion_pct",
                new_column_name="preinfusion_pressure_pct",
                existing_type=sa.Float(),
                nullable=True,
            )

    # ------------------------------------------------------------------ #
    # 2. Add saturation_flow_rate to brewers table                        #
    # ------------------------------------------------------------------ #
    if "saturation_flow_rate" not in b_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("saturation_flow_rate", sa.Float(), nullable=True))


def downgrade() -> None:
    """Reverse: rename preinfusion_pressure_pct → preinfusion_pct; drop saturation_flow_rate."""
    conn = op.get_bind()
    inspector = inspect(conn)
    m_cols = _get_column_names(inspector, "measurements")
    b_cols = _get_column_names(inspector, "brewers")

    # Reverse column rename
    if "preinfusion_pressure_pct" in m_cols and "preinfusion_pct" not in m_cols:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            batch_op.alter_column(
                "preinfusion_pressure_pct",
                new_column_name="preinfusion_pct",
                existing_type=sa.Float(),
                nullable=True,
            )

    # Drop saturation_flow_rate
    if "saturation_flow_rate" in b_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.drop_column("saturation_flow_rate")

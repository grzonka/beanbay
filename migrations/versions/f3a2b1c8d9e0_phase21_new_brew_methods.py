"""phase21_new_brew_methods

Add nullable measurement columns for new brew method parameters and seed
5 new BrewMethod entries: french-press, aeropress, turkish, moka-pot, cold-brew.

Revision ID: f3a2b1c8d9e0
Revises: 4500e5aafecb
Create Date: 2026-02-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = "f3a2b1c8d9e0"
down_revision: Union[str, Sequence[str], None] = "f7a2c91b3d04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(inspector, table_name: str) -> set:
    """Return set of column names for a table, or empty set if table doesn't exist."""
    tables = inspector.get_table_names()
    if table_name not in tables:
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def _get_column_nullable(inspector, table_name: str, col_name: str) -> bool | None:
    """Return nullable status for a column, or None if column/table not found."""
    tables = inspector.get_table_names()
    if table_name not in tables:
        return None
    for col in inspector.get_columns(table_name):
        if col["name"] == col_name:
            return col.get("nullable", True)
    return None


def upgrade() -> None:
    """Upgrade schema — add nullable measurement columns + seed 5 new brew methods."""
    conn = op.get_bind()
    inspector = inspect(conn)
    meas_cols = _get_column_names(inspector, "measurements")

    # ── New nullable columns on measurements ─────────────────────────────────
    # These columns support the new brew methods. All nullable so existing
    # espresso/pour-over measurements are unaffected.
    new_columns = [
        # steep_time: minutes steeping (french-press, aeropress, cold-brew)
        ("steep_time", sa.Float(), True),
        # brew_volume: total water volume in ml (pour-over, french-press, aeropress, turkish, moka-pot)
        ("brew_volume", sa.Float(), True),
        # bloom_weight: bloom water weight in g (pour-over)
        ("bloom_weight", sa.Float(), True),
        # brew_mode: "standard"/"inverted" for aeropress
        # (may already exist from a prior migration — guard below)
        ("brew_mode", sa.String(), True),
    ]

    for col_name, col_type, nullable in new_columns:
        if col_name not in meas_cols:
            with op.batch_alter_table("measurements", schema=None) as batch_op:
                batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))

    # ── Make target_yield nullable (was NOT NULL, must be nullable for non-espresso) ──
    if _get_column_nullable(inspector, "measurements", "target_yield") is False:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            batch_op.alter_column("target_yield", existing_type=sa.Float(), nullable=True)

    # ── Seed new BrewMethod entries ───────────────────────────────────────────
    import uuid

    new_methods = ["pour-over", "french-press", "aeropress", "turkish", "moka-pot", "cold-brew"]
    for method_name in new_methods:
        # Only insert if not already present (idempotent)
        existing = conn.execute(
            sa.text("SELECT id FROM brew_methods WHERE name = :name"),
            {"name": method_name},
        ).fetchone()
        if existing is None:
            conn.execute(
                sa.text("INSERT INTO brew_methods (id, name) VALUES (:id, :name)"),
                {"id": str(uuid.uuid4()), "name": method_name},
            )


def downgrade() -> None:
    """Downgrade schema — drop new measurement columns."""
    conn = op.get_bind()
    inspector = inspect(conn)
    meas_cols = _get_column_names(inspector, "measurements")

    drop_cols = ["steep_time", "brew_volume", "bloom_weight"]
    # Note: brew_mode is NOT dropped on downgrade as it may have been added by a prior migration
    cols_to_drop = [c for c in drop_cols if c in meas_cols]
    if cols_to_drop:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)

    # Restore NOT NULL on target_yield
    if "target_yield" in meas_cols:
        with op.batch_alter_table("measurements", schema=None) as batch_op:
            batch_op.alter_column("target_yield", existing_type=sa.Float(), nullable=False)

    # Note: we don't remove seeded brew_methods rows on downgrade
    # as they may have associated data.

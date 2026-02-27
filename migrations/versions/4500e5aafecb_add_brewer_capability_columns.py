"""add_brewer_capability_columns

Revision ID: 4500e5aafecb
Revises: e32844be4891
Create Date: 2026-02-24 01:32:21.932906

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "4500e5aafecb"
down_revision: Union[str, Sequence[str], None] = "e32844be4891"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(inspector, table_name):
    """Return set of column names for a table, or empty set if table doesn't exist."""
    tables = inspector.get_table_names()
    if table_name not in tables:
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema — add 13 capability columns to brewers table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    brewers_cols = _get_column_names(inspector, "brewers")

    # --- Temperature capability columns ---
    if "temp_control_type" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("temp_control_type", sa.String(), nullable=False, server_default="pid")
            )
        op.execute("UPDATE brewers SET temp_control_type = 'pid' WHERE temp_control_type IS NULL")

    if "temp_min" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("temp_min", sa.Float(), nullable=True))

    if "temp_max" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("temp_max", sa.Float(), nullable=True))

    if "temp_step" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("temp_step", sa.Float(), nullable=True))

    # --- Pre-infusion capability columns ---
    if "preinfusion_type" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("preinfusion_type", sa.String(), nullable=False, server_default="none")
            )
        op.execute("UPDATE brewers SET preinfusion_type = 'none' WHERE preinfusion_type IS NULL")

    if "preinfusion_max_time" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("preinfusion_max_time", sa.Float(), nullable=True))

    # --- Pressure capability columns ---
    if "pressure_control_type" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "pressure_control_type", sa.String(), nullable=False, server_default="fixed"
                )
            )
        op.execute(
            "UPDATE brewers SET pressure_control_type = 'fixed' WHERE pressure_control_type IS NULL"
        )

    if "pressure_min" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("pressure_min", sa.Float(), nullable=True))

    if "pressure_max" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("pressure_max", sa.Float(), nullable=True))

    # --- Flow capability column ---
    if "flow_control_type" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("flow_control_type", sa.String(), nullable=False, server_default="none")
            )
        op.execute("UPDATE brewers SET flow_control_type = 'none' WHERE flow_control_type IS NULL")

    # --- Bloom capability column ---
    if "has_bloom" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("has_bloom", sa.Boolean(), nullable=False, server_default="0")
            )
        op.execute("UPDATE brewers SET has_bloom = 0 WHERE has_bloom IS NULL")

    # --- Stop mode column ---
    if "stop_mode" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("stop_mode", sa.String(), nullable=False, server_default="manual")
            )
        op.execute("UPDATE brewers SET stop_mode = 'manual' WHERE stop_mode IS NULL")


def downgrade() -> None:
    """Downgrade schema — drop 13 capability columns from brewers table."""
    conn = op.get_bind()
    inspector = inspect(conn)
    brewers_cols = _get_column_names(inspector, "brewers")

    drop_cols = [
        "stop_mode",
        "has_bloom",
        "flow_control_type",
        "pressure_max",
        "pressure_min",
        "pressure_control_type",
        "preinfusion_max_time",
        "preinfusion_type",
        "temp_step",
        "temp_max",
        "temp_min",
        "temp_control_type",
    ]
    cols_to_drop = [c for c in drop_cols if c in brewers_cols]
    if cols_to_drop:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)

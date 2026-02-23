"""add_equipment_fields_and_retire_lifecycle

Revision ID: e32844be4891
Revises: bf44156bfd41
Create Date: 2026-02-23 01:03:49.229327

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "e32844be4891"
down_revision: Union[str, Sequence[str], None] = "bf44156bfd41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_column_names(inspector, table_name):
    """Return set of column names for a table, or empty set if table doesn't exist."""
    tables = inspector.get_table_names()
    if table_name not in tables:
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # --- Create brewer_methods association table (may already exist if app did create_all) ---
    if "brewer_methods" not in existing_tables:
        op.create_table(
            "brewer_methods",
            sa.Column("brewer_id", sa.String(), sa.ForeignKey("brewers.id"), primary_key=True),
            sa.Column("method_id", sa.String(), sa.ForeignKey("brew_methods.id"), primary_key=True),
        )

    # --- brew_setups: add is_retired ---
    brew_setups_cols = _get_column_names(inspector, "brew_setups")
    if "is_retired" not in brew_setups_cols:
        with op.batch_alter_table("brew_setups", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_retired", sa.Boolean(), nullable=False, server_default="0")
            )
        # Set default False for existing rows
        op.execute("UPDATE brew_setups SET is_retired = 0 WHERE is_retired IS NULL")

    # --- brewers: add is_retired ---
    brewers_cols = _get_column_names(inspector, "brewers")
    if "is_retired" not in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_retired", sa.Boolean(), nullable=False, server_default="0")
            )
        op.execute("UPDATE brewers SET is_retired = 0 WHERE is_retired IS NULL")

    # --- grinders: add dial_type, step_size, min_value, max_value, is_retired ---
    grinders_cols = _get_column_names(inspector, "grinders")
    if "dial_type" not in grinders_cols:
        with op.batch_alter_table("grinders", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("dial_type", sa.String(), nullable=False, server_default="stepless")
            )
        # Set default "stepless" for existing rows
        op.execute("UPDATE grinders SET dial_type = 'stepless' WHERE dial_type IS NULL")
    if "step_size" not in grinders_cols:
        with op.batch_alter_table("grinders", schema=None) as batch_op:
            batch_op.add_column(sa.Column("step_size", sa.Float(), nullable=True))
    if "min_value" not in grinders_cols:
        with op.batch_alter_table("grinders", schema=None) as batch_op:
            batch_op.add_column(sa.Column("min_value", sa.Float(), nullable=True))
    if "max_value" not in grinders_cols:
        with op.batch_alter_table("grinders", schema=None) as batch_op:
            batch_op.add_column(sa.Column("max_value", sa.Float(), nullable=True))
    if "is_retired" not in grinders_cols:
        with op.batch_alter_table("grinders", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_retired", sa.Boolean(), nullable=False, server_default="0")
            )
        op.execute("UPDATE grinders SET is_retired = 0 WHERE is_retired IS NULL")

    # --- papers: add description, is_retired ---
    papers_cols = _get_column_names(inspector, "papers")
    if "description" not in papers_cols:
        with op.batch_alter_table("papers", schema=None) as batch_op:
            batch_op.add_column(sa.Column("description", sa.String(), nullable=True))
    if "is_retired" not in papers_cols:
        with op.batch_alter_table("papers", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_retired", sa.Boolean(), nullable=False, server_default="0")
            )
        op.execute("UPDATE papers SET is_retired = 0 WHERE is_retired IS NULL")

    # --- water_recipes: add notes + mineral fields + is_retired ---
    water_cols = _get_column_names(inspector, "water_recipes")
    mineral_fields = [
        ("notes", sa.String(), True),
        ("gh", sa.Float(), True),
        ("kh", sa.Float(), True),
        ("ca", sa.Float(), True),
        ("mg", sa.Float(), True),
        ("na", sa.Float(), True),
        ("cl", sa.Float(), True),
        ("so4", sa.Float(), True),
    ]
    for col_name, col_type, nullable in mineral_fields:
        if col_name not in water_cols:
            with op.batch_alter_table("water_recipes", schema=None) as batch_op:
                batch_op.add_column(sa.Column(col_name, col_type, nullable=nullable))
    if "is_retired" not in water_cols:
        with op.batch_alter_table("water_recipes", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("is_retired", sa.Boolean(), nullable=False, server_default="0")
            )
        op.execute("UPDATE water_recipes SET is_retired = 0 WHERE is_retired IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # --- water_recipes: drop mineral fields and is_retired ---
    water_cols = _get_column_names(inspector, "water_recipes")
    drop_water = ["is_retired", "so4", "cl", "na", "mg", "ca", "kh", "gh", "notes"]
    cols_to_drop = [c for c in drop_water if c in water_cols]
    if cols_to_drop:
        with op.batch_alter_table("water_recipes", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)

    # --- papers: drop description and is_retired ---
    papers_cols = _get_column_names(inspector, "papers")
    drop_papers = ["is_retired", "description"]
    cols_to_drop = [c for c in drop_papers if c in papers_cols]
    if cols_to_drop:
        with op.batch_alter_table("papers", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)

    # --- grinders: drop all new columns ---
    grinders_cols = _get_column_names(inspector, "grinders")
    drop_grinders = ["is_retired", "max_value", "min_value", "step_size", "dial_type"]
    cols_to_drop = [c for c in drop_grinders if c in grinders_cols]
    if cols_to_drop:
        with op.batch_alter_table("grinders", schema=None) as batch_op:
            for col in cols_to_drop:
                batch_op.drop_column(col)

    # --- brewers: drop is_retired ---
    brewers_cols = _get_column_names(inspector, "brewers")
    if "is_retired" in brewers_cols:
        with op.batch_alter_table("brewers", schema=None) as batch_op:
            batch_op.drop_column("is_retired")

    # --- brew_setups: drop is_retired ---
    brew_setups_cols = _get_column_names(inspector, "brew_setups")
    if "is_retired" in brew_setups_cols:
        with op.batch_alter_table("brew_setups", schema=None) as batch_op:
            batch_op.drop_column("is_retired")

    # --- Drop brewer_methods association table ---
    if "brewer_methods" in existing_tables:
        op.drop_table("brewer_methods")

"""Brew-related models for BeanBay.

BrewSetup represents a reusable equipment configuration for brewing coffee,
referencing a required BrewMethod and optional Grinder, Brewer, Paper, and Water.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Field, Relationship, SQLModel

from beanbay.models.base import uuid4_default


class BrewSetup(SQLModel, table=True):
    """A reusable brew setup combining a method with equipment.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str | None
        Optional human-readable name for the setup.
    brew_method_id : uuid.UUID
        Foreign key to the brew method (required).
    grinder_id : uuid.UUID | None
        Foreign key to the grinder (optional).
    brewer_id : uuid.UUID | None
        Foreign key to the brewer (optional).
    paper_id : uuid.UUID | None
        Foreign key to the paper (optional).
    water_id : uuid.UUID | None
        Foreign key to the water (optional).
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "brew_setups"

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str | None = Field(default=None, index=True)

    brew_method_id: uuid.UUID = Field(foreign_key="brew_methods.id")
    grinder_id: uuid.UUID | None = Field(default=None, foreign_key="grinders.id")
    brewer_id: uuid.UUID | None = Field(default=None, foreign_key="brewers.id")
    paper_id: uuid.UUID | None = Field(default=None, foreign_key="papers.id")
    water_id: uuid.UUID | None = Field(default=None, foreign_key="waters.id")

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

    # Relationships
    brew_method: "BrewMethod" = Relationship()  # type: ignore[name-defined]  # noqa: F821
    grinder: Optional["Grinder"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    brewer: Optional["Brewer"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    paper: Optional["Paper"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    water: Optional["Water"] = Relationship()  # type: ignore[name-defined]  # noqa: F821

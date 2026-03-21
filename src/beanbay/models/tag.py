"""Lookup table models for BeanBay.

Seven soft-deletable lookup tables, each with ``id``, ``name``,
``created_at``, and ``retired_at`` columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Field, SQLModel

from beanbay.models.base import uuid4_default


class FlavorTag(SQLModel, table=True):
    """A flavor descriptor tag (e.g. 'chocolate', 'fruity').

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique tag name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "flavor_tags"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class Origin(SQLModel, table=True):
    """A coffee origin country or region.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique origin name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "origins"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class Roaster(SQLModel, table=True):
    """A coffee roaster / roastery.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique roaster name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "roasters"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class ProcessMethod(SQLModel, table=True):
    """A coffee processing method (e.g. 'washed', 'natural').

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique process method name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "process_methods"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class BeanVariety(SQLModel, table=True):
    """A coffee bean variety (e.g. 'Typica', 'Bourbon').

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique variety name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "bean_varieties"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class BrewMethod(SQLModel, table=True):
    """A brewing method (e.g. 'espresso', 'pour-over').

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique brew method name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "brew_methods"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class StopMode(SQLModel, table=True):
    """A stop mode for brew automation (e.g. 'time', 'weight').

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique stop mode name.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "stop_modes"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None


class Vendor(SQLModel, table=True):
    """A vendor / shop where beans are purchased.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique vendor name.
    url : str | None
        Shop website URL.
    location : str | None
        City, address, etc.
    notes : str | None
        Free-text notes.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "vendors"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    url: str | None = None
    location: str | None = None
    notes: str | None = None
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None


class StorageType(SQLModel, table=True):
    """A frozen storage type (e.g. 'Vacuum Sealed', 'Zip Lock').

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique storage type name.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "storage_types"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

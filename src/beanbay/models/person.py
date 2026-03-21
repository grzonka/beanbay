"""Person model for BeanBay.

A soft-deletable, updatable model representing a person (user / barista)
who can be marked as the default person.
"""

import uuid
from datetime import datetime

from sqlalchemy import func
from sqlmodel import Field, SQLModel

from beanbay.models.base import uuid4_default


class Person(SQLModel, table=True):
    """A person (user / barista) in the system.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique person name.
    is_default : bool
        Whether this person is the current default. At most one person
        should have ``is_default=True`` at any time.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "people"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    is_default: bool = Field(default=False)
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

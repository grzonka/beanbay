"""Read / write schemas for the Person model."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel


class PersonBase(SQLModel):
    """Shared fields for Person schemas."""

    name: str


class PersonCreate(PersonBase):
    """Schema for creating a Person."""

    pass


class PersonUpdate(SQLModel):
    """Schema for partially updating a Person.

    All fields are optional so callers can send only the fields they
    want to change.
    """

    name: str | None = None
    is_default: bool | None = None
    retired_at: datetime | None = None


class PersonRead(PersonBase):
    """Schema returned when reading a Person.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Person name.
    is_default : bool
        Whether this person is the current default.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    is_default: bool
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Inject ``is_retired`` bool derived from ``retired_at``.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : dict | object
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        dict
            A dict with ``is_retired`` populated.
        """
        if isinstance(data, dict):
            data["is_retired"] = data.get("retired_at") is not None
            return data
        # ORM model
        data_dict: dict[str, Any] = {}
        for field in (
            "id",
            "name",
            "is_default",
            "created_at",
            "updated_at",
            "retired_at",
        ):
            data_dict[field] = getattr(data, field, None)
        data_dict["is_retired"] = data_dict["retired_at"] is not None
        return data_dict

"""Read / write schemas for the seven lookup-table models."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel


# ---------------------------------------------------------------------------
# Helper: shared Read-schema validator
# ---------------------------------------------------------------------------


def _compute_is_retired(cls: type, data: Any) -> Any:
    """Inject ``is_retired`` bool derived from ``retired_at``.

    Parameters
    ----------
    cls : type
        The model class (unused but required by pydantic).
    data : Any
        Raw input — either a dict or an ORM model instance.

    Returns
    -------
    Any
        A dict with ``is_retired`` populated.
    """
    if isinstance(data, dict):
        data["is_retired"] = data.get("retired_at") is not None
        return data
    # ORM model
    data_dict: dict[str, Any] = {}
    for field in ("id", "name", "created_at", "retired_at"):
        data_dict[field] = getattr(data, field, None)
    data_dict["is_retired"] = data_dict["retired_at"] is not None
    return data_dict


# ===================================================================
# FlavorTag
# ===================================================================


class FlavorTagBase(SQLModel):
    """Shared fields for FlavorTag schemas."""

    name: str


class FlavorTagCreate(FlavorTagBase):
    """Schema for creating a FlavorTag."""

    pass


class FlavorTagUpdate(SQLModel):
    """Schema for partially updating a FlavorTag."""

    name: str | None = None


class FlavorTagRead(FlavorTagBase):
    """Schema returned when reading a FlavorTag.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Tag name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# Origin
# ===================================================================


class OriginBase(SQLModel):
    """Shared fields for Origin schemas."""

    name: str


class OriginCreate(OriginBase):
    """Schema for creating an Origin."""

    pass


class OriginUpdate(SQLModel):
    """Schema for partially updating an Origin."""

    name: str | None = None


class OriginRead(OriginBase):
    """Schema returned when reading an Origin.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Origin name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# Roaster
# ===================================================================


class RoasterBase(SQLModel):
    """Shared fields for Roaster schemas."""

    name: str


class RoasterCreate(RoasterBase):
    """Schema for creating a Roaster."""

    pass


class RoasterUpdate(SQLModel):
    """Schema for partially updating a Roaster."""

    name: str | None = None


class RoasterRead(RoasterBase):
    """Schema returned when reading a Roaster.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Roaster name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# ProcessMethod
# ===================================================================


class ProcessMethodBase(SQLModel):
    """Shared fields for ProcessMethod schemas."""

    name: str


class ProcessMethodCreate(ProcessMethodBase):
    """Schema for creating a ProcessMethod."""

    pass


class ProcessMethodUpdate(SQLModel):
    """Schema for partially updating a ProcessMethod."""

    name: str | None = None


class ProcessMethodRead(ProcessMethodBase):
    """Schema returned when reading a ProcessMethod.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Process method name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# BeanVariety
# ===================================================================


class BeanVarietyBase(SQLModel):
    """Shared fields for BeanVariety schemas."""

    name: str


class BeanVarietyCreate(BeanVarietyBase):
    """Schema for creating a BeanVariety."""

    pass


class BeanVarietyUpdate(SQLModel):
    """Schema for partially updating a BeanVariety."""

    name: str | None = None


class BeanVarietyRead(BeanVarietyBase):
    """Schema returned when reading a BeanVariety.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Bean variety name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# BrewMethod
# ===================================================================


class BrewMethodBase(SQLModel):
    """Shared fields for BrewMethod schemas."""

    name: str


class BrewMethodCreate(BrewMethodBase):
    """Schema for creating a BrewMethod."""

    pass


class BrewMethodUpdate(SQLModel):
    """Schema for partially updating a BrewMethod."""

    name: str | None = None


class BrewMethodRead(BrewMethodBase):
    """Schema returned when reading a BrewMethod.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Brew method name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# StopMode
# ===================================================================


class StopModeBase(SQLModel):
    """Shared fields for StopMode schemas."""

    name: str


class StopModeCreate(StopModeBase):
    """Schema for creating a StopMode."""

    pass


class StopModeUpdate(SQLModel):
    """Schema for partially updating a StopMode."""

    name: str | None = None


class StopModeRead(StopModeBase):
    """Schema returned when reading a StopMode.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Stop mode name.
    created_at : datetime
        Creation timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: Any) -> Any:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)

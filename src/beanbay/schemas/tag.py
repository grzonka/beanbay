"""Read / write schemas for the seven lookup-table models."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel

from beanbay.models.enums import CoffeeSpecies, ProcessCategory


# ---------------------------------------------------------------------------
# Helper: shared Read-schema validator
# ---------------------------------------------------------------------------


def _compute_is_retired(cls: type, data: dict | object) -> dict:
    """Inject ``is_retired`` bool derived from ``retired_at``.

    Uses ``cls.model_fields`` to dynamically extract all declared fields,
    making this helper reusable for any Read schema that carries
    ``retired_at`` and ``is_retired``.

    Parameters
    ----------
    cls : type
        The model class whose ``model_fields`` drive extraction.
    data : dict | object
        Raw input — either a dict or an ORM model instance.

    Returns
    -------
    dict
        A dict with ``is_retired`` populated.
    """
    if isinstance(data, dict):
        data["is_retired"] = data.get("retired_at") is not None
        return data
    # ORM model — dynamically pull every declared field except is_retired
    data_dict: dict[str, Any] = {}
    for field_name in cls.model_fields:
        if field_name == "is_retired":
            continue
        data_dict[field_name] = getattr(data, field_name, None)
    data_dict["is_retired"] = data_dict.get("retired_at") is not None
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
    retired_at: datetime | None = None


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
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# Origin
# ===================================================================


class OriginBase(SQLModel):
    """Shared fields for Origin schemas."""

    name: str
    country: str | None = None
    region: str | None = None


class OriginCreate(OriginBase):
    """Schema for creating an Origin."""

    pass


class OriginUpdate(SQLModel):
    """Schema for partially updating an Origin."""

    name: str | None = None
    country: str | None = None
    region: str | None = None
    retired_at: datetime | None = None


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
    percentage : float | None
        Blend percentage (only populated when read via a Bean relationship).
    """

    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool
    percentage: float | None = None

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: dict | object) -> dict:
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
    retired_at: datetime | None = None


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
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# ProcessMethod
# ===================================================================


class ProcessMethodBase(SQLModel):
    """Shared fields for ProcessMethod schemas."""

    name: str
    category: ProcessCategory | None = None


class ProcessMethodCreate(ProcessMethodBase):
    """Schema for creating a ProcessMethod."""

    pass


class ProcessMethodUpdate(SQLModel):
    """Schema for partially updating a ProcessMethod."""

    name: str | None = None
    category: ProcessCategory | None = None
    retired_at: datetime | None = None


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
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# BeanVariety
# ===================================================================


class BeanVarietyBase(SQLModel):
    """Shared fields for BeanVariety schemas."""

    name: str
    species: CoffeeSpecies | None = None


class BeanVarietyCreate(BeanVarietyBase):
    """Schema for creating a BeanVariety."""

    pass


class BeanVarietyUpdate(SQLModel):
    """Schema for partially updating a BeanVariety."""

    name: str | None = None
    species: CoffeeSpecies | None = None
    retired_at: datetime | None = None


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
    def compute_is_retired(cls, data: dict | object) -> dict:
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
    retired_at: datetime | None = None


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
    def compute_is_retired(cls, data: dict | object) -> dict:
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
    retired_at: datetime | None = None


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
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# Vendor
# ===================================================================


class VendorBase(SQLModel):
    """Shared fields for Vendor schemas."""

    name: str
    url: str | None = None
    location: str | None = None
    notes: str | None = None


class VendorCreate(VendorBase):
    """Schema for creating a Vendor."""

    pass


class VendorUpdate(SQLModel):
    """Schema for partially updating a Vendor."""

    name: str | None = None
    url: str | None = None
    location: str | None = None
    notes: str | None = None
    retired_at: datetime | None = None


class VendorRead(VendorBase):
    """Schema returned when reading a Vendor.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Vendor name.
    url : str | None
        Shop website URL.
    location : str | None
        City, address, etc.
    notes : str | None
        Free-text notes.
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
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)


# ===================================================================
# StorageType
# ===================================================================


class StorageTypeBase(SQLModel):
    """Shared fields for StorageType schemas."""

    name: str


class StorageTypeCreate(StorageTypeBase):
    """Schema for creating a StorageType."""

    pass


class StorageTypeUpdate(SQLModel):
    """Schema for partially updating a StorageType."""

    name: str | None = None
    retired_at: datetime | None = None


class StorageTypeRead(StorageTypeBase):
    """Schema returned when reading a StorageType.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Storage type name.
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
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``."""
        return _compute_is_retired(cls, data)

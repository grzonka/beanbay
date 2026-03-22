"""Read / write schemas for the Cupping model.

Schemas for creating, updating, and reading SCAA-protocol cupping
evaluations with linked flavor tags and person names.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator
from sqlmodel import SQLModel

from beanbay.schemas.tag import FlavorTagRead


# ---------------------------------------------------------------------------
# CuppingCreate
# ---------------------------------------------------------------------------


class CuppingCreate(SQLModel):
    """Schema for creating a Cupping.

    Attributes
    ----------
    bag_id : uuid.UUID
        Foreign key to the bag being cupped.
    person_id : uuid.UUID
        Foreign key to the person who cupped.
    cupped_at : datetime
        When the cupping session happened.
    dry_fragrance : float | None
        Ground coffee aroma (0-9 SCAA).
    wet_aroma : float | None
        Aroma after adding water (0-9).
    brightness : float | None
        Acidity / vibrancy (0-9).
    flavor : float | None
        Overall taste quality (0-9).
    body : float | None
        Weight / mouthfeel (0-9).
    finish : float | None
        Aftertaste length and quality (0-9).
    sweetness : float | None
        Sweetness (0-9).
    clean_cup : float | None
        Absence of defects (0-9).
    complexity : float | None
        Flavor layers / depth (0-9).
    uniformity : float | None
        Cup-to-cup consistency (0-9).
    cuppers_correction : float | None
        Personal adjustment (can be negative).
    total_score : float | None
        0-100 SCAA scale.
    notes : str | None
        Free-text notes.
    flavor_tag_ids : list[uuid.UUID]
        Flavor tag IDs to link via M2M.
    """

    bag_id: uuid.UUID
    person_id: uuid.UUID
    cupped_at: datetime

    dry_fragrance: float | None = Field(default=None, ge=0, le=9)
    wet_aroma: float | None = Field(default=None, ge=0, le=9)
    brightness: float | None = Field(default=None, ge=0, le=9)
    flavor: float | None = Field(default=None, ge=0, le=9)
    body: float | None = Field(default=None, ge=0, le=9)
    finish: float | None = Field(default=None, ge=0, le=9)
    sweetness: float | None = Field(default=None, ge=0, le=9)
    clean_cup: float | None = Field(default=None, ge=0, le=9)
    complexity: float | None = Field(default=None, ge=0, le=9)
    uniformity: float | None = Field(default=None, ge=0, le=9)
    cuppers_correction: float | None = None
    total_score: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None

    flavor_tag_ids: list[uuid.UUID] = []


# ---------------------------------------------------------------------------
# CuppingUpdate
# ---------------------------------------------------------------------------


class CuppingUpdate(SQLModel):
    """Schema for partially updating a Cupping.

    All fields are optional so callers can send only the fields they
    want to change.

    Attributes
    ----------
    cupped_at : datetime | None
        Updated cupping time.
    dry_fragrance : float | None
        Updated ground coffee aroma (0-9).
    wet_aroma : float | None
        Updated wet aroma (0-9).
    brightness : float | None
        Updated brightness (0-9).
    flavor : float | None
        Updated flavor (0-9).
    body : float | None
        Updated body (0-9).
    finish : float | None
        Updated finish (0-9).
    sweetness : float | None
        Updated sweetness (0-9).
    clean_cup : float | None
        Updated clean cup (0-9).
    complexity : float | None
        Updated complexity (0-9).
    uniformity : float | None
        Updated uniformity (0-9).
    cuppers_correction : float | None
        Updated cupper's correction.
    total_score : float | None
        Updated total score (0-100).
    notes : str | None
        Updated notes.
    flavor_tag_ids : list[uuid.UUID] | None
        Updated flavor tag IDs; ``None`` means don't touch.
    """

    bag_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    cupped_at: datetime | None = None
    dry_fragrance: float | None = Field(default=None, ge=0, le=9)
    wet_aroma: float | None = Field(default=None, ge=0, le=9)
    brightness: float | None = Field(default=None, ge=0, le=9)
    flavor: float | None = Field(default=None, ge=0, le=9)
    body: float | None = Field(default=None, ge=0, le=9)
    finish: float | None = Field(default=None, ge=0, le=9)
    sweetness: float | None = Field(default=None, ge=0, le=9)
    clean_cup: float | None = Field(default=None, ge=0, le=9)
    complexity: float | None = Field(default=None, ge=0, le=9)
    uniformity: float | None = Field(default=None, ge=0, le=9)
    cuppers_correction: float | None = None
    total_score: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = None
    retired_at: datetime | None = None

    flavor_tag_ids: list[uuid.UUID] | None = None


# ---------------------------------------------------------------------------
# CuppingRead
# ---------------------------------------------------------------------------


class CuppingRead(SQLModel):
    """Schema returned when reading a Cupping.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bag_id : uuid.UUID
        Foreign key to the bag.
    person_id : uuid.UUID
        Foreign key to the person.
    cupped_at : datetime
        When the cupping session happened.
    dry_fragrance : float | None
        Ground coffee aroma (0-9 SCAA).
    wet_aroma : float | None
        Aroma after adding water (0-9).
    brightness : float | None
        Acidity / vibrancy (0-9).
    flavor : float | None
        Overall taste quality (0-9).
    body : float | None
        Weight / mouthfeel (0-9).
    finish : float | None
        Aftertaste length and quality (0-9).
    sweetness : float | None
        Sweetness (0-9).
    clean_cup : float | None
        Absence of defects (0-9).
    complexity : float | None
        Flavor layers / depth (0-9).
    uniformity : float | None
        Cup-to-cup consistency (0-9).
    cuppers_correction : float | None
        Personal adjustment (can be negative).
    total_score : float | None
        0-100 SCAA scale.
    notes : str | None
        Free-text notes.
    created_at : datetime
        Row creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    person_name : str
        Name of the person who performed the cupping.
    flavor_tags : list[FlavorTagRead]
        Nested flavor tag objects.
    """

    id: uuid.UUID
    bag_id: uuid.UUID
    person_id: uuid.UUID
    cupped_at: datetime

    dry_fragrance: float | None = None
    wet_aroma: float | None = None
    brightness: float | None = None
    flavor: float | None = None
    body: float | None = None
    finish: float | None = None
    sweetness: float | None = None
    clean_cup: float | None = None
    complexity: float | None = None
    uniformity: float | None = None
    cuppers_correction: float | None = None
    total_score: float | None = None
    notes: str | None = None

    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None = None
    is_retired: bool = False

    person_name: str = ""
    flavor_tags: list[FlavorTagRead] = []

    @model_validator(mode="before")
    @classmethod
    def compute_cupping_fields(cls, data: dict | object) -> dict:
        """Compute ``is_retired``, ``person_name``, and extract ORM fields.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : dict | object
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        dict
            A dict with computed fields populated.
        """
        if isinstance(data, dict):
            data["is_retired"] = data.get("retired_at") is not None
            return data

        # ORM model -- extract all fields
        d: dict[str, Any] = {}
        for field_name in (
            "id",
            "bag_id",
            "person_id",
            "cupped_at",
            "dry_fragrance",
            "wet_aroma",
            "brightness",
            "flavor",
            "body",
            "finish",
            "sweetness",
            "clean_cup",
            "complexity",
            "uniformity",
            "cuppers_correction",
            "total_score",
            "notes",
            "created_at",
            "updated_at",
            "retired_at",
        ):
            d[field_name] = getattr(data, field_name, None)

        d["is_retired"] = d["retired_at"] is not None

        # Extract person_name from the person relationship
        person = getattr(data, "person", None)
        d["person_name"] = person.name if person else ""

        # Extract flavor tags from the relationship
        d["flavor_tags"] = getattr(data, "flavor_tags", [])

        return d

"""Read / write schemas for BeanRating and BeanTaste models."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from beanbay.schemas.tag import FlavorTagRead


# ===================================================================
# BeanTaste schemas
# ===================================================================


class BeanTasteBase(SQLModel):
    """Shared sensory-profile fields for BeanTaste schemas.

    Attributes
    ----------
    score : float | None
        Overall score (0-10).
    acidity : float | None
        Acidity score (0-10).
    sweetness : float | None
        Sweetness score (0-10).
    body : float | None
        Body score (0-10).
    complexity : float | None
        Complexity score (0-10).
    aroma : float | None
        Aroma score (0-10).
    clean_cup : float | None
        Clean-cup score (0-10).
    notes : str | None
        Free-text tasting notes.
    """

    score: float | None = Field(default=None, ge=0, le=10)
    acidity: float | None = Field(default=None, ge=0, le=10)
    sweetness: float | None = Field(default=None, ge=0, le=10)
    body: float | None = Field(default=None, ge=0, le=10)
    complexity: float | None = Field(default=None, ge=0, le=10)
    aroma: float | None = Field(default=None, ge=0, le=10)
    clean_cup: float | None = Field(default=None, ge=0, le=10)
    notes: str | None = None


class BeanTasteCreate(BeanTasteBase):
    """Schema for creating a BeanTaste.

    Attributes
    ----------
    flavor_tag_ids : list[uuid.UUID]
        Flavor tag IDs to link via M2M.
    """

    flavor_tag_ids: list[uuid.UUID] = []


class BeanTasteUpdate(SQLModel):
    """Schema for partially updating a BeanTaste.

    All fields optional; only provided fields are updated.

    Attributes
    ----------
    score : float | None
        Overall score (0-10).
    acidity : float | None
        Acidity score (0-10).
    sweetness : float | None
        Sweetness score (0-10).
    body : float | None
        Body score (0-10).
    complexity : float | None
        Complexity score (0-10).
    aroma : float | None
        Aroma score (0-10).
    clean_cup : float | None
        Clean-cup score (0-10).
    notes : str | None
        Free-text tasting notes.
    flavor_tag_ids : list[uuid.UUID] | None
        Flavor tag IDs to replace the M2M list.
    """

    score: float | None = Field(default=None, ge=0, le=10)
    acidity: float | None = Field(default=None, ge=0, le=10)
    sweetness: float | None = Field(default=None, ge=0, le=10)
    body: float | None = Field(default=None, ge=0, le=10)
    complexity: float | None = Field(default=None, ge=0, le=10)
    aroma: float | None = Field(default=None, ge=0, le=10)
    clean_cup: float | None = Field(default=None, ge=0, le=10)
    notes: str | None = None
    flavor_tag_ids: list[uuid.UUID] | None = None


class BeanTasteRead(BeanTasteBase):
    """Schema returned when reading a BeanTaste.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_rating_id : uuid.UUID
        Parent rating's primary key.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    flavor_tags : list[FlavorTagRead]
        Nested flavor tag objects.
    """

    id: uuid.UUID
    bean_rating_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    flavor_tags: list[FlavorTagRead] = []

    @model_validator(mode="before")
    @classmethod
    def extract_orm_fields(cls, data: dict | object) -> dict:
        """Extract fields from ORM model instance if needed.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : dict | object
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        dict
            A dict with all fields populated.
        """
        if isinstance(data, dict):
            return data
        # ORM model — extract all fields
        data_dict: dict[str, Any] = {}
        for field in (
            "id",
            "bean_rating_id",
            "score",
            "acidity",
            "sweetness",
            "body",
            "complexity",
            "aroma",
            "clean_cup",
            "notes",
            "created_at",
            "updated_at",
        ):
            data_dict[field] = getattr(data, field, None)
        data_dict["flavor_tags"] = getattr(data, "flavor_tags", [])
        return data_dict


# ===================================================================
# BeanRating schemas
# ===================================================================


class BeanRatingCreate(SQLModel):
    """Schema for creating a BeanRating.

    Attributes
    ----------
    person_id : uuid.UUID
        ID of the person giving the rating.
    rated_at : datetime | None
        When the rating was given. Defaults to now if not provided.
    taste : BeanTasteCreate | None
        Optional taste profile to create inline.
    """

    person_id: uuid.UUID
    rated_at: datetime | None = None
    taste: BeanTasteCreate | None = None


class BeanRatingRead(SQLModel):
    """Schema returned when reading a BeanRating.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Rated bean's primary key.
    person_id : uuid.UUID
        Rating person's primary key.
    rated_at : datetime
        When the rating was given.
    created_at : datetime
        Row creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    person_name : str
        Name of the person who gave the rating.
    taste : BeanTasteRead | None
        Nested taste profile, if present.
    """

    id: uuid.UUID
    bean_id: uuid.UUID
    person_id: uuid.UUID
    rated_at: datetime
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool
    person_name: str
    taste: BeanTasteRead | None = None

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired_and_person_name(cls, data: dict | object) -> dict:
        """Inject ``is_retired`` and ``person_name`` from ORM data.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : dict | object
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        dict
            A dict with ``is_retired`` and ``person_name`` populated.
        """
        if isinstance(data, dict):
            data["is_retired"] = data.get("retired_at") is not None
            return data
        # ORM model — extract all fields
        data_dict: dict[str, Any] = {}
        for field in (
            "id",
            "bean_id",
            "person_id",
            "rated_at",
            "created_at",
            "updated_at",
            "retired_at",
        ):
            data_dict[field] = getattr(data, field, None)
        data_dict["is_retired"] = data_dict["retired_at"] is not None
        person = getattr(data, "person", None)
        data_dict["person_name"] = person.name if person else ""
        taste = getattr(data, "taste", None)
        data_dict["taste"] = taste
        return data_dict

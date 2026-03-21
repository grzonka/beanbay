"""Read / write schemas for the Bean and Bag models."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel

from beanbay.schemas.tag import (
    BeanVarietyRead,
    OriginRead,
    ProcessMethodRead,
    RoasterRead,
)


# ===================================================================
# Bag schemas (defined first so BeanRead can reference BagRead)
# ===================================================================


class BagBase(SQLModel):
    """Shared fields for Bag schemas.

    Attributes
    ----------
    roast_date : date | None
        Date the coffee was roasted.
    opened_at : date | None
        Date the bag was opened.
    weight : float
        Weight in grams.
    price : float | None
        Price paid for the bag.
    is_preground : bool
        Whether the coffee is pre-ground.
    notes : str | None
        Free-text notes.
    """

    roast_date: date | None = None
    opened_at: date | None = None
    weight: float
    price: float | None = None
    is_preground: bool = False
    notes: str | None = None


class BagCreate(BagBase):
    """Schema for creating a Bag.

    The ``bean_id`` comes from the URL path, not the request body.
    """

    pass


class BagUpdate(SQLModel):
    """Schema for partially updating a Bag.

    All fields are optional so callers can send only the fields they
    want to change.
    """

    roast_date: date | None = None
    opened_at: date | None = None
    weight: float | None = None
    price: float | None = None
    is_preground: bool | None = None
    notes: str | None = None


class BagRead(BagBase):
    """Schema returned when reading a Bag.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Parent bean's primary key.
    roast_date : date | None
        Date the coffee was roasted.
    opened_at : date | None
        Date the bag was opened.
    weight : float
        Weight in grams.
    price : float | None
        Price paid.
    is_preground : bool
        Whether the coffee is pre-ground.
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
    bean_id: uuid.UUID
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
        # ORM model — extract all fields
        fields = (
            "id",
            "bean_id",
            "roast_date",
            "opened_at",
            "weight",
            "price",
            "is_preground",
            "notes",
            "created_at",
            "updated_at",
            "retired_at",
        )
        data_dict: dict[str, Any] = {
            f: getattr(data, f, None) for f in fields
        }
        data_dict["is_retired"] = data_dict["retired_at"] is not None
        return data_dict


# ===================================================================
# Bean schemas
# ===================================================================


class BeanBase(SQLModel):
    """Shared fields for Bean schemas.

    Attributes
    ----------
    name : str
        Name of the bean / blend.
    notes : str | None
        Free-text notes.
    """

    name: str
    notes: str | None = None


class BeanCreate(BeanBase):
    """Schema for creating a Bean.

    Attributes
    ----------
    roaster_id : uuid.UUID | None
        Optional roaster FK.
    origin_ids : list[uuid.UUID]
        Origin IDs for M2M.
    process_ids : list[uuid.UUID]
        ProcessMethod IDs for M2M.
    variety_ids : list[uuid.UUID]
        BeanVariety IDs for M2M.
    """

    roaster_id: uuid.UUID | None = None
    origin_ids: list[uuid.UUID] = []
    process_ids: list[uuid.UUID] = []
    variety_ids: list[uuid.UUID] = []


class BeanUpdate(SQLModel):
    """Schema for partially updating a Bean.

    All fields are optional so callers can send only the fields they
    want to change.
    """

    name: str | None = None
    roaster_id: uuid.UUID | None = None
    notes: str | None = None
    origin_ids: list[uuid.UUID] | None = None
    process_ids: list[uuid.UUID] | None = None
    variety_ids: list[uuid.UUID] | None = None


class BeanRead(BeanBase):
    """Schema returned when reading a Bean.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    roaster_id : uuid.UUID | None
        Roaster FK.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    roaster : RoasterRead | None
        Nested roaster data.
    origins : list[OriginRead]
        Nested origins.
    processes : list[ProcessMethodRead]
        Nested process methods.
    varieties : list[BeanVarietyRead]
        Nested bean varieties.
    bags : list[BagRead]
        Nested non-retired bags.
    """

    id: uuid.UUID
    roaster_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool
    roaster: RoasterRead | None = None
    origins: list[OriginRead] = []
    processes: list[ProcessMethodRead] = []
    varieties: list[BeanVarietyRead] = []
    bags: list[BagRead] = []

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired_and_filter_bags(cls, data: dict | object) -> dict:
        """Inject ``is_retired`` and filter out retired bags.

        Parameters
        ----------
        cls : type
            The model class (unused but required by pydantic).
        data : dict | object
            Raw input -- either a dict or an ORM model instance.

        Returns
        -------
        dict
            A dict with ``is_retired`` populated and bags filtered.
        """
        if isinstance(data, dict):
            data["is_retired"] = data.get("retired_at") is not None
            # Filter retired bags if present
            if "bags" in data and data["bags"] is not None:
                data["bags"] = [
                    b
                    for b in data["bags"]
                    if (
                        b.get("retired_at") is None
                        if isinstance(b, dict)
                        else getattr(b, "retired_at", None) is None
                    )
                ]
            return data
        # ORM model — extract all fields
        data_dict: dict[str, Any] = {}
        for field in (
            "id",
            "name",
            "roaster_id",
            "notes",
            "created_at",
            "updated_at",
            "retired_at",
        ):
            data_dict[field] = getattr(data, field, None)
        data_dict["is_retired"] = data_dict["retired_at"] is not None
        data_dict["roaster"] = getattr(data, "roaster", None)
        data_dict["origins"] = getattr(data, "origins", [])
        data_dict["processes"] = getattr(data, "processes", [])
        data_dict["varieties"] = getattr(data, "varieties", [])
        # Filter out retired bags
        all_bags = getattr(data, "bags", [])
        data_dict["bags"] = [
            b for b in all_bags if getattr(b, "retired_at", None) is None
        ]
        return data_dict

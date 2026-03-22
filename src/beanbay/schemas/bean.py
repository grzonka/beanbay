"""Read / write schemas for the Bean and Bag models."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from beanbay.models.enums import BeanMixType, BeanUseType
from beanbay.schemas.tag import (
    BeanVarietyRead,
    FlavorTagRead,
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
    bought_at : date | None
        Date the bag was purchased.
    vendor_id : uuid.UUID | None
        Foreign key to the vendor / shop.
    frozen_at : datetime | None
        Timestamp when the bag was frozen.
    thawed_at : datetime | None
        Timestamp when the bag was thawed.
    storage_type_id : uuid.UUID | None
        Foreign key to the frozen-storage type.
    best_date : date | None
        Best-before date.
    """

    roast_date: date | None = None
    opened_at: date | None = None
    weight: float
    price: float | None = None
    is_preground: bool = False
    notes: str | None = None
    bought_at: date | None = None
    vendor_id: uuid.UUID | None = None
    frozen_at: datetime | None = None
    thawed_at: datetime | None = None
    storage_type_id: uuid.UUID | None = None
    best_date: date | None = None


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
    bought_at: date | None = None
    vendor_id: uuid.UUID | None = None
    frozen_at: datetime | None = None
    thawed_at: datetime | None = None
    storage_type_id: uuid.UUID | None = None
    best_date: date | None = None
    retired_at: datetime | None = None


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
    bought_at : date | None
        Date the bag was purchased.
    vendor_id : uuid.UUID | None
        Foreign key to the vendor / shop.
    frozen_at : datetime | None
        Timestamp when the bag was frozen.
    thawed_at : datetime | None
        Timestamp when the bag was thawed.
    storage_type_id : uuid.UUID | None
        Foreign key to the frozen-storage type.
    best_date : date | None
        Best-before date.
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
            "bought_at",
            "vendor_id",
            "frozen_at",
            "thawed_at",
            "storage_type_id",
            "best_date",
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


class OriginWithPercentage(SQLModel):
    """An origin reference with an optional blend percentage.

    Attributes
    ----------
    origin_id : uuid.UUID
        The origin's primary key.
    percentage : float | None
        Blend percentage (0--100). ``None`` if not specified.
    """

    origin_id: uuid.UUID
    percentage: float | None = Field(default=None, ge=0, le=100)


class BeanBase(SQLModel):
    """Shared fields for Bean schemas.

    Attributes
    ----------
    name : str
        Name of the bean / blend.
    notes : str | None
        Free-text notes.
    roast_degree : float | None
        Roast degree on a 0--10 scale.
    bean_mix_type : BeanMixType
        Whether the bean is single origin, blend, or unknown.
    bean_use_type : BeanUseType | None
        Roaster's intended use (filter, espresso, omni).
    decaf : bool
        Whether the bean is decaffeinated.
    url : str | None
        URL to the roaster's product page.
    ean : str | None
        EAN / barcode for the bean.
    """

    name: str
    notes: str | None = None
    roast_degree: float | None = Field(default=None, ge=0, le=10)
    bean_mix_type: BeanMixType = BeanMixType.UNKNOWN
    bean_use_type: BeanUseType | None = None
    decaf: bool = False
    url: str | None = None
    ean: str | None = None


class BeanCreate(BeanBase):
    """Schema for creating a Bean.

    Attributes
    ----------
    roaster_id : uuid.UUID | None
        Optional roaster FK.
    origin_ids : list[uuid.UUID]
        Origin IDs for M2M (plain, no percentage).
    origins : list[OriginWithPercentage]
        Origins with optional blend percentages.
    process_ids : list[uuid.UUID]
        ProcessMethod IDs for M2M.
    variety_ids : list[uuid.UUID]
        BeanVariety IDs for M2M.
    flavor_tag_ids : list[uuid.UUID]
        FlavorTag IDs for M2M.
    """

    roaster_id: uuid.UUID | None = None
    origin_ids: list[uuid.UUID] = []
    origins: list[OriginWithPercentage] = []
    process_ids: list[uuid.UUID] = []
    variety_ids: list[uuid.UUID] = []
    flavor_tag_ids: list[uuid.UUID] = []


class BeanUpdate(SQLModel):
    """Schema for partially updating a Bean.

    All fields are optional so callers can send only the fields they
    want to change.
    """

    name: str | None = None
    roaster_id: uuid.UUID | None = None
    notes: str | None = None
    roast_degree: float | None = Field(default=None, ge=0, le=10)
    bean_mix_type: BeanMixType | None = None
    bean_use_type: BeanUseType | None = None
    decaf: bool | None = None
    url: str | None = None
    ean: str | None = None
    origin_ids: list[uuid.UUID] | None = None
    origins: list[OriginWithPercentage] | None = None
    process_ids: list[uuid.UUID] | None = None
    variety_ids: list[uuid.UUID] | None = None
    flavor_tag_ids: list[uuid.UUID] | None = None
    retired_at: datetime | None = None


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
    flavor_tags : list[FlavorTagRead]
        Nested flavor tags (roaster's claimed flavors).
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
    flavor_tags: list[FlavorTagRead] = []
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
        from beanbay.models.bean import BeanOriginLink

        data_dict: dict[str, Any] = {}
        for field in (
            "id",
            "name",
            "roaster_id",
            "notes",
            "roast_degree",
            "bean_mix_type",
            "bean_use_type",
            "decaf",
            "url",
            "ean",
            "created_at",
            "updated_at",
            "retired_at",
        ):
            data_dict[field] = getattr(data, field, None)
        data_dict["is_retired"] = data_dict["retired_at"] is not None
        data_dict["roaster"] = getattr(data, "roaster", None)

        # Build origin dicts with percentage from link table
        from sqlmodel import Session, select

        sa_session = Session.object_session(data)
        raw_origins = getattr(data, "origins", [])
        if sa_session is not None and raw_origins:
            link_rows = sa_session.exec(
                select(BeanOriginLink).where(
                    BeanOriginLink.bean_id == data.id
                )
            ).all()
            pct_map = {lnk.origin_id: lnk.percentage for lnk in link_rows}
            origins_with_pct = []
            for origin in raw_origins:
                origin_dict: dict[str, Any] = {
                    "id": origin.id,
                    "name": origin.name,
                    "country": getattr(origin, "country", None),
                    "region": getattr(origin, "region", None),
                    "created_at": origin.created_at,
                    "retired_at": origin.retired_at,
                    "percentage": pct_map.get(origin.id),
                }
                origins_with_pct.append(origin_dict)
            data_dict["origins"] = origins_with_pct
        else:
            data_dict["origins"] = raw_origins

        data_dict["processes"] = getattr(data, "processes", [])
        data_dict["varieties"] = getattr(data, "varieties", [])
        data_dict["flavor_tags"] = getattr(data, "flavor_tags", [])
        # Filter out retired bags
        all_bags = getattr(data, "bags", [])
        data_dict["bags"] = [
            b for b in all_bags if getattr(b, "retired_at", None) is None
        ]
        return data_dict

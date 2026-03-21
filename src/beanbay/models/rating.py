"""BeanRating and BeanTaste models for BeanBay.

BeanRating is an append-only rating record linking a person to a bean.
BeanTaste holds the sensory profile for a rating (1:1 with BeanRating),
including numeric scores and M2M flavor tags.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Field, Relationship, SQLModel

from beanbay.models.base import uuid4_default


# ---------------------------------------------------------------------------
# Junction / link model for BeanTaste M2M to FlavorTag
# ---------------------------------------------------------------------------


class BeanTasteFlavorTagLink(SQLModel, table=True):
    """Link table between BeanTaste and FlavorTag.

    Attributes
    ----------
    bean_taste_id : uuid.UUID
        Foreign key to the bean taste.
    flavor_tag_id : uuid.UUID
        Foreign key to the flavor tag.
    """

    __tablename__ = "bean_taste_flavor_tags"

    bean_taste_id: uuid.UUID = Field(
        foreign_key="bean_tastes.id", primary_key=True
    )
    flavor_tag_id: uuid.UUID = Field(
        foreign_key="flavor_tags.id", primary_key=True
    )


# ---------------------------------------------------------------------------
# BeanRating model (append-only)
# ---------------------------------------------------------------------------


class BeanRating(SQLModel, table=True):
    """An append-only rating of a bean by a person.

    No ``updated_at`` column — to "update" a rating, create a new one.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Foreign key to the bean being rated.
    person_id : uuid.UUID
        Foreign key to the person who gave the rating.
    rated_at : datetime
        When the rating was given.
    created_at : datetime
        Row creation timestamp (server default).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "bean_ratings"

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_id: uuid.UUID = Field(foreign_key="beans.id", index=True)
    person_id: uuid.UUID = Field(foreign_key="people.id", index=True)
    rated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    retired_at: datetime | None = None

    # Relationships
    bean: Optional["Bean"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    person: Optional["Person"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    taste: Optional["BeanTaste"] = Relationship(
        back_populates="bean_rating",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )


# ---------------------------------------------------------------------------
# BeanTaste model (1:1 with BeanRating)
# ---------------------------------------------------------------------------


class BeanTaste(SQLModel, table=True):
    """Sensory profile for a bean rating (1:1 with BeanRating).

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_rating_id : uuid.UUID
        Unique foreign key to the parent rating (enforces 1:1).
    score : float | None
        Overall score (0-10).
    acidity : float | None
        Acidity score (0-10).
    sweetness : float | None
        Sweetness score (0-10).
    body : float | None
        Body score (0-10).
    bitterness : float | None
        Bitterness score (0-10).
    aroma : float | None
        Aroma score (0-10).
    intensity : float | None
        Intensity score (0-10).
    notes : str | None
        Free-text tasting notes.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    """

    __tablename__ = "bean_tastes"

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_rating_id: uuid.UUID = Field(
        foreign_key="bean_ratings.id", unique=True, index=True
    )
    score: float | None = None
    acidity: float | None = None
    sweetness: float | None = None
    body: float | None = None
    bitterness: float | None = None
    aroma: float | None = None
    intensity: float | None = None
    notes: str | None = None
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )

    # Relationships
    bean_rating: Optional[BeanRating] = Relationship(back_populates="taste")
    flavor_tags: list["FlavorTag"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BeanTasteFlavorTagLink,
    )

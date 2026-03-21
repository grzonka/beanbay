"""Brew-related models for BeanBay.

BrewSetup represents a reusable equipment configuration for brewing coffee,
referencing a required BrewMethod and optional Grinder, Brewer, Paper, and Water.

Brew represents an individual coffee brew event with parameters such as dose,
grind setting, temperature, and timing.

BrewTaste captures tasting notes and scores for a brew with M2M FlavorTag links.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

from beanbay.models.base import uuid4_default

if TYPE_CHECKING:
    from beanbay.models.bean import Bag
    from beanbay.models.equipment import Brewer, Grinder, Paper, Water
    from beanbay.models.person import Person
    from beanbay.models.tag import BrewMethod, FlavorTag, StopMode


# ---------------------------------------------------------------------------
# Junction table: BrewTaste <-> FlavorTag (M2M)
# ---------------------------------------------------------------------------


class BrewTasteFlavorTagLink(SQLModel, table=True):
    """Link table between BrewTaste and FlavorTag.

    Attributes
    ----------
    brew_taste_id : uuid.UUID
        Foreign key to the brew taste.
    flavor_tag_id : uuid.UUID
        Foreign key to the flavor tag.
    """

    __tablename__ = "brew_taste_flavor_tags"

    brew_taste_id: uuid.UUID = Field(
        foreign_key="brew_tastes.id", primary_key=True
    )
    flavor_tag_id: uuid.UUID = Field(
        foreign_key="flavor_tags.id", primary_key=True
    )


# ---------------------------------------------------------------------------
# BrewSetup
# ---------------------------------------------------------------------------


class BrewSetup(SQLModel, table=True):
    """A reusable brew setup combining a method with equipment.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str | None
        Optional human-readable name for the setup.
    brew_method_id : uuid.UUID
        Foreign key to the brew method (required).
    grinder_id : uuid.UUID | None
        Foreign key to the grinder (optional).
    brewer_id : uuid.UUID | None
        Foreign key to the brewer (optional).
    paper_id : uuid.UUID | None
        Foreign key to the paper (optional).
    water_id : uuid.UUID | None
        Foreign key to the water (optional).
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "brew_setups"

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str | None = Field(default=None, index=True)

    brew_method_id: uuid.UUID = Field(foreign_key="brew_methods.id")
    grinder_id: uuid.UUID | None = Field(default=None, foreign_key="grinders.id")
    brewer_id: uuid.UUID | None = Field(default=None, foreign_key="brewers.id")
    paper_id: uuid.UUID | None = Field(default=None, foreign_key="papers.id")
    water_id: uuid.UUID | None = Field(default=None, foreign_key="waters.id")

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

    # Relationships
    brew_method: "BrewMethod" = Relationship()  # type: ignore[name-defined]  # noqa: F821
    grinder: Optional["Grinder"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    brewer: Optional["Brewer"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    paper: Optional["Paper"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    water: Optional["Water"] = Relationship()  # type: ignore[name-defined]  # noqa: F821


# ---------------------------------------------------------------------------
# Brew
# ---------------------------------------------------------------------------


class Brew(SQLModel, table=True):
    """An individual coffee brew event.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bag_id : uuid.UUID
        Foreign key to the bag used.
    brew_setup_id : uuid.UUID
        Foreign key to the brew setup used.
    person_id : uuid.UUID
        Foreign key to the person who brewed.
    grind_setting : float | None
        Canonical numeric grind setting; null if preground.
    temperature : float | None
        Temperature in celsius; null for cold-brew.
    pressure : float | None
        Pressure in bar.
    flow_rate : float | None
        Flow rate in ml/s.
    dose : float
        Coffee dose in grams (required).
    yield_amount : float | None
        Yield in grams.
    pre_infusion_time : float | None
        Pre-infusion time in seconds.
    total_time : float | None
        Total brew time in seconds.
    stop_mode_id : uuid.UUID | None
        Foreign key to the stop mode (optional).
    is_failed : bool
        Whether the brew was considered failed.
    notes : str | None
        Free-text notes.
    brewed_at : datetime
        When the brew took place.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "brews"

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)

    bag_id: uuid.UUID = Field(foreign_key="bags.id")
    brew_setup_id: uuid.UUID = Field(foreign_key="brew_setups.id")
    person_id: uuid.UUID = Field(foreign_key="people.id")

    grind_setting: float | None = None
    temperature: float | None = None
    pressure: float | None = None
    flow_rate: float | None = None
    dose: float
    yield_amount: float | None = None
    pre_infusion_time: float | None = None
    total_time: float | None = None

    stop_mode_id: uuid.UUID | None = Field(
        default=None, foreign_key="stop_modes.id"
    )
    is_failed: bool = Field(default=False)
    notes: str | None = None
    brewed_at: datetime

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None

    # Relationships
    bag: "Bag" = Relationship()  # type: ignore[name-defined]  # noqa: F821
    brew_setup: BrewSetup = Relationship()
    person: "Person" = Relationship()  # type: ignore[name-defined]  # noqa: F821
    stop_mode: Optional["StopMode"] = Relationship()  # type: ignore[name-defined]  # noqa: F821
    taste: Optional["BrewTaste"] = Relationship(
        back_populates="brew",
        sa_relationship_kwargs={"uselist": False},
    )


# ---------------------------------------------------------------------------
# BrewTaste
# ---------------------------------------------------------------------------


class BrewTaste(SQLModel, table=True):
    """Tasting notes and scores for a brew (1:1 with Brew).

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    brew_id : uuid.UUID
        Foreign key to the parent brew (unique — 1:1).
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

    __tablename__ = "brew_tastes"
    __table_args__ = (
        UniqueConstraint("brew_id", name="uq_brew_taste_brew_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    brew_id: uuid.UUID = Field(foreign_key="brews.id", index=True)

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
    brew: Brew = Relationship(back_populates="taste")
    flavor_tags: list["FlavorTag"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BrewTasteFlavorTagLink,
    )

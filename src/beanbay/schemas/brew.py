"""Read / write schemas for BrewSetup, Brew, and BrewTaste.

Schemas for creating, updating, and reading brew setups with light
nesting of related equipment names, and brew events with inline taste.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import Field, SQLModel

from beanbay.schemas.tag import FlavorTagRead


# ---------------------------------------------------------------------------
# BrewSetup
# ---------------------------------------------------------------------------


class BrewSetupBase(SQLModel):
    """Shared fields for BrewSetup schemas.

    Attributes
    ----------
    name : str | None
        Optional name for the setup.
    """

    name: str | None = None


class BrewSetupCreate(BrewSetupBase):
    """Schema for creating a BrewSetup.

    Attributes
    ----------
    brew_method_id : uuid.UUID
        Required brew method FK.
    grinder_id : uuid.UUID | None
        Optional grinder FK.
    brewer_id : uuid.UUID | None
        Optional brewer FK.
    paper_id : uuid.UUID | None
        Optional paper FK.
    water_id : uuid.UUID | None
        Optional water FK.
    """

    brew_method_id: uuid.UUID
    grinder_id: uuid.UUID | None = None
    brewer_id: uuid.UUID | None = None
    paper_id: uuid.UUID | None = None
    water_id: uuid.UUID | None = None


class BrewSetupUpdate(SQLModel):
    """Schema for partially updating a BrewSetup.

    Attributes
    ----------
    name : str | None
        Updated name.
    brew_method_id : uuid.UUID | None
        Updated brew method FK.
    grinder_id : uuid.UUID | None
        Updated grinder FK.
    brewer_id : uuid.UUID | None
        Updated brewer FK.
    paper_id : uuid.UUID | None
        Updated paper FK.
    water_id : uuid.UUID | None
        Updated water FK.
    """

    name: str | None = None
    brew_method_id: uuid.UUID | None = None
    grinder_id: uuid.UUID | None = None
    brewer_id: uuid.UUID | None = None
    paper_id: uuid.UUID | None = None
    water_id: uuid.UUID | None = None
    retired_at: datetime | None = None


class BrewSetupRead(BrewSetupBase):
    """Schema returned when reading a BrewSetup.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    brew_method_id : uuid.UUID
        Brew method FK.
    grinder_id : uuid.UUID | None
        Grinder FK.
    brewer_id : uuid.UUID | None
        Brewer FK.
    paper_id : uuid.UUID | None
        Paper FK.
    water_id : uuid.UUID | None
        Water FK.
    brew_method_name : str | None
        Name of the linked brew method.
    grinder_name : str | None
        Name of the linked grinder.
    brewer_name : str | None
        Name of the linked brewer.
    paper_name : str | None
        Name of the linked paper.
    water_name : str | None
        Name of the linked water.
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool

    brew_method_id: uuid.UUID
    grinder_id: uuid.UUID | None
    brewer_id: uuid.UUID | None
    paper_id: uuid.UUID | None
    water_id: uuid.UUID | None

    brew_method_name: str | None = None
    grinder_name: str | None = None
    brewer_name: str | None = None
    paper_name: str | None = None
    water_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def compute_brew_setup_fields(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` and extract nested equipment names.

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
        if not isinstance(data, dict):
            d: dict[str, Any] = {}
            for field in (
                "id",
                "name",
                "brew_method_id",
                "grinder_id",
                "brewer_id",
                "paper_id",
                "water_id",
                "created_at",
                "updated_at",
                "retired_at",
            ):
                d[field] = getattr(data, field, None)

            # Extract names from relationships
            brew_method = getattr(data, "brew_method", None)
            d["brew_method_name"] = brew_method.name if brew_method else None

            grinder = getattr(data, "grinder", None)
            d["grinder_name"] = grinder.name if grinder else None

            brewer = getattr(data, "brewer", None)
            d["brewer_name"] = brewer.name if brewer else None

            paper = getattr(data, "paper", None)
            d["paper_name"] = paper.name if paper else None

            water = getattr(data, "water", None)
            d["water_name"] = water.name if water else None

            data = d

        data["is_retired"] = data.get("retired_at") is not None
        return data


# ---------------------------------------------------------------------------
# BrewTaste
# ---------------------------------------------------------------------------


class BrewTasteBase(SQLModel):
    """Shared fields for BrewTaste schemas.

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
    bitterness : float | None
        Bitterness score (0-10).
    balance : float | None
        Balance score (0-10).
    aftertaste : float | None
        Aftertaste score (0-10).
    notes : str | None
        Free-text tasting notes.
    """

    score: float | None = Field(default=None, ge=0, le=10)
    acidity: float | None = Field(default=None, ge=0, le=10)
    sweetness: float | None = Field(default=None, ge=0, le=10)
    body: float | None = Field(default=None, ge=0, le=10)
    bitterness: float | None = Field(default=None, ge=0, le=10)
    balance: float | None = Field(default=None, ge=0, le=10)
    aftertaste: float | None = Field(default=None, ge=0, le=10)
    notes: str | None = None


class BrewTasteCreate(BrewTasteBase):
    """Schema for creating a BrewTaste.

    Attributes
    ----------
    flavor_tag_ids : list[uuid.UUID]
        Flavor tag IDs to link.
    """

    flavor_tag_ids: list[uuid.UUID] = []


class BrewTasteUpdate(SQLModel):
    """Schema for partially updating a BrewTaste.

    All fields are optional so callers can send only the fields they
    want to change.

    Attributes
    ----------
    score : float | None
        Updated overall score.
    acidity : float | None
        Updated acidity score.
    sweetness : float | None
        Updated sweetness score.
    body : float | None
        Updated body score.
    bitterness : float | None
        Updated bitterness score.
    balance : float | None
        Updated balance score.
    aftertaste : float | None
        Updated aftertaste score.
    notes : str | None
        Updated tasting notes.
    flavor_tag_ids : list[uuid.UUID] | None
        Updated flavor tag IDs; ``None`` means don't touch.
    """

    score: float | None = Field(default=None, ge=0, le=10)
    acidity: float | None = Field(default=None, ge=0, le=10)
    sweetness: float | None = Field(default=None, ge=0, le=10)
    body: float | None = Field(default=None, ge=0, le=10)
    bitterness: float | None = Field(default=None, ge=0, le=10)
    balance: float | None = Field(default=None, ge=0, le=10)
    aftertaste: float | None = Field(default=None, ge=0, le=10)
    notes: str | None = None
    flavor_tag_ids: list[uuid.UUID] | None = None


class BrewTasteRead(BrewTasteBase):
    """Schema returned when reading a BrewTaste.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    brew_id : uuid.UUID
        Parent brew FK.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    flavor_tags : list[FlavorTagRead]
        Nested flavor tags.
    """

    id: uuid.UUID
    brew_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    flavor_tags: list[FlavorTagRead] = []

    @model_validator(mode="before")
    @classmethod
    def extract_taste_fields(cls, data: dict | object) -> dict:
        """Extract fields from ORM model if needed.

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
        d: dict[str, Any] = {}
        for field in (
            "id",
            "brew_id",
            "score",
            "acidity",
            "sweetness",
            "body",
            "bitterness",
            "balance",
            "aftertaste",
            "notes",
            "created_at",
            "updated_at",
        ):
            d[field] = getattr(data, field, None)
        d["flavor_tags"] = getattr(data, "flavor_tags", [])
        return d


# ---------------------------------------------------------------------------
# Brew
# ---------------------------------------------------------------------------


class BrewCreate(SQLModel):
    """Schema for creating a Brew.

    Attributes
    ----------
    bag_id : uuid.UUID
        Required bag FK.
    brew_setup_id : uuid.UUID
        Required brew setup FK.
    person_id : uuid.UUID
        Required person FK.
    grind_setting : float | None
        Canonical numeric grind setting.
    grind_setting_display : str | None
        Human-readable grind display (takes precedence over grind_setting).
    temperature : float | None
        Temperature in celsius.
    pressure : float | None
        Pressure in bar.
    flow_rate : float | None
        Flow rate in ml/s.
    dose : float
        Coffee dose in grams.
    yield_amount : float | None
        Yield in grams.
    pre_infusion_time : float | None
        Pre-infusion time in seconds.
    total_time : float | None
        Total brew time in seconds.
    stop_mode_id : uuid.UUID | None
        Optional stop mode FK.
    is_failed : bool
        Whether the brew was considered failed.
    notes : str | None
        Free-text notes.
    brewed_at : datetime
        When the brew took place.
    taste : BrewTasteCreate | None
        Optional inline taste.
    """

    bag_id: uuid.UUID
    brew_setup_id: uuid.UUID
    person_id: uuid.UUID
    grind_setting: float | None = None
    grind_setting_display: str | None = None
    temperature: float | None = None
    pressure: float | None = None
    flow_rate: float | None = None
    dose: float
    yield_amount: float | None = None
    pre_infusion_time: float | None = None
    total_time: float | None = None
    stop_mode_id: uuid.UUID | None = None
    is_failed: bool = False
    notes: str | None = None
    brewed_at: datetime
    taste: BrewTasteCreate | None = None


class BrewUpdate(SQLModel):
    """Schema for partially updating a Brew.

    All fields are optional so callers can send only the fields they
    want to change.

    Attributes
    ----------
    bag_id : uuid.UUID | None
        Updated bag FK.
    brew_setup_id : uuid.UUID | None
        Updated brew setup FK.
    person_id : uuid.UUID | None
        Updated person FK.
    grind_setting : float | None
        Updated canonical grind setting.
    grind_setting_display : str | None
        Updated human-readable grind display.
    temperature : float | None
        Updated temperature.
    pressure : float | None
        Updated pressure.
    flow_rate : float | None
        Updated flow rate.
    dose : float | None
        Updated dose.
    yield_amount : float | None
        Updated yield.
    pre_infusion_time : float | None
        Updated pre-infusion time.
    total_time : float | None
        Updated total time.
    stop_mode_id : uuid.UUID | None
        Updated stop mode FK.
    is_failed : bool | None
        Updated failure flag.
    notes : str | None
        Updated notes.
    brewed_at : datetime | None
        Updated brew time.
    """

    bag_id: uuid.UUID | None = None
    brew_setup_id: uuid.UUID | None = None
    person_id: uuid.UUID | None = None
    grind_setting: float | None = None
    grind_setting_display: str | None = None
    temperature: float | None = None
    pressure: float | None = None
    flow_rate: float | None = None
    dose: float | None = None
    yield_amount: float | None = None
    pre_infusion_time: float | None = None
    total_time: float | None = None
    stop_mode_id: uuid.UUID | None = None
    is_failed: bool | None = None
    notes: str | None = None
    brewed_at: datetime | None = None
    retired_at: datetime | None = None


class BrewListRead(SQLModel):
    """Summary schema for listing brews.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    grind_setting : float | None
        Canonical grind setting.
    grind_setting_display : str | None
        Human-readable grind display.
    dose : float
        Coffee dose in grams.
    temperature : float | None
        Temperature in celsius.
    is_failed : bool
        Whether the brew was considered failed.
    brewed_at : datetime
        When the brew took place.
    created_at : datetime
        Creation timestamp.
    bean_name : str
        Name of the bean (via bag.bean.name).
    brew_method_name : str
        Name of the brew method (via brew_setup.brew_method.name).
    person_name : str
        Name of the person.
    score : float | None
        Overall taste score (from taste.score).
    """

    id: uuid.UUID
    grind_setting: float | None = None
    grind_setting_display: str | None = None
    dose: float
    temperature: float | None = None
    is_failed: bool
    brewed_at: datetime
    created_at: datetime
    bean_name: str
    brew_method_name: str
    person_name: str
    score: float | None = None


class BrewRead(SQLModel):
    """Full detail schema returned when reading a Brew.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bag_id : uuid.UUID
        Bag FK.
    brew_setup_id : uuid.UUID
        Brew setup FK.
    person_id : uuid.UUID
        Person FK.
    grind_setting : float | None
        Canonical grind setting.
    grind_setting_display : str | None
        Human-readable grind display.
    temperature : float | None
        Temperature in celsius.
    pressure : float | None
        Pressure in bar.
    flow_rate : float | None
        Flow rate in ml/s.
    dose : float
        Coffee dose in grams.
    yield_amount : float | None
        Yield in grams.
    pre_infusion_time : float | None
        Pre-infusion time in seconds.
    total_time : float | None
        Total brew time in seconds.
    stop_mode_id : uuid.UUID | None
        Stop mode FK.
    is_failed : bool
        Whether the brew was considered failed.
    notes : str | None
        Free-text notes.
    brewed_at : datetime
        When the brew took place.
    created_at : datetime
        Creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    retired_at : datetime | None
        Soft-delete timestamp.
    is_retired : bool
        Computed from ``retired_at``.
    bag : dict | None
        Nested bag data (with bean).
    brew_setup : BrewSetupRead | None
        Nested brew setup (with equipment names).
    person : dict | None
        Nested person data.
    taste : BrewTasteRead | None
        Nested taste data (with flavor tags).
    stop_mode : dict | None
        Nested stop mode data.
    """

    id: uuid.UUID
    bag_id: uuid.UUID
    brew_setup_id: uuid.UUID
    person_id: uuid.UUID
    grind_setting: float | None = None
    grind_setting_display: str | None = None
    temperature: float | None = None
    pressure: float | None = None
    flow_rate: float | None = None
    dose: float
    yield_amount: float | None = None
    pre_infusion_time: float | None = None
    total_time: float | None = None
    stop_mode_id: uuid.UUID | None = None
    is_failed: bool
    notes: str | None = None
    brewed_at: datetime
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None = None
    is_retired: bool = False
    bag: dict | None = None
    brew_setup: BrewSetupRead | None = None
    person: dict | None = None
    taste: BrewTasteRead | None = None
    stop_mode: dict | None = None

    @model_validator(mode="before")
    @classmethod
    def compute_brew_fields(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` and extract nested relationships.

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

        d: dict[str, Any] = {}
        for field in (
            "id",
            "bag_id",
            "brew_setup_id",
            "person_id",
            "grind_setting",
            "temperature",
            "pressure",
            "flow_rate",
            "dose",
            "yield_amount",
            "pre_infusion_time",
            "total_time",
            "stop_mode_id",
            "is_failed",
            "notes",
            "brewed_at",
            "created_at",
            "updated_at",
            "retired_at",
        ):
            d[field] = getattr(data, field, None)

        d["is_retired"] = d["retired_at"] is not None

        # Nested relationships — let the caller (router) attach these
        d["bag"] = getattr(data, "bag", None)
        d["brew_setup"] = getattr(data, "brew_setup", None)
        d["person"] = getattr(data, "person", None)
        d["taste"] = getattr(data, "taste", None)
        d["stop_mode"] = getattr(data, "stop_mode", None)

        # grind_setting_display is injected by the router, not the ORM
        d["grind_setting_display"] = None

        return d

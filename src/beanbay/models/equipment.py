"""Equipment models for BeanBay.

Grinder, Brewer (with M2M to BrewMethod/StopMode), Paper, Water,
and WaterMineral models, plus StrEnum types for brewer capabilities
and grinder dial configuration.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

from beanbay.models.base import uuid4_default


# ---------------------------------------------------------------------------
# StrEnum types
# ---------------------------------------------------------------------------


class TempControlType(StrEnum):
    """Temperature control capability levels."""

    NONE = "none"
    PRESET = "preset"
    PID = "pid"
    PROFILING = "profiling"


class PreinfusionType(StrEnum):
    """Pre-infusion capability levels."""

    NONE = "none"
    FIXED = "fixed"
    TIMED = "timed"
    ADJUSTABLE_PRESSURE = "adjustable_pressure"
    PROGRAMMABLE = "programmable"
    MANUAL = "manual"


class PressureControlType(StrEnum):
    """Pressure control capability levels."""

    FIXED = "fixed"
    OPV_ADJUSTABLE = "opv_adjustable"
    ELECTRONIC = "electronic"
    MANUAL_PROFILING = "manual_profiling"
    PROGRAMMABLE = "programmable"


class FlowControlType(StrEnum):
    """Flow control capability levels."""

    NONE = "none"
    MANUAL_PADDLE = "manual_paddle"
    MANUAL_VALVE = "manual_valve"
    PROGRAMMABLE = "programmable"


class DialType(StrEnum):
    """Grinder dial type."""

    STEPLESS = "stepless"
    STEPPED = "stepped"


# ---------------------------------------------------------------------------
# Junction / link models for Brewer M2M
# ---------------------------------------------------------------------------


class BrewerMethodLink(SQLModel, table=True):
    """Link table between Brewer and BrewMethod.

    Attributes
    ----------
    brewer_id : uuid.UUID
        Foreign key to the brewer.
    method_id : uuid.UUID
        Foreign key to the brew method.
    """

    __tablename__ = "brewer_methods"  # type: ignore[assignment]

    brewer_id: uuid.UUID = Field(
        foreign_key="brewers.id", primary_key=True
    )
    method_id: uuid.UUID = Field(
        foreign_key="brew_methods.id", primary_key=True
    )


class BrewerStopModeLink(SQLModel, table=True):
    """Link table between Brewer and StopMode.

    Attributes
    ----------
    brewer_id : uuid.UUID
        Foreign key to the brewer.
    stop_mode_id : uuid.UUID
        Foreign key to the stop mode.
    """

    __tablename__ = "brewer_stop_modes"  # type: ignore[assignment]

    brewer_id: uuid.UUID = Field(
        foreign_key="brewers.id", primary_key=True
    )
    stop_mode_id: uuid.UUID = Field(
        foreign_key="stop_modes.id", primary_key=True
    )


# ---------------------------------------------------------------------------
# Grinder
# ---------------------------------------------------------------------------


class Grinder(SQLModel, table=True):
    """A coffee grinder with dial configuration.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique grinder name.
    dial_type : DialType
        Whether the grinder is stepless or stepped.
    display_format : str
        Display format hint (e.g. ``"decimal"``).
    ring_sizes_json : str | None
        JSON-encoded list of ``[min, max, step]`` tuples describing
        each ring of the grinder dial.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "grinders"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    dial_type: DialType = Field(default=DialType.STEPLESS)
    display_format: str = Field(default="decimal")
    ring_sizes_json: str | None = None
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None


# ---------------------------------------------------------------------------
# Brewer
# ---------------------------------------------------------------------------


class Brewer(SQLModel, table=True):
    """A coffee brewer / espresso machine with capability flags.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique brewer name.
    temp_control_type : TempControlType
        Temperature control capability.
    temp_min : float | None
        Minimum temperature setting.
    temp_max : float | None
        Maximum temperature setting.
    temp_step : float | None
        Temperature step size.
    preinfusion_type : PreinfusionType
        Pre-infusion capability.
    preinfusion_max_time : float | None
        Maximum pre-infusion time in seconds.
    pressure_control_type : PressureControlType
        Pressure control capability.
    pressure_min : float | None
        Minimum pressure setting (bar).
    pressure_max : float | None
        Maximum pressure setting (bar).
    flow_control_type : FlowControlType
        Flow control capability.
    saturation_flow_rate : float | None
        Saturation flow rate (ml/s).
    has_bloom : bool
        Whether the brewer supports bloom phase.
    methods : list[BrewMethod]
        M2M relationship to supported brew methods.
    stop_modes : list[StopMode]
        M2M relationship to supported stop modes.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "brewers"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)

    # Temperature
    temp_control_type: TempControlType = Field(default=TempControlType.PID)
    temp_min: float | None = None
    temp_max: float | None = None
    temp_step: float | None = None

    # Pre-infusion
    preinfusion_type: PreinfusionType = Field(default=PreinfusionType.NONE)
    preinfusion_max_time: float | None = None

    # Pressure
    pressure_control_type: PressureControlType = Field(
        default=PressureControlType.FIXED
    )
    pressure_min: float | None = None
    pressure_max: float | None = None

    # Flow
    flow_control_type: FlowControlType = Field(default=FlowControlType.NONE)
    saturation_flow_rate: float | None = None

    # Bloom
    has_bloom: bool = Field(default=False)

    # M2M relationships
    methods: list["BrewMethod"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BrewerMethodLink,
    )
    stop_modes: list["StopMode"] = Relationship(  # type: ignore[name-defined]  # noqa: F821
        link_model=BrewerStopModeLink,
    )

    # Timestamps
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------


class Paper(SQLModel, table=True):
    """A filter paper product.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique paper name.
    notes : str | None
        Optional notes.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "papers"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    notes: str | None = None
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None


# ---------------------------------------------------------------------------
# Water + WaterMineral
# ---------------------------------------------------------------------------


class Water(SQLModel, table=True):
    """A water recipe / profile.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    name : str
        Unique water name.
    notes : str | None
        Optional notes.
    minerals : list[WaterMineral]
        Nested mineral composition.
    created_at : datetime
        Row creation timestamp (server default).
    updated_at : datetime
        Last-modified timestamp (server default, auto-updated).
    retired_at : datetime | None
        Soft-delete timestamp; ``None`` while active.
    """

    __tablename__ = "waters"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    name: str = Field(index=True, unique=True)
    notes: str | None = None

    minerals: list["WaterMineral"] = Relationship(
        back_populates="water",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
    retired_at: datetime | None = None


class WaterMineral(SQLModel, table=True):
    """A mineral component of a water recipe.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    water_id : uuid.UUID
        Foreign key to the parent water.
    mineral_name : str
        Name of the mineral (e.g. ``"calcium"``, ``"magnesium"``).
    ppm : float
        Concentration in parts per million.
    """

    __tablename__ = "water_minerals"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("water_id", "mineral_name", name="uq_water_mineral"),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    water_id: uuid.UUID = Field(foreign_key="waters.id", index=True)
    mineral_name: str
    ppm: float

    water: Water | None = Relationship(back_populates="minerals")

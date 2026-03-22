"""Read / write schemas for equipment models.

Grinder, Brewer, Paper, Water, and WaterMineral schemas with computed
fields (``is_retired``, ``rings``, ``grind_range``, ``tier``).
"""

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import model_validator
from sqlmodel import SQLModel

from beanbay.models.equipment import (
    DialType,
    FlowControlType,
    PreinfusionType,
    PressureControlType,
    TempControlType,
)
from beanbay.schemas.tag import BrewMethodRead, StopModeRead
from beanbay.utils.brewer_capabilities import derive_tier
from beanbay.utils.grinder_display import linear_bounds


# ---------------------------------------------------------------------------
# Grinder
# ---------------------------------------------------------------------------


class RingConfig(SQLModel):
    """Configuration for a single grinder ring.

    Attributes
    ----------
    label : str
        Human-readable ring label.
    min : float
        Minimum dial position.
    max : float
        Maximum dial position.
    step : float
        Step size between positions.
    """

    label: str
    min: float
    max: float
    step: float


class GrindRange(SQLModel):
    """Linearised grind range computed from ring configuration.

    Attributes
    ----------
    min : float
        Minimum linear grind value.
    max : float
        Maximum linear grind value.
    step : float
        Step size (always 1.0 for multi-ring, otherwise ring step).
    """

    min: float
    max: float
    step: float


class GrinderBase(SQLModel):
    """Shared fields for Grinder schemas.

    Attributes
    ----------
    name : str
        Grinder name.
    dial_type : DialType
        Stepless or stepped.
    """

    name: str
    dial_type: DialType = DialType.STEPLESS


class GrinderCreate(SQLModel):
    """Schema for creating a Grinder.

    Attributes
    ----------
    name : str
        Grinder name.
    dial_type : DialType
        Stepless or stepped.
    rings : list[RingConfig] | None
        Optional ring configuration.
    """

    name: str
    dial_type: DialType = DialType.STEPLESS
    rings: list[RingConfig] | None = None


class GrinderUpdate(SQLModel):
    """Schema for partially updating a Grinder.

    Attributes
    ----------
    name : str | None
        Updated name.
    dial_type : DialType | None
        Updated dial type.
    rings : list[RingConfig] | None
        Updated ring configuration.
    retired_at : datetime | None
        Set to null to un-retire.
    """

    name: str | None = None
    dial_type: DialType | None = None
    rings: list[RingConfig] | None = None
    retired_at: datetime | None = None


class GrinderRead(GrinderBase):
    """Schema returned when reading a Grinder.

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
    rings : list[RingConfig]
        Structured ring configuration parsed from ``ring_sizes_json``.
    grind_range : GrindRange | None
        Linearised bounds computed from rings.
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool
    rings: list[RingConfig]
    grind_range: GrindRange | None

    @model_validator(mode="before")
    @classmethod
    def compute_grinder_fields(cls, data: dict | object) -> dict:
        """Parse ``ring_sizes_json`` into ``rings`` and ``grind_range``.

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
                "dial_type",
                "ring_sizes_json",
                "created_at",
                "updated_at",
                "retired_at",
            ):
                d[field] = getattr(data, field, None)
            data = d

        data["is_retired"] = data.get("retired_at") is not None

        # Parse ring_sizes_json -> rings
        raw_json = data.get("ring_sizes_json")
        rings: list[dict[str, Any]] = []
        ring_tuples: list[tuple[float, float, float | None]] = []
        if raw_json:
            parsed = json.loads(raw_json)
            for i, ring in enumerate(parsed):
                r_min, r_max, r_step = float(ring[0]), float(ring[1]), float(ring[2])
                rings.append(
                    {
                        "label": f"Ring {i + 1}",
                        "min": r_min,
                        "max": r_max,
                        "step": r_step,
                    }
                )
                ring_tuples.append((r_min, r_max, r_step))

        data["rings"] = rings

        # Compute grind_range from rings
        if ring_tuples:
            bounds = linear_bounds(ring_tuples)
            if bounds is not None:
                # Step: for single ring use the ring step, for multi-ring use 1.0
                if len(ring_tuples) == 1:
                    step = ring_tuples[0][2] if ring_tuples[0][2] is not None else 1.0
                else:
                    step = 1.0
                data["grind_range"] = {
                    "min": bounds[0],
                    "max": bounds[1],
                    "step": step,
                }
            else:
                data["grind_range"] = None
        else:
            data["grind_range"] = None

        # Remove ring_sizes_json from output dict
        data.pop("ring_sizes_json", None)

        return data


# ---------------------------------------------------------------------------
# Brewer
# ---------------------------------------------------------------------------


class BrewerBase(SQLModel):
    """Shared fields for Brewer schemas.

    Attributes
    ----------
    name : str
        Brewer name.
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
    """

    name: str
    temp_control_type: TempControlType = TempControlType.PID
    temp_min: float | None = None
    temp_max: float | None = None
    temp_step: float | None = None
    preinfusion_type: PreinfusionType = PreinfusionType.NONE
    preinfusion_max_time: float | None = None
    pressure_control_type: PressureControlType = PressureControlType.FIXED
    pressure_min: float | None = None
    pressure_max: float | None = None
    flow_control_type: FlowControlType = FlowControlType.NONE
    saturation_flow_rate: float | None = None
    has_bloom: bool = False


class BrewerCreate(BrewerBase):
    """Schema for creating a Brewer.

    Attributes
    ----------
    method_ids : list[uuid.UUID] | None
        IDs of brew methods to link.
    stop_mode_ids : list[uuid.UUID] | None
        IDs of stop modes to link.
    """

    method_ids: list[uuid.UUID] | None = None
    stop_mode_ids: list[uuid.UUID] | None = None


class BrewerUpdate(SQLModel):
    """Schema for partially updating a Brewer.

    Attributes
    ----------
    name : str | None
        Updated name.
    temp_control_type : TempControlType | None
        Updated temperature control.
    temp_min : float | None
        Updated minimum temperature.
    temp_max : float | None
        Updated maximum temperature.
    temp_step : float | None
        Updated temperature step.
    preinfusion_type : PreinfusionType | None
        Updated pre-infusion type.
    preinfusion_max_time : float | None
        Updated max pre-infusion time.
    pressure_control_type : PressureControlType | None
        Updated pressure control.
    pressure_min : float | None
        Updated minimum pressure.
    pressure_max : float | None
        Updated maximum pressure.
    flow_control_type : FlowControlType | None
        Updated flow control.
    saturation_flow_rate : float | None
        Updated saturation flow rate.
    has_bloom : bool | None
        Updated bloom support.
    method_ids : list[uuid.UUID] | None
        Updated list of brew method IDs.
    stop_mode_ids : list[uuid.UUID] | None
        Updated list of stop mode IDs.
    """

    name: str | None = None
    temp_control_type: TempControlType | None = None
    temp_min: float | None = None
    temp_max: float | None = None
    temp_step: float | None = None
    preinfusion_type: PreinfusionType | None = None
    preinfusion_max_time: float | None = None
    pressure_control_type: PressureControlType | None = None
    pressure_min: float | None = None
    pressure_max: float | None = None
    flow_control_type: FlowControlType | None = None
    saturation_flow_rate: float | None = None
    has_bloom: bool | None = None
    method_ids: list[uuid.UUID] | None = None
    stop_mode_ids: list[uuid.UUID] | None = None
    retired_at: datetime | None = None


class BrewerRead(BrewerBase):
    """Schema returned when reading a Brewer.

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
    tier : int
        Computed UX tier (1--5).
    methods : list[BrewMethodRead]
        Nested brew methods.
    stop_modes : list[StopModeRead]
        Nested stop modes.
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool
    tier: int
    methods: list[BrewMethodRead]
    stop_modes: list[StopModeRead]

    @model_validator(mode="before")
    @classmethod
    def compute_brewer_fields(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` and ``tier`` from brewer data.

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
                "temp_control_type",
                "temp_min",
                "temp_max",
                "temp_step",
                "preinfusion_type",
                "preinfusion_max_time",
                "pressure_control_type",
                "pressure_min",
                "pressure_max",
                "flow_control_type",
                "saturation_flow_rate",
                "has_bloom",
                "methods",
                "stop_modes",
                "created_at",
                "updated_at",
                "retired_at",
            ):
                d[field] = getattr(data, field, None)
            data = d

        data["is_retired"] = data.get("retired_at") is not None

        # Compute tier using a simple namespace object
        from types import SimpleNamespace

        proxy = SimpleNamespace(
            flow_control_type=data.get("flow_control_type", "none"),
            pressure_control_type=data.get("pressure_control_type", "fixed"),
            preinfusion_type=data.get("preinfusion_type", "none"),
            temp_control_type=data.get("temp_control_type", "pid"),
        )
        data["tier"] = derive_tier(proxy)  # type: ignore[arg-type]

        # Ensure methods and stop_modes default to empty list
        if data.get("methods") is None:
            data["methods"] = []
        if data.get("stop_modes") is None:
            data["stop_modes"] = []

        return data


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------


class PaperBase(SQLModel):
    """Shared fields for Paper schemas.

    Attributes
    ----------
    name : str
        Paper name.
    notes : str | None
        Optional notes.
    """

    name: str
    notes: str | None = None


class PaperCreate(PaperBase):
    """Schema for creating a Paper."""

    pass


class PaperUpdate(SQLModel):
    """Schema for partially updating a Paper.

    Attributes
    ----------
    name : str | None
        Updated name.
    notes : str | None
        Updated notes.
    retired_at : datetime | None
        Set to null to un-retire.
    """

    name: str | None = None
    notes: str | None = None
    retired_at: datetime | None = None


class PaperRead(PaperBase):
    """Schema returned when reading a Paper.

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
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool

    @model_validator(mode="before")
    @classmethod
    def compute_is_retired(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` from ``retired_at``.

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
        if not isinstance(data, dict):
            d: dict[str, Any] = {}
            for field in ("id", "name", "notes", "created_at", "updated_at", "retired_at"):
                d[field] = getattr(data, field, None)
            data = d
        data["is_retired"] = data.get("retired_at") is not None
        return data


# ---------------------------------------------------------------------------
# Water + WaterMineral
# ---------------------------------------------------------------------------


class WaterMineralBase(SQLModel):
    """Shared fields for WaterMineral schemas.

    Attributes
    ----------
    mineral_name : str
        Name of the mineral.
    ppm : float
        Concentration in parts per million.
    """

    mineral_name: str
    ppm: float


class WaterMineralCreate(WaterMineralBase):
    """Schema for creating a WaterMineral inline with a Water."""

    pass


class WaterMineralRead(WaterMineralBase):
    """Schema returned when reading a WaterMineral.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    mineral_name : str
        Name of the mineral.
    ppm : float
        Concentration in parts per million.
    """

    id: uuid.UUID


class WaterBase(SQLModel):
    """Shared fields for Water schemas.

    Attributes
    ----------
    name : str
        Water name.
    notes : str | None
        Optional notes.
    """

    name: str
    notes: str | None = None


class WaterCreate(WaterBase):
    """Schema for creating a Water with optional inline minerals.

    Attributes
    ----------
    minerals : list[WaterMineralCreate] | None
        Inline mineral composition.
    """

    minerals: list[WaterMineralCreate] | None = None


class WaterUpdate(SQLModel):
    """Schema for partially updating a Water.

    Attributes
    ----------
    name : str | None
        Updated name.
    notes : str | None
        Updated notes.
    minerals : list[WaterMineralCreate] | None
        Updated mineral composition. When present, replaces all minerals.
    retired_at : datetime | None
        Set to null to un-retire.
    """

    name: str | None = None
    notes: str | None = None
    minerals: list[WaterMineralCreate] | None = None
    retired_at: datetime | None = None


class WaterRead(WaterBase):
    """Schema returned when reading a Water.

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
    minerals : list[WaterMineralRead]
        Nested mineral composition.
    """

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    is_retired: bool
    minerals: list[WaterMineralRead]

    @model_validator(mode="before")
    @classmethod
    def compute_water_fields(cls, data: dict | object) -> dict:
        """Compute ``is_retired`` and ensure minerals default.

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
                "notes",
                "minerals",
                "created_at",
                "updated_at",
                "retired_at",
            ):
                d[field] = getattr(data, field, None)
            data = d

        data["is_retired"] = data.get("retired_at") is not None
        if data.get("minerals") is None:
            data["minerals"] = []

        return data

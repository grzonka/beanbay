"""Seed optimization parameter defaults for all brew methods.

Idempotent seeding of ``MethodParameterDefault`` rows that define
the default search-space bounds for each brew method.
"""

from sqlmodel import Session, select

from beanbay.models.optimization import MethodParameterDefault
from beanbay.models.tag import BrewMethod

# ---------------------------------------------------------------------------
# Per-method parameter definitions
# ---------------------------------------------------------------------------
# Each entry is a dict with keys matching MethodParameterDefault fields
# (excluding id, brew_method_id, created_at, updated_at).
# grind_setting is intentionally excluded for every method.

_ESPRESSO_PARAMS: list[dict] = [
    {"parameter_name": "temperature", "min_value": 85.0, "max_value": 105.0, "step": 0.5},
    {"parameter_name": "dose", "min_value": 15.0, "max_value": 25.0, "step": 0.1},
    {"parameter_name": "yield_amount", "min_value": 25.0, "max_value": 50.0, "step": 0.5},
    {
        "parameter_name": "pre_infusion_time",
        "min_value": 0.0,
        "max_value": 15.0,
        "step": 0.5,
        "requires": "preinfusion_type != none",
    },
    {
        "parameter_name": "preinfusion_pressure",
        "min_value": 1.0,
        "max_value": 6.0,
        "step": 0.5,
        "requires": "preinfusion_type in (adjustable_pressure, programmable, manual)",
    },
    {
        "parameter_name": "pressure",
        "min_value": 6.0,
        "max_value": 12.0,
        "step": 0.5,
        "requires": "pressure_control_type in (opv_adjustable, electronic, programmable)",
    },
    {
        "parameter_name": "flow_rate",
        "min_value": 0.5,
        "max_value": 4.0,
        "step": 0.1,
        "requires": "flow_control_type != none",
    },
    {
        "parameter_name": "saturation",
        "min_value": 0.0,
        "max_value": 1.0,
        "step": 0.1,
        "requires": "flow_control_type != none",
    },
    {
        "parameter_name": "bloom_pause",
        "min_value": 0.0,
        "max_value": 10.0,
        "step": 0.5,
        "requires": "has_bloom == true",
    },
    {
        "parameter_name": "pressure_profile",
        "requires": "pressure_control_type in (manual_profiling, programmable)",
        "allowed_values": "ramp_up,flat,decline,custom",
    },
    {
        "parameter_name": "brew_mode",
        "requires": "flow_control_type == programmable",
        "allowed_values": "auto,manual",
    },
    {
        "parameter_name": "temp_profile",
        "requires": "temp_control_type == profiling",
        "allowed_values": "flat,declining,profiling",
    },
]

_POUR_OVER_PARAMS: list[dict] = [
    {"parameter_name": "temperature", "min_value": 85.0, "max_value": 100.0, "step": 0.5},
    {"parameter_name": "dose", "min_value": 12.0, "max_value": 30.0, "step": 0.5},
    {"parameter_name": "yield_amount", "min_value": 200.0, "max_value": 500.0, "step": 10.0},
    {"parameter_name": "bloom_weight", "min_value": 20.0, "max_value": 90.0, "step": 5.0},
]

_FRENCH_PRESS_PARAMS: list[dict] = [
    {"parameter_name": "temperature", "min_value": 85.0, "max_value": 100.0, "step": 0.5},
    {"parameter_name": "dose", "min_value": 12.0, "max_value": 30.0, "step": 0.5},
    {"parameter_name": "yield_amount", "min_value": 200.0, "max_value": 500.0, "step": 10.0},
    {"parameter_name": "total_time", "min_value": 180.0, "max_value": 480.0, "step": 15.0},
]

_AEROPRESS_PARAMS: list[dict] = [
    {"parameter_name": "temperature", "min_value": 75.0, "max_value": 100.0, "step": 0.5},
    {"parameter_name": "dose", "min_value": 10.0, "max_value": 25.0, "step": 0.5},
    {"parameter_name": "yield_amount", "min_value": 150.0, "max_value": 300.0, "step": 10.0},
    {"parameter_name": "total_time", "min_value": 60.0, "max_value": 300.0, "step": 10.0},
    {"parameter_name": "brew_mode", "allowed_values": "standard,inverted"},
]

_TURKISH_PARAMS: list[dict] = [
    {"parameter_name": "temperature", "min_value": 85.0, "max_value": 100.0, "step": 0.5},
    {"parameter_name": "dose", "min_value": 5.0, "max_value": 15.0, "step": 0.5},
    {"parameter_name": "yield_amount", "min_value": 50.0, "max_value": 150.0, "step": 10.0},
]

_MOKA_POT_PARAMS: list[dict] = [
    {"parameter_name": "temperature", "min_value": 85.0, "max_value": 100.0, "step": 0.5},
    {"parameter_name": "dose", "min_value": 10.0, "max_value": 25.0, "step": 0.5},
    {"parameter_name": "yield_amount", "min_value": 30.0, "max_value": 120.0, "step": 10.0},
]

_COLD_BREW_PARAMS: list[dict] = [
    {"parameter_name": "dose", "min_value": 30.0, "max_value": 120.0, "step": 5.0},
    {"parameter_name": "yield_amount", "min_value": 400.0, "max_value": 1200.0, "step": 50.0},
    {"parameter_name": "total_time", "min_value": 720.0, "max_value": 1440.0, "step": 60.0},
]

# Map brew method name -> parameter list
_METHOD_DEFAULTS: dict[str, list[dict]] = {
    "espresso": _ESPRESSO_PARAMS,
    "pour-over": _POUR_OVER_PARAMS,
    "french-press": _FRENCH_PRESS_PARAMS,
    "aeropress": _AEROPRESS_PARAMS,
    "turkish": _TURKISH_PARAMS,
    "moka-pot": _MOKA_POT_PARAMS,
    "cold-brew": _COLD_BREW_PARAMS,
}


def seed_method_parameter_defaults(session: Session) -> None:
    """Insert default parameter search-space bounds for all brew methods.

    This function is idempotent: if rows already exist for a given brew
    method, they are not re-inserted. If a brew method does not yet exist
    in the database, it is silently skipped.

    Parameters
    ----------
    session : Session
        An active SQLModel session. The caller is responsible for
        calling ``session.commit()`` after this function returns.
    """
    for method_name, params in _METHOD_DEFAULTS.items():
        brew_method = session.exec(
            select(BrewMethod).where(BrewMethod.name == method_name)
        ).first()

        if brew_method is None:
            continue

        # Check if any defaults already exist for this method
        existing = session.exec(
            select(MethodParameterDefault).where(
                MethodParameterDefault.brew_method_id == brew_method.id
            )
        ).first()

        if existing is not None:
            continue

        for param in params:
            session.add(
                MethodParameterDefault(
                    brew_method_id=brew_method.id,
                    **param,
                )
            )

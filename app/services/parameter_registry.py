"""Parameter Registry — the single source of truth for all brew method parameter definitions.

This module provides:
  - PARAMETER_REGISTRY: dict mapping brew method → list of parameter definition dicts
  - METHOD_GRIND_PERCENTAGES: grind range as fraction of grinder's full range, per method
  - requires_check(condition_str, brewer): evaluates capability-gate condition strings
  - build_parameters_for_setup(method, brewer, overrides): builds BayBE parameter objects
  - get_param_columns(method, brewer): returns list of parameter name strings
  - get_default_bounds(method): returns dict of param_name → (min, max)
  - get_rounding_rules(method): returns dict of param_name → rounding step
  - suggest_grind_range(grinder, method): returns (min, max) grind setting for method

Each parameter definition dict has the following keys:
  - name (str): parameter name
  - type (str): "continuous" | "categorical"
  - bounds (tuple[float,float]): for continuous params — (min, max)
  - values (list[str]): for categorical params
  - encoding (str): for categorical params — e.g. "OHE"
  - rounding (float | None): for continuous params — rounding step (None = not in rounding rules)
  - requires (str | None): capability condition string, or None if always included
"""

from __future__ import annotations

from typing import Any

from baybe.parameters import CategoricalParameter, NumericalContinuousParameter

# ---------------------------------------------------------------------------
# Grind range percentages per brew method
# Expressed as (low_pct, high_pct) of the grinder's full range (min_value..max_value)
# ---------------------------------------------------------------------------
METHOD_GRIND_PERCENTAGES: dict[str, tuple[float, float]] = {
    "espresso": (0.15, 0.40),
    "pour-over": (0.40, 0.70),
    "french-press": (0.55, 0.85),
    "aeropress": (0.25, 0.60),
    "turkish": (0.05, 0.20),
    "moka-pot": (0.25, 0.45),
    "cold-brew": (0.55, 0.85),
}

# ---------------------------------------------------------------------------
# PARAMETER_REGISTRY
#
# Each entry is a dict with:
#   name       str
#   type       "continuous" | "categorical"
#   bounds     (min, max)            — continuous only
#   values     list[str]             — categorical only
#   encoding   str                   — categorical only
#   rounding   float | None          — continuous only (None = not rounded)
#   requires   str | None            — capability gate, None = always include
# ---------------------------------------------------------------------------
PARAMETER_REGISTRY: dict[str, list[dict[str, Any]]] = {
    # ------------------------------------------------------------------
    # Espresso — backward-compatible with optimizer.py constants
    # Core params (no requires):
    #   grind_setting, temperature, preinfusion_pct, dose_in, target_yield, saturation
    # Advanced params (requires brewer capability):
    #   preinfusion_time, brew_pressure, pressure_profile
    # ------------------------------------------------------------------
    "espresso": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (15.0, 25.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "temperature",
            "type": "continuous",
            "bounds": (86.0, 96.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "preinfusion_pct",
            "type": "continuous",
            "bounds": (55.0, 100.0),
            "rounding": 5.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (18.5, 20.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "target_yield",
            "type": "continuous",
            "bounds": (36.0, 50.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "saturation",
            "type": "categorical",
            "values": ["yes", "no"],
            "encoding": "OHE",
            "rounding": None,
            "requires": None,
        },
        # Advanced — gated on preinfusion capability
        {
            "name": "preinfusion_time",
            "type": "continuous",
            "bounds": (0.0, 15.0),
            "rounding": 1.0,
            "requires": "brewer.preinfusion_type in (timed, adjustable_pressure, programmable)",
        },
        # Advanced — gated on pressure control
        {
            "name": "brew_pressure",
            "type": "continuous",
            "bounds": (6.0, 9.5),
            "rounding": 0.5,
            "requires": "brewer.pressure_control_type in (opv_adjustable, electronic, programmable)",
        },
        # Advanced — gated on profiling capability
        {
            "name": "pressure_profile",
            "type": "categorical",
            "values": ["flat", "ramp_up", "ramp_down", "pre_infusion_ramp"],
            "encoding": "OHE",
            "rounding": None,
            "requires": "brewer.pressure_control_type in (manual_profiling, programmable)",
        },
    ],
    # ------------------------------------------------------------------
    # Pour-over — backward-compatible with optimizer.py constants
    # ------------------------------------------------------------------
    "pour-over": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (15.0, 40.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "temperature",
            "type": "continuous",
            "bounds": (88.0, 98.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "bloom_weight",
            "type": "continuous",
            "bounds": (20.0, 80.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (12.0, 22.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "brew_volume",
            "type": "continuous",
            "bounds": (150.0, 500.0),
            "rounding": 5.0,
            "requires": None,
        },
    ],
    # ------------------------------------------------------------------
    # French press
    # ------------------------------------------------------------------
    "french-press": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (30.0, 50.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "temperature",
            "type": "continuous",
            "bounds": (90.0, 99.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "steep_time",
            "type": "continuous",
            "bounds": (180.0, 480.0),
            "rounding": 15.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (15.0, 30.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "brew_volume",
            "type": "continuous",
            "bounds": (200.0, 600.0),
            "rounding": 10.0,
            "requires": None,
        },
    ],
    # ------------------------------------------------------------------
    # AeroPress
    # ------------------------------------------------------------------
    "aeropress": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (10.0, 30.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "temperature",
            "type": "continuous",
            "bounds": (75.0, 96.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "steep_time",
            "type": "continuous",
            "bounds": (30.0, 240.0),
            "rounding": 10.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (10.0, 20.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "brew_volume",
            "type": "continuous",
            "bounds": (100.0, 250.0),
            "rounding": 5.0,
            "requires": None,
        },
        {
            "name": "brew_mode",
            "type": "categorical",
            "values": ["standard", "inverted"],
            "encoding": "OHE",
            "rounding": None,
            "requires": None,
        },
    ],
    # ------------------------------------------------------------------
    # Turkish coffee
    # ------------------------------------------------------------------
    "turkish": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (1.0, 8.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "temperature",
            "type": "continuous",
            "bounds": (60.0, 95.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (6.0, 12.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "brew_volume",
            "type": "continuous",
            "bounds": (50.0, 100.0),
            "rounding": 5.0,
            "requires": None,
        },
    ],
    # ------------------------------------------------------------------
    # Moka pot
    # ------------------------------------------------------------------
    "moka-pot": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (10.0, 20.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "temperature",
            "type": "continuous",
            "bounds": (80.0, 95.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (12.0, 22.0),
            "rounding": 0.5,
            "requires": None,
        },
        {
            "name": "brew_volume",
            "type": "continuous",
            "bounds": (50.0, 150.0),
            "rounding": 5.0,
            "requires": None,
        },
    ],
    # ------------------------------------------------------------------
    # Cold brew
    # ------------------------------------------------------------------
    "cold-brew": [
        {
            "name": "grind_setting",
            "type": "continuous",
            "bounds": (35.0, 55.0),
            "rounding": 1.0,
            "requires": None,
        },
        {
            "name": "steep_time",
            "type": "continuous",
            "bounds": (720.0, 1440.0),  # 12–24 hours in minutes
            "rounding": 60.0,
            "requires": None,
        },
        {
            "name": "dose_in",
            "type": "continuous",
            "bounds": (60.0, 120.0),
            "rounding": 5.0,
            "requires": None,
        },
        {
            "name": "brew_volume",
            "type": "continuous",
            "bounds": (500.0, 1500.0),
            "rounding": 50.0,
            "requires": None,
        },
    ],
}


# ---------------------------------------------------------------------------
# Helper: capability-gate evaluation
# ---------------------------------------------------------------------------


def requires_check(condition_str: str | None, brewer: Any) -> bool:
    """Evaluate a capability-gate condition string against a brewer instance.

    Condition format:  ``brewer.{attr} in ({val1}, {val2}, ...)``

    Rules:
    - If condition_str is None → return True (always include)
    - If brewer is None → return True (backward-compat: include all when no brewer)
    - Otherwise parse and evaluate the condition

    Args:
        condition_str: Condition string or None.
        brewer: Brewer ORM instance (or any object with the relevant attribute), or None.

    Returns:
        True if the parameter should be included, False otherwise.
    """
    if condition_str is None:
        return True
    if brewer is None:
        return True

    # Parse: "brewer.{attr} in ({val1}, {val2}, ...)"
    try:
        # Strip whitespace
        cond = condition_str.strip()
        # Must start with "brewer."
        if not cond.startswith("brewer."):
            return True  # Unknown format — include to be safe

        # Split on " in "
        parts = cond.split(" in ", 1)
        if len(parts) != 2:
            return True

        attr_part = parts[0].strip()  # e.g. "brewer.preinfusion_type"
        values_part = parts[1].strip()  # e.g. "(timed, adjustable_pressure, programmable)"

        # Extract attribute name
        attr_name = attr_part[len("brewer.") :]  # e.g. "preinfusion_type"

        # Extract values list — strip outer parens, split on comma
        values_str = values_part.strip("() ")
        allowed_values = {v.strip() for v in values_str.split(",")}

        # Read attribute from brewer
        brewer_value = getattr(brewer, attr_name, None)
        if brewer_value is None:
            return False

        return str(brewer_value) in allowed_values

    except Exception:
        # Any parse error — include parameter to be safe
        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_parameters_for_setup(
    method: str,
    brewer: Any = None,
    overrides: dict[str, dict[str, float]] | None = None,
) -> list:
    """Build BayBE parameter objects for the given method and brewer.

    Args:
        method: Brew method (e.g. "espresso", "pour-over").
        brewer: Brewer ORM instance for capability gating, or None for backward compat.
        overrides: Per-param bound overrides, e.g. {"grind_setting": {"min": 18.0, "max": 22.0}}.

    Returns:
        List of BayBE parameter objects (NumericalContinuousParameter or CategoricalParameter).
    """
    param_defs = PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])

    parameters = []
    for pdef in param_defs:
        if not requires_check(pdef.get("requires"), brewer):
            continue

        name = pdef["name"]
        ptype = pdef["type"]

        if ptype == "categorical":
            parameters.append(
                CategoricalParameter(
                    name=name,
                    values=pdef["values"],
                    encoding=pdef.get("encoding", "OHE"),
                )
            )
        else:
            # Continuous
            lo, hi = pdef["bounds"]
            if overrides and name in overrides:
                spec = overrides[name]
                if isinstance(spec, dict):
                    lo = spec.get("min", lo)
                    hi = spec.get("max", hi)
            parameters.append(NumericalContinuousParameter(name=name, bounds=(lo, hi)))

    return parameters


def get_param_columns(method: str, brewer: Any = None) -> list[str]:
    """Return parameter column names for the given method and brewer.

    Args:
        method: Brew method name.
        brewer: Brewer instance for capability gating, or None for backward compat.

    Returns:
        Ordered list of parameter name strings.
    """
    param_defs = PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])
    return [pdef["name"] for pdef in param_defs if requires_check(pdef.get("requires"), brewer)]


def get_default_bounds(method: str) -> dict[str, tuple[float, float]]:
    """Return default parameter bounds for continuous params of the given method.

    Args:
        method: Brew method name.

    Returns:
        Dict of param_name → (min, max).  Categorical params are excluded.
    """
    param_defs = PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])
    return {pdef["name"]: pdef["bounds"] for pdef in param_defs if pdef["type"] == "continuous"}


def get_rounding_rules(method: str) -> dict[str, float]:
    """Return rounding rules for continuous params of the given method.

    Args:
        method: Brew method name.

    Returns:
        Dict of param_name → rounding step.  Params with rounding=None are excluded.
    """
    param_defs = PARAMETER_REGISTRY.get(method, PARAMETER_REGISTRY["espresso"])
    return {
        pdef["name"]: pdef["rounding"]
        for pdef in param_defs
        if pdef["type"] == "continuous" and pdef.get("rounding") is not None
    }


def suggest_grind_range(grinder: Any, method: str) -> tuple[float, float] | None:
    """Suggest a grind setting range for the given grinder and brew method.

    Uses METHOD_GRIND_PERCENTAGES to compute the range as a fraction of the
    grinder's full range (grinder.min_value .. grinder.max_value).

    Args:
        grinder: Grinder ORM instance with min_value and max_value attributes.
        method: Brew method name.

    Returns:
        (min_grind, max_grind) tuple, or None if grinder has no range configured.
    """
    if grinder is None:
        return None

    lo_val = getattr(grinder, "min_value", None)
    hi_val = getattr(grinder, "max_value", None)

    if lo_val is None or hi_val is None:
        return None

    grind_range = hi_val - lo_val
    if grind_range <= 0:
        return None

    pcts = METHOD_GRIND_PERCENTAGES.get(method)
    if pcts is None:
        return None

    lo_pct, hi_pct = pcts
    return (
        round(lo_val + lo_pct * grind_range, 2),
        round(lo_val + hi_pct * grind_range, 2),
    )

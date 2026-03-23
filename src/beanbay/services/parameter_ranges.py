"""Parameter range computation service.

Provides the 3-layer effective range system and capability gate evaluation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


def evaluate_requires(condition: str | None, brewer: Any) -> bool:
    """Evaluate a capability gate condition against a brewer.

    Supported formats:
    - ``"attr != value"``
    - ``"attr == value"`` (including ``"true"``/``"false"`` for booleans)
    - ``"attr in (val1, val2, ...)"``

    Parameters
    ----------
    condition : str | None
        Condition string, or None (always passes).
    brewer : Any
        Object with brewer capability attributes.

    Returns
    -------
    bool
        Whether the condition is satisfied.
    """
    if condition is None:
        return True

    condition = condition.strip()

    # "attr in (val1, val2, ...)"
    m = re.match(r"(\w+)\s+in\s+\(([^)]+)\)", condition)
    if m:
        attr, values_str = m.group(1), m.group(2)
        values = [v.strip() for v in values_str.split(",")]
        return str(getattr(brewer, attr, None)) in values

    # "attr != value"
    m = re.match(r"(\w+)\s*!=\s*(\w+)", condition)
    if m:
        attr, value = m.group(1), m.group(2)
        return str(getattr(brewer, attr, None)) != value

    # "attr == value"
    m = re.match(r"(\w+)\s*==\s*(\w+)", condition)
    if m:
        attr, value = m.group(1), m.group(2)
        actual = getattr(brewer, attr, None)
        if value.lower() == "true":
            return bool(actual) is True
        if value.lower() == "false":
            return bool(actual) is False
        return str(actual) == value

    return False


# ---------------------------------------------------------------------------
# Effective range computation
# ---------------------------------------------------------------------------

# Mapping from parameter names to brewer attribute pairs for narrowing.
_BREWER_PARAM_MAP: dict[str, dict[str, str]] = {
    "temperature": {"min_attr": "temp_min", "max_attr": "temp_max"},
    "pressure": {"min_attr": "pressure_min", "max_attr": "pressure_max"},
    "pre_infusion_time": {"max_attr": "preinfusion_max_time"},
}


@dataclass
class EffectiveRange:
    """A computed parameter range after all layers are applied.

    Attributes
    ----------
    parameter_name : str
        Name of the parameter.
    min_value : float | None
        Effective minimum value, or None for categorical parameters.
    max_value : float | None
        Effective maximum value, or None for categorical parameters.
    step : float | None
        Step size, or None if continuous.
    allowed_values : str | None
        JSON string of allowed categorical values, or None for numeric.
    source : str
        Describes which layer was most restrictive
        (``"method_default"``, ``"equipment"``, ``"grinder"``,
        or ``"bean_override"``).
    """

    parameter_name: str
    min_value: float | None
    max_value: float | None
    step: float | None
    allowed_values: str | None
    source: str


def compute_effective_ranges(
    method_defaults: list,
    brewer: Any | None,
    grinder: Any | None,
    bean_overrides: list,
) -> list[EffectiveRange]:
    """Compute effective parameter ranges using the 3-layer system.

    Layer 1: method defaults provide the base range.
    Layer 2: brewer equipment constraints narrow the range.
    Layer 3: bean-specific overrides narrow the range further.

    Parameters
    ----------
    method_defaults : list
        MethodParameterDefault rows for the brew method.
    brewer : Any | None
        Brewer with capability attributes, or None.
    grinder : Any | None
        Grinder with ``ring_sizes_json``, or None.
    bean_overrides : list
        BeanParameterOverride rows for the bean.

    Returns
    -------
    list[EffectiveRange]
        Effective ranges after layering.

    Raises
    ------
    ValueError
        If any parameter's effective range is invalid (min >= max).
    """
    results: list[EffectiveRange] = []
    override_map: dict[str, Any] = {o.parameter_name: o for o in bean_overrides}

    for default in method_defaults:
        # --- Capability gate ---
        if default.requires is not None:
            if brewer is None or not evaluate_requires(default.requires, brewer):
                continue

        # --- Categorical parameters: pass through ---
        if default.allowed_values is not None:
            results.append(
                EffectiveRange(
                    parameter_name=default.parameter_name,
                    min_value=None,
                    max_value=None,
                    step=None,
                    allowed_values=default.allowed_values,
                    source="method_default",
                )
            )
            continue

        # --- Numeric parameters: start from method defaults ---
        eff_min = default.min_value
        eff_max = default.max_value
        source = "method_default"

        # --- Layer 2: brewer narrowing ---
        if brewer is not None and default.parameter_name in _BREWER_PARAM_MAP:
            mapping = _BREWER_PARAM_MAP[default.parameter_name]

            if "min_attr" in mapping:
                brewer_min = getattr(brewer, mapping["min_attr"], None)
                if brewer_min is not None and (eff_min is None or brewer_min > eff_min):
                    eff_min = brewer_min
                    source = "equipment"

            if "max_attr" in mapping:
                brewer_max = getattr(brewer, mapping["max_attr"], None)
                if brewer_max is not None and (eff_max is None or brewer_max < eff_max):
                    eff_max = brewer_max
                    source = "equipment"

        # --- Layer 3: bean overrides ---
        override = override_map.get(default.parameter_name)
        if override is not None:
            if override.min_value is not None and (eff_min is None or override.min_value > eff_min):
                eff_min = override.min_value
                source = "bean_override"
            if override.max_value is not None and (eff_max is None or override.max_value < eff_max):
                eff_max = override.max_value
                source = "bean_override"

        # --- Validate ---
        if eff_min is not None and eff_max is not None and eff_min >= eff_max:
            msg = (
                f"Invalid effective range for '{default.parameter_name}': "
                f"min={eff_min} >= max={eff_max}"
            )
            raise ValueError(msg)

        results.append(
            EffectiveRange(
                parameter_name=default.parameter_name,
                min_value=eff_min,
                max_value=eff_max,
                step=default.step,
                allowed_values=None,
                source=source,
            )
        )

    # --- Grind setting from grinder ---
    if grinder is not None and grinder.ring_sizes_json is not None:
        rings = json.loads(grinder.ring_sizes_json)
        if rings:
            # Compute linear bounds
            if len(rings) == 1:
                linear_min = float(rings[0][0])
                linear_max = float(rings[0][1])
            else:
                total = 1
                for ring in rings:
                    ring_min, ring_max, ring_step = ring
                    total *= int((ring_max - ring_min) / ring_step) + 1
                linear_min = 0.0
                linear_max = float(total - 1)

            source = "grinder"

            # Apply bean override for grind_setting
            override = override_map.get("grind_setting")
            if override is not None:
                if override.min_value is not None and override.min_value > linear_min:
                    linear_min = override.min_value
                    source = "bean_override"
                if override.max_value is not None and override.max_value < linear_max:
                    linear_max = override.max_value
                    source = "bean_override"

            # Validate
            if linear_min >= linear_max:
                msg = (
                    f"Invalid effective range for 'grind_setting': "
                    f"min={linear_min} >= max={linear_max}"
                )
                raise ValueError(msg)

            results.append(
                EffectiveRange(
                    parameter_name="grind_setting",
                    min_value=linear_min,
                    max_value=linear_max,
                    step=1.0,
                    allowed_values=None,
                    source=source,
                )
            )

    return results

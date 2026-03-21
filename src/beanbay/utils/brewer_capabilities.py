"""Brewer capability utilities.

Provides ``derive_tier()`` to compute a UX tier (1--5) from a brewer's
capability flags, and ``TIER_LABELS`` for human-readable display.

Tier progression (from most basic to most capable):

  Tier 1 -- Basic:             grind, dose, yield only (no controllable temp/pressure/flow)
  Tier 2 -- Temperature:       + temperature setting (PID or profiling)
  Tier 3 -- Pre-infusion:      + timed / adjustable pre-infusion
  Tier 4 -- Pressure & Flow:   + manual pressure profiling or paddle/valve flow control
  Tier 5 -- Full Programmable: + fully programmable flow control (Decent DE1, Meticulous)

Adapted from the main branch (original author: grzonka).
"""

from __future__ import annotations

from enum import IntEnum
from typing import Protocol


class BrewerTier(IntEnum):
    """UX tier for brewer capability classification."""

    BASIC = 1
    TEMPERATURE = 2
    PRE_INFUSION = 3
    PRESSURE_FLOW = 4
    FULL_PROGRAMMABLE = 5

    @property
    def label(self) -> str:
        """Return the human-readable label for this tier."""
        return _TIER_LABELS[self]


_TIER_LABELS: dict[BrewerTier, str] = {
    BrewerTier.BASIC: "Basic",
    BrewerTier.TEMPERATURE: "Temperature Control",
    BrewerTier.PRE_INFUSION: "Pre-infusion",
    BrewerTier.PRESSURE_FLOW: "Pressure & Flow",
    BrewerTier.FULL_PROGRAMMABLE: "Full Programmable",
}

# Keep TIER_LABELS as a public alias for backward compat
TIER_LABELS: dict[int, str] = {t.value: label for t, label in _TIER_LABELS.items()}


class HasBrewerCapabilities(Protocol):
    """Protocol for objects that expose brewer capability attributes."""

    flow_control_type: str
    pressure_control_type: str
    preinfusion_type: str
    temp_control_type: str


def derive_tier(brewer: HasBrewerCapabilities) -> BrewerTier:
    """Derive UX tier (1--5) from brewer capability flags.

    Parameters
    ----------
    brewer : HasBrewerCapabilities
        Any object with the following string attributes:
        ``flow_control_type``, ``pressure_control_type``,
        ``preinfusion_type``, ``temp_control_type``.

    Returns
    -------
    BrewerTier
        Enum member representing the tier (1--5) based on the
        highest-capability feature present.
    """
    # Tier 5: programmable flow control (Decent DE1, Meticulous, Cremina mod)
    if brewer.flow_control_type == "programmable":
        return BrewerTier.FULL_PROGRAMMABLE

    # Tier 4: any flow control OR programmable/manual pressure profiling
    if brewer.flow_control_type in ("manual_paddle", "manual_valve"):
        return BrewerTier.PRESSURE_FLOW
    if brewer.pressure_control_type in ("manual_profiling", "programmable"):
        return BrewerTier.PRESSURE_FLOW

    # Tier 3: timed or adjustable pre-infusion (Sage Dual Boiler, Profitec Pro 300)
    if brewer.preinfusion_type in ("timed", "adjustable_pressure", "programmable"):
        return BrewerTier.PRE_INFUSION

    # Tier 2: PID or profiling temperature control (Rancilio Silvia Pro X, ECM Synchronika)
    if brewer.temp_control_type in ("pid", "profiling"):
        return BrewerTier.TEMPERATURE

    # Tier 1: basic -- no controllable parameters beyond grind/dose/yield
    # (Gaggia Classic stock, Bambino Plus preset-only, manual lever machines)
    return BrewerTier.BASIC

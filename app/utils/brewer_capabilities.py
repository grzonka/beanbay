"""Brewer capability utilities.

Provides derive_tier() to compute a UX tier (1-5) from a Brewer's capability
flags, and TIER_LABELS for human-readable display.

Tier progression (from most basic to most capable):
  Tier 1 — Basic:             grind, dose, yield only (no controllable temp/pressure/flow)
  Tier 2 — Temperature:       + temperature setting (PID or profiling)
  Tier 3 — Pre-infusion:      + timed / adjustable pre-infusion
  Tier 4 — Pressure & Flow:   + manual pressure profiling or paddle/valve flow control
  Tier 5 — Full Programmable: + fully programmable flow control (Decent DE1, Meticulous)
"""

from __future__ import annotations

TIER_LABELS: dict[int, str] = {
    1: "Basic",
    2: "Temperature Control",
    3: "Pre-infusion",
    4: "Pressure & Flow",
    5: "Full Programmable",
}


def derive_tier(brewer) -> int:
    """Derive UX tier (1-5) from brewer capability flags.

    Args:
        brewer: A Brewer ORM instance with capability attributes already
                populated (i.e. after DB flush or with Python-side defaults).

    Returns:
        Integer tier 1-5 based on the highest-capability feature present.
    """
    # Tier 5: programmable flow control (Decent DE1, Meticulous, Cremina mod)
    if brewer.flow_control_type == "programmable":
        return 5

    # Tier 4: any flow control OR programmable/manual pressure profiling
    if brewer.flow_control_type in ("manual_paddle", "manual_valve"):
        return 4
    if brewer.pressure_control_type in ("manual_profiling", "programmable"):
        return 4

    # Tier 3: timed or adjustable pre-infusion (Sage Dual Boiler, Profitec Pro 300)
    if brewer.preinfusion_type in ("timed", "adjustable_pressure", "programmable"):
        return 3

    # Tier 2: PID or profiling temperature control (Rancilio Silvia Pro X, ECM Synchronika)
    if brewer.temp_control_type in ("pid", "profiling"):
        return 2

    # Tier 1: basic — no controllable parameters beyond grind/dose/yield
    # (Gaggia Classic stock, Bambino Plus preset-only, manual lever machines)
    return 1

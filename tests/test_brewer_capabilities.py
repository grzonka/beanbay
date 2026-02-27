"""Tests for Brewer capability model columns and derive_tier() utility.

Covers:
- Default capability values (model-level and post-flush)
- Custom capability values
- DB persistence round-trip
- All 5 tier boundaries
- Real machine classifications: Gaggia stock→T1, Sage DB→T3, Decent DE1→T5
"""

from app.models.equipment import (
    FLOW_CONTROL_TYPES,
    PREINFUSION_TYPES,
    PRESSURE_CONTROL_TYPES,
    STOP_MODES,
    TEMP_CONTROL_TYPES,
    Brewer,
)
from app.utils.brewer_capabilities import TIER_LABELS, derive_tier


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


def test_temp_control_types_values():
    """TEMP_CONTROL_TYPES contains all expected values."""
    assert set(TEMP_CONTROL_TYPES) == {"none", "preset", "pid", "profiling"}


def test_preinfusion_types_values():
    """PREINFUSION_TYPES contains all expected values."""
    assert set(PREINFUSION_TYPES) == {
        "none",
        "fixed",
        "timed",
        "adjustable_pressure",
        "programmable",
        "manual",
    }


def test_pressure_control_types_values():
    """PRESSURE_CONTROL_TYPES contains all expected values."""
    assert set(PRESSURE_CONTROL_TYPES) == {
        "fixed",
        "opv_adjustable",
        "electronic",
        "manual_profiling",
        "programmable",
    }


def test_flow_control_types_values():
    """FLOW_CONTROL_TYPES contains all expected values."""
    assert set(FLOW_CONTROL_TYPES) == {"none", "manual_paddle", "manual_valve", "programmable"}


def test_stop_modes_values():
    """STOP_MODES contains all expected values."""
    assert set(STOP_MODES) == {"manual", "timed", "volumetric", "gravimetric"}


def test_tier_labels_all_tiers():
    """TIER_LABELS has entries for tiers 1-5."""
    assert set(TIER_LABELS.keys()) == {1, 2, 3, 4, 5}
    assert all(isinstance(v, str) and v for v in TIER_LABELS.values())


# ---------------------------------------------------------------------------
# Default capability checks (Python-side, pre-flush)
# ---------------------------------------------------------------------------


def test_brewer_default_capabilities_pre_flush():
    """Brewer Python-side defaults are set correctly before any DB flush."""
    b = Brewer(name="Test Brewer")
    assert b.temp_control_type == "pid"
    assert b.preinfusion_type == "none"
    assert b.pressure_control_type == "fixed"
    assert b.flow_control_type == "none"
    assert b.has_bloom is False
    assert b.stop_mode == "manual"


def test_brewer_default_float_columns_are_none():
    """Float capability columns default to None before flush (no range set)."""
    b = Brewer(name="Test Brewer")
    assert b.temp_min is None
    assert b.temp_max is None
    assert b.temp_step is None
    assert b.preinfusion_max_time is None
    assert b.pressure_min is None
    assert b.pressure_max is None


# ---------------------------------------------------------------------------
# Custom capabilities
# ---------------------------------------------------------------------------


def test_brewer_custom_capabilities():
    """Brewer accepts and stores arbitrary valid capability values."""
    b = Brewer(
        name="Decent DE1",
        temp_control_type="profiling",
        temp_min=20.0,
        temp_max=105.0,
        temp_step=0.1,
        preinfusion_type="programmable",
        preinfusion_max_time=30.0,
        pressure_control_type="programmable",
        pressure_min=0.0,
        pressure_max=13.0,
        flow_control_type="programmable",
        has_bloom=True,
        stop_mode="gravimetric",
    )
    assert b.temp_control_type == "profiling"
    assert b.temp_min == 20.0
    assert b.temp_max == 105.0
    assert b.temp_step == 0.1
    assert b.preinfusion_type == "programmable"
    assert b.preinfusion_max_time == 30.0
    assert b.pressure_control_type == "programmable"
    assert b.pressure_min == 0.0
    assert b.pressure_max == 13.0
    assert b.flow_control_type == "programmable"
    assert b.has_bloom is True
    assert b.stop_mode == "gravimetric"


# ---------------------------------------------------------------------------
# DB persistence round-trip
# ---------------------------------------------------------------------------


def test_brewer_capabilities_persist_defaults(db_session):
    """Default capabilities survive a DB round-trip (flush + reload)."""
    b = Brewer(name="Default Brewer")
    db_session.add(b)
    db_session.flush()

    loaded = db_session.query(Brewer).filter_by(name="Default Brewer").one()
    assert loaded.temp_control_type == "pid"
    assert loaded.preinfusion_type == "none"
    assert loaded.pressure_control_type == "fixed"
    assert loaded.flow_control_type == "none"
    assert loaded.has_bloom is False
    assert loaded.stop_mode == "manual"
    assert loaded.temp_min is None
    assert loaded.temp_max is None


def test_brewer_capabilities_persist_custom(db_session):
    """Custom capabilities survive a DB round-trip."""
    b = Brewer(
        name="Lelit Bianca",
        temp_control_type="pid",
        temp_min=85.0,
        temp_max=105.0,
        temp_step=1.0,
        preinfusion_type="timed",
        preinfusion_max_time=10.0,
        pressure_control_type="manual_profiling",
        pressure_min=3.0,
        pressure_max=12.0,
        flow_control_type="manual_paddle",
        has_bloom=False,
        stop_mode="volumetric",
    )
    db_session.add(b)
    db_session.flush()

    loaded = db_session.query(Brewer).filter_by(name="Lelit Bianca").one()
    assert loaded.temp_control_type == "pid"
    assert loaded.temp_min == 85.0
    assert loaded.temp_max == 105.0
    assert loaded.temp_step == 1.0
    assert loaded.preinfusion_type == "timed"
    assert loaded.preinfusion_max_time == 10.0
    assert loaded.pressure_control_type == "manual_profiling"
    assert loaded.pressure_min == 3.0
    assert loaded.pressure_max == 12.0
    assert loaded.flow_control_type == "manual_paddle"
    assert loaded.has_bloom is False
    assert loaded.stop_mode == "volumetric"


# ---------------------------------------------------------------------------
# Tier boundary tests
# ---------------------------------------------------------------------------


def test_tier1_no_temp_control():
    """Brewer with temp_control_type=none is Tier 1 (Basic)."""
    b = Brewer(name="Stock Gaggia", temp_control_type="none")
    assert derive_tier(b) == 1


def test_tier1_preset_temp():
    """Brewer with temp_control_type=preset is Tier 1 — presets are not PID."""
    b = Brewer(name="Bambino Plus", temp_control_type="preset")
    assert derive_tier(b) == 1


def test_tier2_pid_temp():
    """Brewer with temp_control_type=pid is Tier 2 (Temperature Control)."""
    b = Brewer(name="Rancilio Silvia Pro X")  # default is pid
    assert derive_tier(b) == 2


def test_tier2_profiling_temp():
    """Brewer with temp_control_type=profiling is Tier 2."""
    b = Brewer(name="ECM Synchronika", temp_control_type="profiling")
    assert derive_tier(b) == 2


def test_tier3_timed_preinfusion():
    """Brewer with timed preinfusion is Tier 3 (Pre-infusion)."""
    b = Brewer(name="Sage DB", temp_control_type="pid", preinfusion_type="timed")
    assert derive_tier(b) == 3


def test_tier3_adjustable_preinfusion():
    """Brewer with adjustable_pressure preinfusion is Tier 3."""
    b = Brewer(name="ECM Classika PID", preinfusion_type="adjustable_pressure")
    assert derive_tier(b) == 3


def test_tier3_programmable_preinfusion():
    """Brewer with programmable preinfusion (but no flow control) is Tier 3."""
    b = Brewer(
        name="Hypothetical",
        preinfusion_type="programmable",
        flow_control_type="none",
        pressure_control_type="fixed",
    )
    assert derive_tier(b) == 3


def test_tier4_manual_paddle():
    """Brewer with manual_paddle flow control is Tier 4 (Pressure & Flow)."""
    b = Brewer(name="Lelit Bianca", flow_control_type="manual_paddle")
    assert derive_tier(b) == 4


def test_tier4_manual_valve():
    """Brewer with manual_valve flow control is Tier 4."""
    b = Brewer(name="Rocket Appartamento Valve Mod", flow_control_type="manual_valve")
    assert derive_tier(b) == 4


def test_tier4_manual_profiling_pressure():
    """Brewer with manual_profiling pressure is Tier 4."""
    b = Brewer(name="La Marzocco GS3 MP", pressure_control_type="manual_profiling")
    assert derive_tier(b) == 4


def test_tier4_programmable_pressure():
    """Brewer with programmable pressure control (no flow) is Tier 4."""
    b = Brewer(
        name="Profitec Pro 800",
        pressure_control_type="programmable",
        flow_control_type="none",
    )
    assert derive_tier(b) == 4


def test_tier5_programmable_flow():
    """Brewer with programmable flow control is Tier 5 (Full Programmable)."""
    b = Brewer(name="Decent DE1", flow_control_type="programmable")
    assert derive_tier(b) == 5


def test_tier5_overrides_pressure():
    """Programmable flow control → Tier 5 even if pressure_control_type is basic."""
    b = Brewer(
        name="Meticulous",
        flow_control_type="programmable",
        pressure_control_type="fixed",
    )
    assert derive_tier(b) == 5


# ---------------------------------------------------------------------------
# Real machine classification tests
# ---------------------------------------------------------------------------


def test_gaggia_stock_tier1():
    """Gaggia Classic stock (no PID, no pressure control) → Tier 1."""
    gaggia_stock = Brewer(
        name="Gaggia Classic Stock",
        temp_control_type="none",
        preinfusion_type="none",
        pressure_control_type="fixed",
        flow_control_type="none",
        has_bloom=False,
        stop_mode="manual",
    )
    assert derive_tier(gaggia_stock) == 1
    assert TIER_LABELS[derive_tier(gaggia_stock)] == "Basic"


def test_sage_dual_boiler_tier3():
    """Sage Dual Boiler (PID + timed preinfusion, OPV-adjustable) → Tier 3."""
    sage_db = Brewer(
        name="Sage Dual Boiler",
        temp_control_type="pid",
        temp_min=85.0,
        temp_max=100.0,
        temp_step=1.0,
        preinfusion_type="timed",
        preinfusion_max_time=15.0,
        pressure_control_type="opv_adjustable",
        pressure_min=6.0,
        pressure_max=12.0,
        flow_control_type="none",
        has_bloom=False,
        stop_mode="volumetric",
    )
    assert derive_tier(sage_db) == 3
    assert TIER_LABELS[derive_tier(sage_db)] == "Pre-infusion"


def test_decent_de1_tier5():
    """Decent DE1 (programmable flow, profiling everything) → Tier 5."""
    decent_de1 = Brewer(
        name="Decent DE1",
        temp_control_type="profiling",
        temp_min=20.0,
        temp_max=105.0,
        temp_step=0.1,
        preinfusion_type="programmable",
        preinfusion_max_time=30.0,
        pressure_control_type="programmable",
        pressure_min=0.0,
        pressure_max=13.0,
        flow_control_type="programmable",
        has_bloom=True,
        stop_mode="gravimetric",
    )
    assert derive_tier(decent_de1) == 5
    assert TIER_LABELS[derive_tier(decent_de1)] == "Full Programmable"

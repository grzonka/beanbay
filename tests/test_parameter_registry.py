"""Tests for app/services/parameter_registry.py

Covers:
  - Registry shape (7 methods, required fields, no duplicate param names per method)
  - Backward compatibility: espresso and pour-over match legacy optimizer.py constants exactly
  - Capability filtering: brewer flags control which advanced params appear
  - Override tests: per-param bound overrides applied correctly
  - Grind range tests: suggest_grind_range uses grinder min/max_value correctly
  - requires_check edge cases
  - get_default_bounds / get_rounding_rules
  - BayBE parameter object types
"""

from types import SimpleNamespace

import pytest
from baybe.parameters import CategoricalParameter, NumericalContinuousParameter

from app.services.parameter_registry import (
    METHOD_GRIND_PERCENTAGES,
    PARAMETER_REGISTRY,
    build_parameters_for_setup,
    get_default_bounds,
    get_param_columns,
    get_rounding_rules,
    requires_check,
    suggest_grind_range,
)

# ---------------------------------------------------------------------------
# Legacy constants from optimizer.py — must match registry exactly
# ---------------------------------------------------------------------------
LEGACY_BAYBE_PARAM_COLUMNS = [
    "grind_setting",
    "temperature",
    "preinfusion_pressure_pct",
    "dose_in",
    "target_yield",
    "saturation",
]
LEGACY_POUR_OVER_PARAM_COLUMNS = [
    "grind_setting",
    "temperature",
    "bloom_weight",
    "dose_in",
    "brew_volume",
]
LEGACY_DEFAULT_BOUNDS = {
    "grind_setting": (15.0, 25.0),
    "temperature": (86.0, 96.0),
    "preinfusion_pressure_pct": (55.0, 100.0),
    "dose_in": (18.5, 20.0),
    "target_yield": (36.0, 50.0),
}
LEGACY_POUR_OVER_DEFAULT_BOUNDS = {
    "grind_setting": (15.0, 40.0),
    "temperature": (88.0, 98.0),
    "bloom_weight": (20.0, 80.0),
    "dose_in": (12.0, 22.0),
    "brew_volume": (150.0, 500.0),
}
LEGACY_ROUNDING_RULES = {
    "grind_setting": 0.5,
    "temperature": 1.0,
    "preinfusion_pressure_pct": 5.0,
    "dose_in": 0.5,
    "target_yield": 1.0,
}
LEGACY_POUR_OVER_ROUNDING_RULES = {
    "grind_setting": 0.5,
    "temperature": 1.0,
    "bloom_weight": 1.0,
    "dose_in": 0.5,
    "brew_volume": 5.0,
}

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def make_brewer(**kwargs) -> SimpleNamespace:
    """Create a minimal mock brewer with capability attributes."""
    defaults = {
        "preinfusion_type": "none",
        "pressure_control_type": "fixed",
        "temp_control_type": "pid",
        "flow_control_type": "none",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_grinder(min_value=0.0, max_value=100.0) -> SimpleNamespace:
    """Create a minimal mock grinder."""
    return SimpleNamespace(min_value=min_value, max_value=max_value)


# ===========================================================================
# 1. Registry shape tests
# ===========================================================================

EXPECTED_METHODS = {
    "espresso",
    "pour-over",
    "french-press",
    "aeropress",
    "turkish",
    "moka-pot",
    "cold-brew",
}


class TestRegistryShape:
    def test_all_seven_methods_present(self):
        """Registry must contain exactly the 7 brew methods."""
        assert set(PARAMETER_REGISTRY.keys()) == EXPECTED_METHODS

    def test_each_method_has_at_least_one_param(self):
        """Every method must have at least one parameter definition."""
        for method, params in PARAMETER_REGISTRY.items():
            assert len(params) >= 1, f"{method} has no parameters"

    def test_required_fields_present_in_every_param(self):
        """Every param dict must have 'name', 'type', 'requires'."""
        for method, params in PARAMETER_REGISTRY.items():
            for pdef in params:
                assert "name" in pdef, f"{method}: param missing 'name'"
                assert "type" in pdef, f"{method}: param {pdef.get('name')} missing 'type'"
                assert "requires" in pdef, f"{method}: param {pdef.get('name')} missing 'requires'"

    def test_no_duplicate_param_names_per_method(self):
        """Parameter names must be unique within each method."""
        for method, params in PARAMETER_REGISTRY.items():
            names = [p["name"] for p in params]
            assert len(names) == len(set(names)), f"{method} has duplicate param names: {names}"

    def test_continuous_params_have_bounds(self):
        """All continuous params must have 'bounds' tuple of length 2."""
        for method, params in PARAMETER_REGISTRY.items():
            for pdef in params:
                if pdef["type"] == "continuous":
                    assert "bounds" in pdef, f"{method}/{pdef['name']} missing bounds"
                    assert len(pdef["bounds"]) == 2, (
                        f"{method}/{pdef['name']} bounds must be (min, max)"
                    )
                    lo, hi = pdef["bounds"]
                    assert lo < hi, f"{method}/{pdef['name']} bounds lo >= hi"

    def test_categorical_params_have_values(self):
        """All categorical params must have non-empty 'values' list."""
        for method, params in PARAMETER_REGISTRY.items():
            for pdef in params:
                if pdef["type"] == "categorical":
                    assert "values" in pdef, f"{method}/{pdef['name']} missing values"
                    assert len(pdef["values"]) >= 2, f"{method}/{pdef['name']} needs ≥2 values"

    def test_method_grind_percentages_has_all_methods(self):
        """METHOD_GRIND_PERCENTAGES covers all 7 methods."""
        assert set(METHOD_GRIND_PERCENTAGES.keys()) == EXPECTED_METHODS

    def test_grind_percentages_are_valid_fractions(self):
        """Grind percentages must be in [0,1] and lo < hi."""
        for method, (lo, hi) in METHOD_GRIND_PERCENTAGES.items():
            assert 0.0 <= lo < hi <= 1.0, f"{method} grind percentages invalid: ({lo}, {hi})"


# ===========================================================================
# 2. Backward compatibility — espresso
# ===========================================================================


class TestEspressoBackwardCompat:
    def test_espresso_columns_no_brewer_returns_tier1(self):
        """Phase 20: get_param_columns('espresso') with no brewer returns Tier 1 (4 params).

        Legacy params (preinfusion_pressure_pct, saturation) are excluded from new campaigns.
        Capability-gated params are excluded when no brewer context is provided.
        """
        columns = get_param_columns("espresso")
        assert columns == ["grind_setting", "temperature", "dose_in", "target_yield"]

    def test_espresso_legacy_params_still_in_bounds(self):
        """get_default_bounds includes legacy params — needed for form validation + history."""
        bounds = get_default_bounds("espresso")
        # Legacy params must still have bounds for backward compat display
        assert "preinfusion_pressure_pct" in bounds
        assert (
            bounds["preinfusion_pressure_pct"] == LEGACY_DEFAULT_BOUNDS["preinfusion_pressure_pct"]
        )

    def test_espresso_bounds_match_legacy_for_core_params(self):
        """Core param bounds (grind, temp, dose, yield) must match legacy values."""
        bounds = get_default_bounds("espresso")
        core_legacy = {
            k: v for k, v in LEGACY_DEFAULT_BOUNDS.items() if k not in ("preinfusion_pressure_pct",)
        }
        for param, expected in core_legacy.items():
            assert bounds[param] == expected, f"espresso bounds mismatch for {param}"

    def test_espresso_rounding_matches_legacy_for_core_params(self):
        """Core param rounding rules (grind, temp, dose, yield) must match legacy values."""
        rules = get_rounding_rules("espresso")
        core_legacy = {
            k: v for k, v in LEGACY_ROUNDING_RULES.items() if k not in ("preinfusion_pressure_pct",)
        }
        for param, expected in core_legacy.items():
            assert rules[param] == expected, f"espresso rounding mismatch for {param}"

    def test_espresso_legacy_rounding_still_present(self):
        """get_rounding_rules includes legacy params — used for historical data display."""
        rules = get_rounding_rules("espresso")
        assert "preinfusion_pressure_pct" in rules
        assert (
            rules["preinfusion_pressure_pct"] == LEGACY_ROUNDING_RULES["preinfusion_pressure_pct"]
        )

    def test_espresso_build_no_brewer_returns_four_params(self):
        """Phase 20: build_parameters_for_setup('espresso') with no brewer returns Tier 1 (4 params).

        Legacy params excluded. Capability-gated params excluded without brewer context.
        """
        params = build_parameters_for_setup("espresso")
        assert len(params) == 4

    def test_espresso_build_no_brewer_all_continuous(self):
        """Phase 20: Tier 1 espresso has 4 NumericalContinuous params, no categoricals."""
        params = build_parameters_for_setup("espresso")
        continuous = [p for p in params if isinstance(p, NumericalContinuousParameter)]
        categorical = [p for p in params if isinstance(p, CategoricalParameter)]
        assert len(continuous) == 4
        assert len(categorical) == 0

    def test_espresso_legacy_params_excluded_from_new_campaigns(self):
        """preinfusion_pressure_pct and saturation must NOT appear in new espresso campaigns."""
        params = build_parameters_for_setup("espresso")
        names = [p.name for p in params]
        assert "preinfusion_pressure_pct" not in names, (
            "Legacy preinfusion_pressure_pct must not be in new campaigns"
        )
        assert "saturation" not in names, "Legacy saturation must not be in new campaigns"


# ===========================================================================
# 3. Backward compatibility — pour-over
# ===========================================================================


class TestPourOverBackwardCompat:
    def test_pour_over_columns_match_legacy(self):
        """get_param_columns('pour-over') must match legacy POUR_OVER_PARAM_COLUMNS."""
        assert get_param_columns("pour-over") == LEGACY_POUR_OVER_PARAM_COLUMNS

    def test_pour_over_bounds_match_legacy(self):
        """get_default_bounds('pour-over') must match legacy POUR_OVER_DEFAULT_BOUNDS."""
        bounds = get_default_bounds("pour-over")
        for param, expected in LEGACY_POUR_OVER_DEFAULT_BOUNDS.items():
            assert bounds[param] == expected, f"pour-over bounds mismatch for {param}"

    def test_pour_over_rounding_matches_legacy(self):
        """get_rounding_rules('pour-over') must match legacy POUR_OVER_ROUNDING_RULES."""
        rules = get_rounding_rules("pour-over")
        for param, expected in LEGACY_POUR_OVER_ROUNDING_RULES.items():
            assert rules[param] == expected, f"pour-over rounding mismatch for {param}"

    def test_pour_over_build_no_brewer_returns_five_params(self):
        """build_parameters_for_setup('pour-over') returns exactly 5 params."""
        params = build_parameters_for_setup("pour-over")
        assert len(params) == 5

    def test_pour_over_all_continuous(self):
        """All pour-over params must be NumericalContinuousParameter."""
        params = build_parameters_for_setup("pour-over")
        for p in params:
            assert isinstance(p, NumericalContinuousParameter), f"{p.name} should be continuous"


# ===========================================================================
# 4. Capability filtering — espresso advanced params
# ===========================================================================


class TestCapabilityFiltering:
    def test_no_brewer_excludes_advanced_params(self):
        """With brewer=None, capability-gated params (preinfusion_time etc.) are excluded."""
        params = build_parameters_for_setup("espresso", brewer=None)
        names = [p.name for p in params]
        assert "preinfusion_time" not in names
        assert "brew_pressure" not in names
        assert "pressure_profile" not in names

    def test_basic_brewer_excludes_advanced_params(self):
        """A basic brewer (none/fixed preinfusion and pressure) excludes advanced params."""
        brewer = make_brewer(preinfusion_type="none", pressure_control_type="fixed")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "preinfusion_time" not in names
        assert "brew_pressure" not in names
        assert "pressure_profile" not in names

    def test_timed_preinfusion_includes_preinfusion_time(self):
        """Brewer with preinfusion_type='timed' → preinfusion_time included."""
        brewer = make_brewer(preinfusion_type="timed")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "preinfusion_time" in names

    def test_adjustable_pressure_preinfusion_includes_preinfusion_time(self):
        """Brewer with preinfusion_type='adjustable_pressure' → preinfusion_time included."""
        brewer = make_brewer(preinfusion_type="adjustable_pressure")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "preinfusion_time" in names

    def test_programmable_preinfusion_includes_preinfusion_time(self):
        """Brewer with preinfusion_type='programmable' → preinfusion_time included."""
        brewer = make_brewer(preinfusion_type="programmable")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "preinfusion_time" in names

    def test_opv_adjustable_pressure_includes_brew_pressure(self):
        """Brewer with pressure_control_type='opv_adjustable' → brew_pressure included."""
        brewer = make_brewer(pressure_control_type="opv_adjustable")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "brew_pressure" in names

    def test_manual_profiling_pressure_includes_pressure_profile(self):
        """Brewer with pressure_control_type='manual_profiling' → pressure_profile included."""
        brewer = make_brewer(pressure_control_type="manual_profiling")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "pressure_profile" in names

    def test_programmable_brewer_includes_all_advanced(self):
        """Fully programmable brewer → all advanced params included."""
        brewer = make_brewer(
            preinfusion_type="programmable",
            pressure_control_type="programmable",
        )
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        assert "preinfusion_time" in names
        assert "brew_pressure" in names
        assert "pressure_profile" in names

    def test_get_param_columns_with_capable_brewer(self):
        """get_param_columns with capable brewer includes advanced param names."""
        brewer = make_brewer(preinfusion_type="timed")
        columns = get_param_columns("espresso", brewer=brewer)
        assert "preinfusion_time" in columns

    def test_basic_brewer_core_params_still_present(self):
        """Basic brewer gets all Phase 20 Tier 1 espresso params (no legacy, no advanced)."""
        brewer = make_brewer(preinfusion_type="none", pressure_control_type="fixed")
        params = build_parameters_for_setup("espresso", brewer=brewer)
        names = [p.name for p in params]
        for core_param in [
            "grind_setting",
            "temperature",
            "dose_in",
            "target_yield",
        ]:
            assert core_param in names, f"Core param {core_param} missing with basic brewer"
        # Legacy params must NOT appear in new campaigns
        assert "preinfusion_pressure_pct" not in names, (
            "Legacy param must not appear in new campaigns"
        )
        assert "saturation" not in names, "Legacy param must not appear in new campaigns"


# ===========================================================================
# 5. Override tests
# ===========================================================================


class TestOverrides:
    def test_override_grind_setting_bounds(self):
        """Overriding grind_setting bounds replaces default bounds."""
        overrides = {"grind_setting": {"min": 18.0, "max": 22.0}}
        params = build_parameters_for_setup("espresso", overrides=overrides)
        grind = next(p for p in params if p.name == "grind_setting")
        assert isinstance(grind, NumericalContinuousParameter)
        assert grind.bounds.lower == 18.0
        assert grind.bounds.upper == 22.0

    def test_override_partial_bounds_min_only(self):
        """Overriding only 'min' leaves 'max' at default."""
        overrides = {"grind_setting": {"min": 18.0}}
        params = build_parameters_for_setup("espresso", overrides=overrides)
        grind = next(p for p in params if p.name == "grind_setting")
        assert grind.bounds.lower == 18.0
        assert grind.bounds.upper == 25.0  # default max

    def test_override_does_not_affect_other_params(self):
        """Overriding one param does not change others."""
        overrides = {"grind_setting": {"min": 18.0, "max": 22.0}}
        params = build_parameters_for_setup("espresso", overrides=overrides)
        temp = next(p for p in params if p.name == "temperature")
        assert temp.bounds.lower == 86.0
        assert temp.bounds.upper == 96.0

    def test_none_overrides_uses_defaults(self):
        """None overrides → default bounds used."""
        params = build_parameters_for_setup("espresso", overrides=None)
        grind = next(p for p in params if p.name == "grind_setting")
        assert grind.bounds.lower == 15.0
        assert grind.bounds.upper == 25.0

    def test_empty_overrides_uses_defaults(self):
        """Empty dict overrides → default bounds used."""
        params = build_parameters_for_setup("espresso", overrides={})
        grind = next(p for p in params if p.name == "grind_setting")
        assert grind.bounds.lower == 15.0
        assert grind.bounds.upper == 25.0


# ===========================================================================
# 6. Grind range tests
# ===========================================================================


class TestGrindRange:
    def test_espresso_grind_range_basic(self):
        """Espresso grind range is 15–40% of grinder range."""
        grinder = make_grinder(min_value=0.0, max_value=100.0)
        lo, hi = suggest_grind_range(grinder, "espresso")
        assert lo == pytest.approx(15.0)
        assert hi == pytest.approx(40.0)

    def test_pour_over_grind_range_basic(self):
        """Pour-over grind range is 40–70% of grinder range."""
        grinder = make_grinder(min_value=0.0, max_value=100.0)
        lo, hi = suggest_grind_range(grinder, "pour-over")
        assert lo == pytest.approx(40.0)
        assert hi == pytest.approx(70.0)

    def test_grind_range_with_offset_grinder(self):
        """Grinder starting at non-zero min_value shifts the range correctly."""
        grinder = make_grinder(min_value=10.0, max_value=110.0)
        lo, hi = suggest_grind_range(grinder, "espresso")
        # range = 100, espresso = (0.15, 0.40) → 10+15=25, 10+40=50
        assert lo == pytest.approx(25.0)
        assert hi == pytest.approx(50.0)

    def test_grind_range_none_grinder_returns_none(self):
        """None grinder returns None."""
        assert suggest_grind_range(None, "espresso") is None

    def test_grind_range_no_min_value_returns_none(self):
        """Grinder without min_value returns None."""
        grinder = SimpleNamespace(min_value=None, max_value=100.0)
        assert suggest_grind_range(grinder, "espresso") is None

    def test_grind_range_no_max_value_returns_none(self):
        """Grinder without max_value returns None."""
        grinder = SimpleNamespace(min_value=0.0, max_value=None)
        assert suggest_grind_range(grinder, "espresso") is None

    def test_all_methods_produce_range_with_valid_grinder(self):
        """All 7 methods produce a valid grind range for a grinder with full range."""
        grinder = make_grinder(min_value=0.0, max_value=100.0)
        for method in EXPECTED_METHODS:
            result = suggest_grind_range(grinder, method)
            assert result is not None, f"{method} returned None"
            lo, hi = result
            assert lo < hi, f"{method} grind range lo >= hi"


# ===========================================================================
# 7. requires_check edge cases
# ===========================================================================


class TestRequiresCheck:
    def test_none_condition_always_true(self):
        """None condition → always included (True)."""
        assert requires_check(None, None) is True
        assert requires_check(None, make_brewer()) is True

    def test_none_brewer_with_condition_returns_false(self):
        """None brewer + non-None condition → False (exclude gated params when no brewer context)."""
        cond = "brewer.preinfusion_type in (timed, programmable)"
        assert requires_check(cond, None) is False

    def test_matching_value_returns_true(self):
        """Brewer value in allowed set → True."""
        brewer = make_brewer(preinfusion_type="timed")
        cond = "brewer.preinfusion_type in (timed, adjustable_pressure, programmable)"
        assert requires_check(cond, brewer) is True

    def test_non_matching_value_returns_false(self):
        """Brewer value NOT in allowed set → False."""
        brewer = make_brewer(preinfusion_type="none")
        cond = "brewer.preinfusion_type in (timed, adjustable_pressure, programmable)"
        assert requires_check(cond, brewer) is False

    def test_single_value_condition(self):
        """Single value in condition parens."""
        brewer = make_brewer(pressure_control_type="programmable")
        cond = "brewer.pressure_control_type in (programmable)"
        assert requires_check(cond, brewer) is True

    def test_missing_attr_returns_false(self):
        """Brewer without the required attribute → False."""
        brewer = SimpleNamespace()  # no preinfusion_type attribute
        cond = "brewer.preinfusion_type in (timed)"
        assert requires_check(cond, brewer) is False


# ===========================================================================
# 8. get_default_bounds / get_rounding_rules
# ===========================================================================


class TestGetters:
    def test_get_default_bounds_excludes_categorical(self):
        """get_default_bounds must not include categorical params."""
        bounds = get_default_bounds("espresso")
        assert "saturation" not in bounds

    def test_get_rounding_rules_excludes_categorical(self):
        """get_rounding_rules must not include categorical params."""
        rules = get_rounding_rules("espresso")
        assert "saturation" not in rules

    def test_get_rounding_rules_excludes_none_rounding(self):
        """get_rounding_rules excludes params with rounding=None."""
        # All core espresso params have defined rounding rules
        rules = get_rounding_rules("espresso")
        for name, step in rules.items():
            assert step is not None

    def test_unknown_method_falls_back_to_espresso(self):
        """Unknown method falls back to espresso registry."""
        columns = get_param_columns("unknown-method")
        espresso_columns = get_param_columns("espresso")
        assert columns == espresso_columns

    def test_french_press_has_steep_time(self):
        """French press registry includes steep_time parameter."""
        bounds = get_default_bounds("french-press")
        assert "steep_time" in bounds

    def test_cold_brew_has_steep_time_in_minutes(self):
        """Cold brew steep_time bounds are in minutes (720–1440 = 12–24h)."""
        bounds = get_default_bounds("cold-brew")
        assert "steep_time" in bounds
        lo, hi = bounds["steep_time"]
        assert lo == 720.0
        assert hi == 1440.0

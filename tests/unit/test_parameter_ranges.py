"""Unit tests for effective parameter range computation."""

from __future__ import annotations

import json

import pytest

from beanbay.services.parameter_ranges import (
    compute_effective_ranges,
)


# ---------------------------------------------------------------------------
# Fake domain objects (duck-typed, no DB dependencies)
# ---------------------------------------------------------------------------


class FakeMethodDefault:
    """Mimics a MethodParameterDefault row."""

    def __init__(
        self,
        parameter_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
        step: float | None = None,
        allowed_values: str | None = None,
        requires: str | None = None,
    ):
        self.parameter_name = parameter_name
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.allowed_values = allowed_values
        self.requires = requires


class FakeBrewer:
    """Mimics a Brewer with equipment capability attributes."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeGrinder:
    """Mimics a Grinder with ring_sizes_json."""

    def __init__(self, ring_sizes_json: str | None = None):
        self.ring_sizes_json = ring_sizes_json


class FakeBeanOverride:
    """Mimics a BeanParameterOverride row."""

    def __init__(
        self,
        parameter_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ):
        self.parameter_name = parameter_name
        self.min_value = min_value
        self.max_value = max_value


# ---------------------------------------------------------------------------
# 1. Method default only (no brewer, no grinder, no overrides)
# ---------------------------------------------------------------------------


class TestMethodDefaultOnly:
    """Method default range returned as-is when no equipment or overrides."""

    def test_returns_method_default_range(self):
        defaults = [FakeMethodDefault("dose", min_value=14.0, max_value=22.0, step=0.1)]
        result = compute_effective_ranges(defaults, brewer=None, grinder=None, bean_overrides=[])

        assert len(result) == 1
        r = result[0]
        assert r.parameter_name == "dose"
        assert r.min_value == 14.0
        assert r.max_value == 22.0
        assert r.step == 0.1
        assert r.source == "method_default"

    def test_multiple_defaults(self):
        defaults = [
            FakeMethodDefault("dose", min_value=14.0, max_value=22.0, step=0.1),
            FakeMethodDefault("temperature", min_value=85.0, max_value=100.0, step=0.5),
        ]
        result = compute_effective_ranges(defaults, brewer=None, grinder=None, bean_overrides=[])

        assert len(result) == 2
        names = {r.parameter_name for r in result}
        assert names == {"dose", "temperature"}


# ---------------------------------------------------------------------------
# 2. Method default + brewer narrows temperature
# ---------------------------------------------------------------------------


class TestBrewerNarrowsRange:
    """Brewer equipment constraints clip the method default range."""

    def test_brewer_narrows_temperature(self):
        defaults = [FakeMethodDefault("temperature", min_value=85.0, max_value=100.0, step=0.5)]
        brewer = FakeBrewer(temp_min=88.0, temp_max=96.0)

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        assert len(result) == 1
        r = result[0]
        assert r.min_value == 88.0
        assert r.max_value == 96.0
        assert r.source == "equipment"

    def test_brewer_narrows_pressure(self):
        defaults = [FakeMethodDefault("pressure", min_value=6.0, max_value=12.0)]
        brewer = FakeBrewer(pressure_min=7.0, pressure_max=9.5)

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        r = result[0]
        assert r.min_value == 7.0
        assert r.max_value == 9.5
        assert r.source == "equipment"

    def test_brewer_narrows_preinfusion_time(self):
        defaults = [FakeMethodDefault("pre_infusion_time", min_value=0.0, max_value=30.0)]
        brewer = FakeBrewer(preinfusion_max_time=15.0)

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        r = result[0]
        assert r.min_value == 0.0
        assert r.max_value == 15.0
        assert r.source == "equipment"

    def test_brewer_with_none_limits_does_not_narrow(self):
        defaults = [FakeMethodDefault("temperature", min_value=85.0, max_value=100.0)]
        brewer = FakeBrewer(temp_min=None, temp_max=None)

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        r = result[0]
        assert r.min_value == 85.0
        assert r.max_value == 100.0
        assert r.source == "method_default"


# ---------------------------------------------------------------------------
# 3. Method default + bean override narrows dose
# ---------------------------------------------------------------------------


class TestBeanOverrideNarrows:
    """Bean overrides narrow the effective range."""

    def test_override_narrows_dose(self):
        defaults = [FakeMethodDefault("dose", min_value=14.0, max_value=22.0, step=0.1)]
        overrides = [FakeBeanOverride("dose", min_value=16.0, max_value=20.0)]

        result = compute_effective_ranges(
            defaults, brewer=None, grinder=None, bean_overrides=overrides
        )

        r = result[0]
        assert r.min_value == 16.0
        assert r.max_value == 20.0
        assert r.source == "bean_override"

    def test_override_only_min(self):
        defaults = [FakeMethodDefault("dose", min_value=14.0, max_value=22.0)]
        overrides = [FakeBeanOverride("dose", min_value=17.0)]

        result = compute_effective_ranges(
            defaults, brewer=None, grinder=None, bean_overrides=overrides
        )

        r = result[0]
        assert r.min_value == 17.0
        assert r.max_value == 22.0
        assert r.source == "bean_override"

    def test_override_only_max(self):
        defaults = [FakeMethodDefault("dose", min_value=14.0, max_value=22.0)]
        overrides = [FakeBeanOverride("dose", max_value=19.0)]

        result = compute_effective_ranges(
            defaults, brewer=None, grinder=None, bean_overrides=overrides
        )

        r = result[0]
        assert r.min_value == 14.0
        assert r.max_value == 19.0
        assert r.source == "bean_override"


# ---------------------------------------------------------------------------
# 4. All 3 layers combined → most restrictive wins
# ---------------------------------------------------------------------------


class TestAllLayersCombined:
    """When all layers are present, the most restrictive bounds win."""

    def test_most_restrictive_wins(self):
        defaults = [FakeMethodDefault("temperature", min_value=80.0, max_value=100.0, step=0.5)]
        brewer = FakeBrewer(temp_min=85.0, temp_max=96.0)
        overrides = [FakeBeanOverride("temperature", min_value=88.0, max_value=94.0)]

        result = compute_effective_ranges(
            defaults, brewer=brewer, grinder=None, bean_overrides=overrides
        )

        r = result[0]
        assert r.min_value == 88.0
        assert r.max_value == 94.0
        # Bean override was the most restrictive on both sides
        assert r.source == "bean_override"

    def test_mixed_most_restrictive(self):
        """Brewer is most restrictive on min, bean on max."""
        defaults = [FakeMethodDefault("temperature", min_value=80.0, max_value=100.0)]
        brewer = FakeBrewer(temp_min=90.0, temp_max=98.0)
        overrides = [FakeBeanOverride("temperature", min_value=88.0, max_value=93.0)]

        result = compute_effective_ranges(
            defaults, brewer=brewer, grinder=None, bean_overrides=overrides
        )

        r = result[0]
        assert r.min_value == 90.0  # brewer was more restrictive
        assert r.max_value == 93.0  # bean was more restrictive
        # Both equipment and bean contributed, but source reflects
        # that *some* narrowing came from bean_override (latest layer)
        assert r.source == "bean_override"


# ---------------------------------------------------------------------------
# 5. Capability-gated parameter excluded when brewer lacks capability
# ---------------------------------------------------------------------------


class TestCapabilityGateExcluded:
    """Parameters with unmet capability gates are excluded."""

    def test_excluded_when_brewer_lacks_capability(self):
        defaults = [
            FakeMethodDefault("dose", min_value=14.0, max_value=22.0),
            FakeMethodDefault(
                "pre_infusion_time",
                min_value=0.0,
                max_value=30.0,
                requires="preinfusion_type != none",
            ),
        ]
        brewer = FakeBrewer(preinfusion_type="none")

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        names = [r.parameter_name for r in result]
        assert "dose" in names
        assert "pre_infusion_time" not in names

    def test_excluded_when_brewer_is_none_and_requires_set(self):
        defaults = [
            FakeMethodDefault(
                "pressure",
                min_value=6.0,
                max_value=12.0,
                requires="pressure_control_type != fixed",
            ),
        ]

        result = compute_effective_ranges(defaults, brewer=None, grinder=None, bean_overrides=[])

        assert len(result) == 0


# ---------------------------------------------------------------------------
# 6. Capability-gated parameter included when brewer has capability
# ---------------------------------------------------------------------------


class TestCapabilityGateIncluded:
    """Parameters with met capability gates are included."""

    def test_included_when_brewer_has_capability(self):
        defaults = [
            FakeMethodDefault(
                "pre_infusion_time",
                min_value=0.0,
                max_value=30.0,
                requires="preinfusion_type != none",
            ),
        ]
        brewer = FakeBrewer(preinfusion_type="timed", preinfusion_max_time=20.0)

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        assert len(result) == 1
        r = result[0]
        assert r.parameter_name == "pre_infusion_time"
        assert r.min_value == 0.0
        assert r.max_value == 20.0


# ---------------------------------------------------------------------------
# 7. Grind setting from grinder ring_sizes_json
# ---------------------------------------------------------------------------


class TestGrindSettingFromGrinder:
    """Grind setting range is computed from grinder, not method defaults."""

    def test_grind_setting_from_single_ring(self):
        grinder = FakeGrinder(ring_sizes_json=json.dumps([[0, 40, 1]]))

        result = compute_effective_ranges([], brewer=None, grinder=grinder, bean_overrides=[])

        assert len(result) == 1
        r = result[0]
        assert r.parameter_name == "grind_setting"
        assert r.min_value == 0.0
        assert r.max_value == 40.0
        assert r.source == "grinder"

    def test_grind_setting_from_multi_ring(self):
        rings = [[0, 4, 1], [0, 9, 1], [0, 5, 1]]
        grinder = FakeGrinder(ring_sizes_json=json.dumps(rings))

        result = compute_effective_ranges([], brewer=None, grinder=grinder, bean_overrides=[])

        r = result[0]
        assert r.parameter_name == "grind_setting"
        # 5*10*6 = 300 positions -> (0, 299)
        assert r.min_value == 0.0
        assert r.max_value == 299.0
        assert r.source == "grinder"

    def test_grind_setting_with_bean_override(self):
        grinder = FakeGrinder(ring_sizes_json=json.dumps([[0, 40, 1]]))
        overrides = [FakeBeanOverride("grind_setting", min_value=10.0, max_value=30.0)]

        result = compute_effective_ranges(
            [], brewer=None, grinder=grinder, bean_overrides=overrides
        )

        r = result[0]
        assert r.min_value == 10.0
        assert r.max_value == 30.0
        assert r.source == "bean_override"


# ---------------------------------------------------------------------------
# 8. No grinder on setup → grind_setting excluded
# ---------------------------------------------------------------------------


class TestNoGrinder:
    """When no grinder is present, grind_setting is not in the result."""

    def test_no_grinder_no_grind_setting(self):
        defaults = [FakeMethodDefault("dose", min_value=14.0, max_value=22.0)]

        result = compute_effective_ranges(defaults, brewer=None, grinder=None, bean_overrides=[])

        names = [r.parameter_name for r in result]
        assert "grind_setting" not in names

    def test_grinder_with_none_ring_sizes(self):
        """A stepless grinder with no ring config also excludes grind_setting."""
        grinder = FakeGrinder(ring_sizes_json=None)

        result = compute_effective_ranges([], brewer=None, grinder=grinder, bean_overrides=[])

        names = [r.parameter_name for r in result]
        assert "grind_setting" not in names


# ---------------------------------------------------------------------------
# 9. Invalid range after layering (min >= max) → raises ValueError
# ---------------------------------------------------------------------------


class TestInvalidRange:
    """Raise ValueError when layering produces an invalid range."""

    def test_min_equals_max_raises(self):
        defaults = [FakeMethodDefault("dose", min_value=18.0, max_value=22.0)]
        overrides = [FakeBeanOverride("dose", min_value=22.0, max_value=22.0)]

        with pytest.raises(ValueError, match="dose"):
            compute_effective_ranges(
                defaults, brewer=None, grinder=None, bean_overrides=overrides
            )

    def test_min_exceeds_max_raises(self):
        defaults = [FakeMethodDefault("temperature", min_value=85.0, max_value=100.0)]
        brewer = FakeBrewer(temp_min=95.0, temp_max=96.0)
        overrides = [FakeBeanOverride("temperature", min_value=97.0)]

        with pytest.raises(ValueError, match="temperature"):
            compute_effective_ranges(
                defaults, brewer=brewer, grinder=None, bean_overrides=overrides
            )

    def test_grind_setting_invalid_after_override(self):
        grinder = FakeGrinder(ring_sizes_json=json.dumps([[0, 40, 1]]))
        overrides = [FakeBeanOverride("grind_setting", min_value=45.0, max_value=50.0)]

        # min=45 > grinder max=40, so effective_min=45, effective_max=40 => invalid
        with pytest.raises(ValueError, match="grind_setting"):
            compute_effective_ranges(
                [], brewer=None, grinder=grinder, bean_overrides=overrides
            )


# ---------------------------------------------------------------------------
# 10. Categorical parameter → allowed_values passed through
# ---------------------------------------------------------------------------


class TestCategoricalParameter:
    """Categorical parameters pass through allowed_values, no min/max."""

    def test_categorical_pass_through(self):
        defaults = [
            FakeMethodDefault(
                "grind_type",
                allowed_values='["fine", "medium", "coarse"]',
            ),
        ]

        result = compute_effective_ranges(defaults, brewer=None, grinder=None, bean_overrides=[])

        assert len(result) == 1
        r = result[0]
        assert r.parameter_name == "grind_type"
        assert r.min_value is None
        assert r.max_value is None
        assert r.allowed_values == '["fine", "medium", "coarse"]'
        assert r.source == "method_default"

    def test_categorical_with_brewer_still_passes_through(self):
        defaults = [
            FakeMethodDefault(
                "stop_mode",
                allowed_values='["time", "weight", "volume"]',
            ),
        ]
        brewer = FakeBrewer()

        result = compute_effective_ranges(defaults, brewer=brewer, grinder=None, bean_overrides=[])

        r = result[0]
        assert r.allowed_values == '["time", "weight", "volume"]'
        assert r.source == "method_default"

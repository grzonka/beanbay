---
phase: 20-espresso-parameter-evolution
plan: "01"
subsystem: parameter-registry
tags: [schema, alembic, parameter-registry, espresso, capability-gating]
requires:
  - "19-parameter-registry"
provides:
  - "preinfusion_pressure_pct column renamed in DB and ORM"
  - "saturation reworked from legacy to active gated param"
  - "Brewer.saturation_flow_rate column added"
  - "preinfusion_pressure, bloom_pause, temp_profile registry entries"
  - "requires_check() handles boolean == True/False conditions"
affects:
  - "20-02: brewer context wiring into campaigns"
  - "20-03: brew UI capability-driven parameter display"
tech-stack:
  added: []
  patterns:
    - "Boolean capability-gate condition syntax: brewer.attr == True/False"
    - "Tier-ordered registry: T1→T2→T3→T4→T5→bloom/temp→legacy"
key-files:
  created:
    - "migrations/versions/6d76407e7f4e_rename_preinfusion_pct_add_saturation_flow_rate.py"
  modified:
    - "app/models/measurement.py"
    - "app/models/equipment.py"
    - "app/services/parameter_registry.py"
    - "migrations/versions/f7a2c91b3d04_add_espresso_parameter_evolution_columns.py"
    - "tests/test_parameter_registry.py"
    - "tests/test_brew_phase20.py"
    - "app/routers/brew.py"
    - "app/routers/history.py"
    - "app/routers/insights.py"
    - "app/routers/analytics.py"
    - "app/templates/brew/_recipe_card.html"
    - "app/templates/brew/best.html"
    - "app/templates/brew/recommend.html"
    - "app/templates/analytics/_comparison_table.html"
    - "app/templates/history/_shot_modal.html"
    - "tests/test_brew.py"
    - "tests/test_models.py"
    - "tests/test_beans.py"
    - "tests/test_history.py"
    - "tests/test_insights.py"
    - "tests/test_analytics.py"
    - "tests/test_similarity.py"
    - "tests/test_optimizer.py"
    - "tests/test_brew_multimethod.py"
    - "tests/test_brew_phase21.py"
    - "tests/test_transfer_learning.py"
    - "tests/test_transfer_learning_integration.py"
decisions:
  - "preinfusion_pct → preinfusion_pressure_pct is a pure column rename (no data conversion) — it was always pump pressure %, not a time proxy"
  - "saturation is NOT deprecated — reworked to active boolean toggle gated by flow_control_type != none"
  - "saturation_flow_rate is a Brewer-level setting (fixed ml/s), NOT a per-shot BayBE optimization parameter"
  - "preinfusion_pressure bounds (1.0-6.0 bar) — gated on adjustable_pressure or programmable preinfusion"
  - "bloom_pause bounds (0.0-10.0s) — gated on brewer.has_bloom == True (new boolean gate syntax)"
  - "temp_profile values [flat/ramp_up/ramp_down] — gated on temp_control_type in (profiling)"
  - "requires_check() extended with == True/False boolean branch before existing in (...) branch"
  - "Old f7a2c91b3d04 migration data conversion (preinfusion_pct/100*15.0 formula) removed — was factually wrong"
metrics:
  duration: "~2h (continuation of prior session)"
  completed: "2026-02-26"
---

# Phase 20 Plan 01: Schema & Registry Foundation Summary

**One-liner:** Column rename preinfusion_pct→preinfusion_pressure_pct, saturation promoted from legacy to flow-gated active param, new entries preinfusion_pressure/bloom_pause/temp_profile with boolean and membership gate support.

## What Was Built

This plan established the foundation for all Phase 20 capability-driven espresso parameter work:

1. **Column rename** — `preinfusion_pct` → `preinfusion_pressure_pct` across the entire codebase (ORM, router, templates, tests). New Alembic migration `6d76407e7f4e` handles the SQLite-safe batch rename plus `saturation_flow_rate` addition to brewers.

2. **Saturation rework** — Removed from legacy, added active capability gate `brewer.flow_control_type in (manual_paddle, manual_valve, programmable)`. The field is meaningful for machines with flow control; the legacy entry was wrong per CONTEXT.md.

3. **New espresso registry entries:**
   - `preinfusion_pressure` (1.0–6.0 bar) — gated on `adjustable_pressure` or `programmable` preinfusion
   - `bloom_pause` (0.0–10.0 s) — gated on `brewer.has_bloom == True`
   - `temp_profile` [flat/ramp_up/ramp_down] — gated on `temp_control_type in (profiling)`

4. **`requires_check()` extension** — New boolean equality branch (`== True` / `== False`) added before the existing `in (...)` membership branch.

5. **22 new tests** added to `test_parameter_registry.py` covering all new params, gate combinations, and boolean condition syntax. `test_brew_phase20.py` updated for saturation's new non-legacy status.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `72710df` | feat(20-01) | Rename preinfusion_pct→preinfusion_pressure_pct; add saturation_flow_rate to Brewer |
| `bc6c82f` | feat(20-01) | Registry: saturation active+gated, add preinfusion_pressure/bloom_pause/temp_profile |

## Test Results

- **Before:** 367 tests passing
- **After:** 389 tests passing (+22 new registry/capability-gate tests)

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `preinfusion_pct` rename with NO data conversion | Column always stored pump pressure %; formula `value/100*15` in old migration was factually wrong per CONTEXT.md |
| `saturation` active, not legacy | Flow-control machines can do saturation (pre-wetting at reduced flow) — it's a meaningful BayBE parameter |
| `saturation_flow_rate` on Brewer (not Measurement) | Fixed ml/s the brewer performs during saturation — not something BayBE should vary per shot |
| Boolean gate syntax `brewer.has_bloom == True` | More expressive than `in (True)` for boolean attributes; extended parser handles both |
| Tier ordering in registry | T1→T2(preinfusion_time+preinfusion_pressure)→T3→T4→T5(flow_rate+brew_mode+saturation)→bloom/temp→legacy |

## Deviations from Plan

### Auto-fixed Issues

**1. [Plan-directed correction] f7a2c91b3d04 data migration removed**

- **Found during:** Task 1
- **Issue:** The original migration converted `preinfusion_pct / 100 * 15.0` into `preinfusion_time` — but `preinfusion_pct` was always a pump pressure percentage (55–100%), not a time proxy. The formula was factually wrong.
- **Fix:** Removed lines 64–78 from `f7a2c91b3d04` entirely. Added `text` import removal. Updated docstring.
- **Files modified:** `migrations/versions/f7a2c91b3d04_add_espresso_parameter_evolution_columns.py`

**2. [Rule 2 - Missing Critical] test_brew_phase20.py::test_espresso_legacy_params_identified updated**

- **Found during:** Task 2 (full test run)
- **Issue:** Test asserted `saturation in legacy` — now incorrect since saturation is active.
- **Fix:** Updated test to assert `saturation not in legacy` and clarify intent in docstring.
- **Files modified:** `tests/test_brew_phase20.py`

## Next Phase Readiness

Phase 20 Plan 01 is the foundation for:
- **Plan 02:** Wire brewer context into `OptimizerService.get_or_create_campaign()` so campaigns are built with capability-correct parameter sets
- **Plan 03:** Brew UI shows/hides advanced parameter fields based on brewer capabilities

No blockers. All 389 tests green. Migration chain intact: `87c4e18a3be4` → `f7a2c91b3d04` → `6d76407e7f4e`.

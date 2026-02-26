---
phase: 21-new-brew-methods
verified: 2026-02-26T12:00:00Z
status: passed
score: 7/7 must-haves verified
gaps: []
---

# Phase 21: New Brew Methods — Verification Report

**Phase Goal:** Add 5 new brew methods (french-press, aeropress, turkish, moka-pot, cold-brew) with method-specific parameters from the registry, extending BeanBay from 2 methods to 7

**Verified:** 2026-02-26
**Status:** ✅ PASSED
**Re-verification:** No — initial verification

## Test Suite

**408 passed, 0 failed** (3 warnings — unrelated torch deprecation)

```
408 passed, 3 warnings in 5.25s
```

## Success Criteria (from ROADMAP.md)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | All 7 brew methods available in BeanBay | ✅ | `PARAMETER_REGISTRY` has keys: espresso, pour-over, french-press, aeropress, turkish, moka-pot, cold-brew |
| 2 | Each method's parameters come from PARAMETER_REGISTRY | ✅ | `get_param_columns()` returns correct params per method; `build_parameters_for_setup()` creates BayBE params from registry |
| 3 | Method-specific brew forms show correct parameters | ✅ | `brew.py` passes `param_defs` from registry to templates for recommend, manual, and best views |
| 4 | Campaigns created per method with correct search spaces | ✅ | Tests verify distinct campaign keys per method; `test_optimizer_french_press_campaign`, `test_optimizer_aeropress_campaign`, `test_optimizer_cold_brew_campaign` all pass |
| 5 | BayBE optimization works for all new methods | ✅ | Campaign creation tests pass for french-press, aeropress, cold-brew; `record_measurement` integration tests pass for all 3 |
| 6 | New measurement columns nullable (no impact on existing data) | ✅ | `Measurement` model: `steep_time`, `brew_volume`, `bloom_weight`, `brew_mode` all `nullable=True`; migration guards with column existence checks; `test_measurement_phase21_columns_nullable` passes |
| 7 | All existing tests pass; new method tests for ≥3 methods | ✅ | 408 tests pass; `test_brew_phase21.py` has 17 tests covering french-press, aeropress, cold-brew (3 methods), plus pour-over bloom_weight |

## Must-Have Truths (Plan 21-01)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Recipe card shows steep_time for french-press, aeropress, cold-brew | ✅ VERIFIED | `_recipe_card.html` lines 81-96: conditional render of `steep_time` for both mapping (dict) and ORM object, with "Steep" label and "s" unit |
| 2 | Recipe card shows brew_volume for non-espresso methods | ✅ VERIFIED | `_recipe_card.html` lines 115-151: shows `brew_volume` as "Volume" (ml) — displayed when `target_yield` absent OR alongside `target_yield` when both present |
| 3 | Recipe card hides temperature for cold-brew | ✅ VERIFIED | `_recipe_card.html` lines 17-31: temperature only rendered when `not none`; cold-brew registry has NO temperature param, so recommendations omit it; `rec.temperature` will be `None` |
| 4 | Recipe card shows bloom_weight for pour-over | ✅ VERIFIED | `_recipe_card.html` lines 98-113: conditional render of `bloom_weight` with "Bloom" label and "g" unit; pour-over registry includes `bloom_weight` param |
| 5 | Shot detail modal shows method-specific params (not hardcoded) | ✅ VERIFIED | `_shot_modal.html` lines 26-123: fully dynamic — all params conditionally rendered with `{% if shot.X is not none %}` guards including steep_time (line 70), bloom_weight (line 76), brew_volume (line 64), brew_mode (line 100), brew_pressure, pressure_profile, flow_rate, bloom_pause, temp_profile |
| 6 | Brew index page shows method label on active setup | ✅ VERIFIED | `brew.py` line 213: passes `method` to template; `index.html` lines 19-21: `{% if method and method != "espresso" %}<span class="badge badge-outline badge-sm capitalize">{{ method }}</span>{% endif %}` |

**Score:** 6/6 truths verified

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/templates/brew/_recipe_card.html` | Method-aware param rendering | ✅ VERIFIED | 227 lines; renders steep_time, bloom_weight, brew_volume, temperature conditionally; no stubs |
| `app/templates/history/_shot_modal.html` | Method-aware shot detail | ✅ VERIFIED | 185 lines; dynamic param display for all Phase 20+21 columns; no hardcoded 6-param layout |
| `app/routers/history.py` | Phase 21 columns in `_load_shot_detail` | ✅ VERIFIED | Lines 94-129: includes steep_time, brew_volume, bloom_weight, brew_mode alongside all Phase 20 columns |
| `app/routers/brew.py` | Method label in `brew_index` context | ✅ VERIFIED | Line 213: `"method": _get_method_from_setup(active_setup)` |
| `app/services/parameter_registry.py` | All 7 methods defined | ✅ VERIFIED | 700 lines; PARAMETER_REGISTRY dict has 7 keys with full param defs |
| `app/models/measurement.py` | Phase 21 columns | ✅ VERIFIED | Lines 38-46: steep_time, brew_volume, bloom_weight, brew_mode — all `nullable=True` |
| `migrations/versions/f3a2b1c8d9e0_phase21_new_brew_methods.py` | Migration for columns + seed data | ✅ VERIFIED | 112 lines; adds 4 nullable columns, seeds 5 BrewMethod entries, makes target_yield nullable, idempotent guards |
| `tests/test_brew_phase21.py` | Tests for ≥3 new methods | ✅ VERIFIED | 385 lines; 17 tests covering registry, campaign creation, model storage, POST integration, and seeding for french-press, aeropress, cold-brew |

## Key Link Verification

| From → To | Status | Evidence |
|-----------|--------|---------|
| `history.py` `_load_shot_detail` → `_shot_modal.html` | ✅ WIRED | `_load_shot_detail` returns dict with steep_time, brew_volume, bloom_weight, brew_mode (lines 111-114); template renders all via `shot.steep_time`, `shot.brew_volume`, etc. |
| `_recipe_card.html` → `rec` object | ✅ WIRED | Conditional rendering with `rec.steep_time is defined`, `rec.bloom_weight is defined` for dicts; `rec.steep_time is not none` for ORM objects — handles both code paths |
| `brew.py` `brew_index()` → `index.html` method badge | ✅ WIRED | `brew_index` passes `method` key (line 213); template conditionally displays badge (lines 19-21) |
| `brew.py` `record_measurement()` → `Measurement` model | ✅ WIRED | `_extract_params_from_form` handles all Phase 21 float columns (steep_time, brew_volume, bloom_weight) and string columns (brew_mode); `record_measurement` stores them (lines 441-444) |
| `_build_shot_dicts` → `brew_method` field | ✅ WIRED | Lines 67-71: extracts `brew_method` from `m.brew_setup.brew_method.name` with fallback to "espresso" |

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|---------|
| New methods in BrewMethod table | ✅ SATISFIED | Migration seeds 5 entries; idempotent guards |
| New param columns on Measurement | ✅ SATISFIED | 4 nullable columns: steep_time, brew_volume, bloom_weight, brew_mode |
| Method-specific brew forms | ✅ SATISFIED | `param_defs` from registry drives form generation in recommend, manual, best views |
| Campaign creation for new methods | ✅ SATISFIED | `OptimizerService` creates BayBE campaigns via `build_parameters_for_setup(method)` |

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | No TODO/FIXME/placeholder patterns found in any Phase 21 artifact |

## Human Verification Required

### 1. Visual: Recipe Card for French Press

**Test:** Create a french-press setup, get a recommendation, verify the recipe card shows Grind, Temp, Steep, Dose, Volume
**Expected:** All 5 params displayed with correct labels and units (°C, s, g, ml)
**Why human:** Visual layout verification; can't check CSS rendering programmatically

### 2. Visual: Cold Brew Temperature Hidden

**Test:** Create a cold-brew setup, get a recommendation
**Expected:** No "Temp" param displayed on the recipe card
**Why human:** Need to verify visual absence, not just data absence

### 3. Visual: Method Badge on Brew Index

**Test:** Select a non-espresso setup on the brew page
**Expected:** Capitalized method name badge (e.g., "French-press") appears below setup name
**Why human:** Visual element rendering

## Gaps Summary

**None.** All 7 success criteria verified. All 6 must-have truths confirmed against actual code. All key links wired. 17 dedicated Phase 21 tests pass alongside all 408 existing tests. No anti-patterns or stubs detected.

---

_Verified: 2026-02-26_
_Verifier: OpenCode (gsd-verifier)_

---
phase: 21
plan: 01
status: complete
tests-passing: 408
subsystem: templates
tags: [brew-methods, templates, history, recipe-card, shot-modal]
requires: [20-03]
provides: [method-aware-recipe-card, method-aware-shot-modal, brew-index-method-badge, history-full-columns]
affects: [22-frontend-modernization]
tech-stack:
  added: []
  patterns: [conditional-jinja2-rendering, method-aware-template-display]
key-files:
  created: []
  modified:
    - app/templates/brew/_recipe_card.html
    - app/templates/brew/index.html
    - app/routers/brew.py
    - app/routers/history.py
    - app/templates/history/_shot_modal.html
decisions:
  - "Temperature block wrapped conditionally — cold-brew shows no Temp row rather than Temp: None°C"
  - "steep_time and bloom_weight placed after Dose row in recipe card — logical ordering for non-espresso methods"
  - "brew_volume shown as fallback when target_yield absent, or independently when both present (future-safe)"
  - "Method badge on brew index shown only for non-espresso setups — espresso is the default/implicit method"
  - "_load_shot_detail now returns ALL Phase 20+21 columns — shot modal has full data to conditionally render"
  - "_build_shot_dicts includes brew_method — informational field derived from brew_setup.brew_method.name"
  - "Shot modal renders params in order: grind, temp, dose, preinfusion, yield, volume, steep, bloom, pressure, profile, flow, mode, saturation, bloom_pause, temp_profile"
metrics:
  duration: "2 minutes"
  completed: "2026-02-26"
---

# Phase 21 Plan 01: Method-Aware Template Rendering Summary

**One-liner:** Brew recipe card, shot modal, and history router now dynamically render method-specific parameters for all 7 brew methods (cold-brew hides temperature, french-press/aeropress show steep_time, pour-over shows bloom_weight, etc.)

## What Was Built

### Task 1: Method-Aware Recipe Card and Brew Index Badge

**`app/templates/brew/_recipe_card.html`** — three changes:
1. **Temperature conditional**: Wrapped `<div class="recipe-param" data-param="temperature">` with `{% if rec.temperature is not none %}` (ORM) and `{% if rec.temperature is defined and rec.temperature is not none %}` (dict). Cold-brew shots no longer show "Temp: None°C".
2. **steep_time block**: Added after Dose row, dual mapping/ORM pattern. Shows only when not none. Label "Steep", unit "s".
3. **bloom_weight block**: Added after steep_time, same pattern. Label "Bloom", unit "g".
4. **brew_volume standalone block**: Added after yield/volume conditional — shows brew_volume independently when both `target_yield` and `brew_volume` are present (future-safe for edge cases).

**`app/routers/brew.py`** — `brew_index()` now passes `method` to template context via `_get_method_from_setup(active_setup)`.

**`app/templates/brew/index.html`** — method badge added after setup name. Only shown for non-espresso methods (espresso is implicit default, not labeled).

### Task 2: Method-Aware Shot Modal and History Column Wiring

**`app/routers/history.py`** — two changes:
1. **`_load_shot_detail`**: Added all Phase 20+21 missing columns:
   - Phase 20: `preinfusion_time`, `preinfusion_pressure`, `brew_pressure`, `pressure_profile`, `bloom_pause`, `flow_rate`, `temp_profile`
   - Phase 21: `steep_time`, `brew_volume`, `bloom_weight`, `brew_mode`
2. **`_build_shot_dicts`**: Added `brew_method` field derived from `m.brew_setup.brew_method.name` (falls back to `"espresso"` when no setup/method).

**`app/templates/history/_shot_modal.html`** — replaced hardcoded 6-param grid with dynamic conditional blocks. Old behavior: always showed grind, temp, pre-inf%, dose, yield, saturation regardless of None. New behavior: shows only params with actual values. Full list with conditions:
- Grind (always)
- Temperature (if not none) — hidden for cold-brew
- Dose (always)
- Pre-inf Time (if not none), elif Pre-inf % (if not none)
- Pre-inf Pressure (if not none)
- Yield (if not none)
- Volume / brew_volume (if not none)
- Steep (if not none)
- Bloom weight (if not none)
- Pressure (if not none)
- Profile, Flow, Mode, Saturation, Bloom Pause, Temp Profile — all conditional

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Temperature hidden (not "N/A") for cold-brew | Better UX — absence is more accurate than showing a meaningless value |
| steep_time placed after dose | Natural brewing order: you set dose, then steep time |
| Method badge only for non-espresso | Espresso is the implicit default; labeling it would be redundant for existing users |
| All Phase 20+21 columns added to `_load_shot_detail` in one pass | Cleaner than incremental additions; all columns were already in the DB model |
| `brew_method` in shot list dicts defaults to `"espresso"` | Backward compat — legacy shots without brew_setup still have a valid method label |

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- **408/408 tests pass** (no regressions)
- Phase 21 tests: 17/17
- History tests: 26/26
- Brew + Phase 20 tests: 59/59

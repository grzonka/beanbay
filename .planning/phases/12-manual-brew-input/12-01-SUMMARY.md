---
phase: 12
plan: "01"
name: "Manual Brew Foundation"
subsystem: "brew"
tags: ["brew", "is_manual", "alembic", "migration", "validation", "bean-picker"]

depends_on:
  requires: ["11-01", "11-02"]
  provides: ["is_manual column", "bean picker on brew page", "Manual Input button", "manual brew bounds validation"]
  affects: ["12-02 (manual brew form)", "12-03 (repeat best + manual integration)"]

tech-stack:
  added: []
  patterns: ["form-based bean switching via POST /beans/set-active", "server-side bounds validation for manual brews"]

key-files:
  created:
    - "migrations/versions/c06d948aa2d7_add_is_manual_to_measurements.py"
  modified:
    - "app/models/measurement.py"
    - "app/routers/brew.py"
    - "app/routers/beans.py"
    - "app/templates/brew/index.html"
    - "tests/test_brew.py"

decisions:
  - id: "12-01-A"
    decision: "Add POST /beans/set-active endpoint for bean picker form"
    rationale: "Existing /beans/{id}/activate requires bean_id in path; a form <select> submits a body field. New endpoint accepts bean_id as Form field and redirects back to /brew."
  - id: "12-01-B"
    decision: "Bean picker uses onchange=this.form.submit() (no JS framework)"
    rationale: "Simplest approach — native form submit on select change. Consistent with rest of app's progressive enhancement approach."
  - id: "12-01-C"
    decision: "Bounds validation only applies when is_manual == 'true'"
    rationale: "Optimizer-generated recommendations are always within bounds by construction. Manual input may stray out-of-range so validation is opt-in via flag."

metrics:
  duration: "~25 minutes"
  completed: "2026-02-22"
---

# Phase 12 Plan 01: Manual Brew Foundation Summary

**One-liner:** Added `is_manual` DB column + Alembic migration, bean picker dropdown, Manual Input button, and server-side bounds validation for manual brews.

## What Was Built

### Task 1 — is_manual model + migration
- Added `is_manual = Column(Boolean, nullable=True, default=False)` to `Measurement` model (after `is_failed`)
- Created Alembic migration `c06d948aa2d7` with `server_default=sa.text('0')`
- Applied migration against existing DB (stamped `e192b884d9c6` first as DB had no Alembic version row)

### Task 2 — brew page restructure + validation
- Rewrote `brew/index.html`: added bean picker `<select>` (submits to `/beans/set-active`) and **Manual Input** button linking to `/brew/manual`
- Added `POST /beans/set-active` endpoint in `beans.py` — accepts `bean_id` as form field, sets cookie, redirects to `/brew`
- Added `is_manual: Optional[str] = Form(None)` to `record_measurement`
- When `is_manual == "true"`: calls `_resolve_bounds(bean.parameter_overrides)`, checks all 5 continuous params, returns `JSONResponse(422)` with violations list if any out of range
- Sets `is_manual=(is_manual == "true")` on `Measurement` creation
- Added 5 new tests (all passing): bean picker presence, Manual Input button, is_manual saved, 422 on out-of-range, non-manual bypass

## Tests Added

| Test | Assertion |
|------|-----------|
| `test_brew_index_shows_manual_input_button` | GET /brew → "Manual Input" + "/brew/manual" in HTML |
| `test_brew_index_shows_bean_picker` | GET /brew → `<select` + active bean name in HTML |
| `test_record_manual_measurement` | POST with `is_manual=true` → `m.is_manual is True` |
| `test_record_manual_rejects_out_of_range` | `is_manual=true` + `grind_setting=5.0` → 422 + violations |
| `test_record_non_manual_allows_any_values` | no `is_manual` + `grind_setting=5.0` → 303 + saved |

**Total tests:** 29 (was 24, added 5) — all pass.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 12-01-A | New `POST /beans/set-active` endpoint | Form `<select>` needs body-based bean_id; existing activate route uses path param |
| 12-01-B | `onchange=this.form.submit()` on bean picker | Simplest native approach, no JS framework needed |
| 12-01-C | Bounds validation only for `is_manual == "true"` | Optimizer recs are always in-bounds; only manual entries need validation |

## Deviations from Plan

### Auto-added functionality

**1. [Rule 3 - Blocking] Added `POST /beans/set-active` endpoint in `beans.py`**

- **Found during:** Task 2 (template implementation)
- **Issue:** The brew page bean picker `<form>` submits `bean_id` as a POST body field. No existing route accepts this — only `POST /beans/{bean_id}/activate` exists (path param). Without a body-based route, the form couldn't function.
- **Fix:** Added `POST /beans/set-active` to `beans.py` — accepts `bean_id: str = Form(...)`, sets the `active_bean_id` cookie (same logic as activate), redirects to `/brew`.
- **Files modified:** `app/routers/beans.py`
- **Commit:** `0493246`

## Next Phase Readiness

**Phase 12-02 (Manual Brew Form at `/brew/manual`):**
- ✅ `is_manual` column exists in DB and model
- ✅ `POST /brew/record` accepts and persists `is_manual`
- ✅ Bounds validation in place for manual submissions
- ✅ Manual Input button on brew index links to `/brew/manual`
- The `/brew/manual` route and form template still need to be created in 12-02

---
phase: "07"
plan: "02"
name: "tech-debt-cleanup"
subsystem: "core-routing"
tags: [deduplication, persistence, alembic, error-handling, migrations]

dependency-graph:
  requires:
    - "07-01: rebrand-rename (BeanBay naming in place)"
  provides:
    - "File-persisted pending recommendations"
    - "Alembic migration for flavor_tags"
    - "Visible override validation errors"
    - "Single canonical _get_active_bean"
  affects:
    - "08: documentation (tech debt section now resolved)"
    - "09: deployment (clean migration chain for prod)"

tech-stack:
  added: []
  patterns:
    - "File-backed JSON store for cross-restart state"
    - "Alembic for all schema changes (no startup DDL)"
    - "422 TemplateResponse for form validation errors"

key-files:
  created:
    - migrations/versions/e192b884d9c6_add_flavor_tags_to_measurements.py
  modified:
    - app/routers/brew.py
    - app/routers/beans.py
    - app/main.py
    - app/templates/beans/detail.html

decisions:
  - "File-based pending store uses data_dir/pending_recommendations.json (same dir as campaigns)"
  - "show_recommendation checks in-memory first, then falls back to file (graceful for warm restarts)"
  - "update_overrides returns 422 TemplateResponse (not redirect) so form values are preserved on error"
  - "Removed inline HTMLResponse import from beans.py (was redundant — HTMLResponse already in scope via response_class)"

metrics:
  duration: "~30 minutes"
  completed: "2026-02-22"
  tasks-completed: 2
  tests-before: 108
  tests-after: 108
---

# Phase 7 Plan 02: Tech Debt Cleanup Summary

**One-liner:** Eliminated 5 v1 tech debt items — deduped helper, deleted dead dir, file-persisted pending recs, Alembic migration for flavor_tags, and visible override validation errors.

## What Was Built

All 5 items from the v1 audit tech debt list are resolved:

1. **Deduplication of `_get_active_bean`** — removed duplicate definitions from `brew.py` and `insights.py`; both now import from `beans.py` (the canonical location).
2. **Dead `app/routes/` directory removed** — the empty `__init__.py` and directory are gone.
3. **Persistent pending recommendations** — added `_save_pending` / `_load_pending` / `_remove_pending` helpers in `brew.py` backed by `data_dir/pending_recommendations.json`. `show_recommendation` falls back to disk if not in memory. `record_measurement` removes from both.
4. **Alembic migration for `flavor_tags`** — created `e192b884d9c6_add_flavor_tags_to_measurements.py`; removed the startup `ALTER TABLE` block from `main.py`.
5. **Override error surfacing** — `update_overrides` now collects invalid params and returns a 422 `TemplateResponse` with an `error` context variable. `detail.html` renders the error above the Custom Ranges collapsible.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| File store in `data_dir` (not a new DB table) | Minimal complexity; pending recs are short-lived; same directory already used for BayBE campaigns |
| In-memory check first, then disk fallback | Warm restarts don't need a disk read for every view |
| 422 TemplateResponse (not redirect) on override error | Preserves user's form input; standard HTTP semantics for validation failure |
| `down_revision = "a2f1c3d5e7b9"` | Chains onto the existing initial migration |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_beans.py health check assertion (Task 1)**

- **Found during:** Task 1 verification
- **Issue:** `test_beans.py:313` asserted `"service": "brewflow"` but `main.py` already emits `"service": "beanbay"` (from plan 07-01)
- **Fix:** Updated assertion to `"beanbay"`
- **Files modified:** `tests/test_beans.py`
- **Commit:** `1a94d89`

**2. [Rule 2 - Missing Critical] Added error display to detail.html (Task 2)**

- **Found during:** Task 2 implementation
- **Issue:** `update_overrides` passed `error` context variable to template but template had no `{{ error }}` rendering block — users would see no feedback
- **Fix:** Added `{% if error %}` paragraph above Custom Ranges collapsible in `detail.html`
- **Files modified:** `app/templates/beans/detail.html`
- **Commit:** `8fac0ca`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `1a94d89` | `refactor(07-02): deduplicate _get_active_bean and remove dead directory` |
| 2 | `8fac0ca` | `fix(07-02): persist pending recs, add Alembic migration, surface override errors` |

## Test Results

- **Before:** 108/108 passing
- **After:** 108/108 passing
- No new tests added (all changes covered by existing integration tests)

## Next Phase Readiness

Phase 7 is complete. Phase 8 (Documentation & Release) can proceed:
- Tech debt list from v1 audit: fully resolved ✓
- BeanBay rename: complete (07-01) ✓
- Migration chain: clean ✓
- No blockers for documentation/release work

---
phase: 12
plan: 03
subsystem: history-ui
tags: [history, badge, batch-delete, baybe, htmx, css]

dependency-graph:
  requires: ["12-01", "12-02"]
  provides: ["manual-badge-history", "batch-delete-endpoint"]
  affects: ["12-04"]

tech-stack:
  added: []
  patterns: ["delete-mode-toggle", "form-link-via-form-attribute", "oob-swap-preservation"]

key-files:
  created: []
  modified:
    - app/routers/history.py
    - app/templates/history/_shot_row.html
    - app/templates/history/_shot_modal.html
    - app/templates/history/index.html
    - app/static/css/main.css
    - tests/test_history.py

decisions:
  - id: D1
    decision: "Capture shot IDs before DB delete in tests"
    rationale: "SQLAlchemy raises ObjectDeletedError when accessing attributes of deleted instances after expire_all(); save IDs before the delete call"
  - id: D2
    decision: "Delete checkbox uses form attribute to link to external form"
    rationale: "Checkbox is inside shot row card (not inside the form element); HTML form attribute links input to any form by ID regardless of DOM nesting"
  - id: D3
    decision: "Hardcode #3b82f6 for badge-manual (no --info CSS variable)"
    rationale: "--info is not defined in :root; hardcoded blue matches the plan spec and avoids adding a variable that has no other uses"

metrics:
  duration: "~3 minutes"
  completed: "2026-02-22"
---

# Phase 12 Plan 03: Manual Badge + Batch Delete Summary

**One-liner:** Manual badge (blue #3b82f6) on history rows/modal surfaces `is_manual` field; batch delete via `POST /history/delete-batch` removes measurements and rebuilds BayBE campaigns for affected beans.

## What Was Built

### Task 1: Manual badge in history rows and modal
- Added `"is_manual": getattr(m, "is_manual", False) or False` to `_build_shot_dicts`, `_load_shot_detail`, and `row_shot` dict in `shot_edit_save`
- Added `{% if shot.is_manual %}<span class="badge badge-manual">Manual</span>{% endif %}` to `_shot_row.html` (before Failed badge) and `_shot_modal.html` (after taste score, before Failed badge)
- Added `.badge-manual` CSS class with `background: #3b82f6; color: white` matching `.badge-failed` pattern
- Updated `_seed_shot` helper to accept `is_manual: bool = False`
- Added 3 new tests: shows badge in list, hidden for regular brews, shows badge in modal

### Task 2: Batch delete with campaign rebuild
- Added delete mode toggle button (`🗑️ Delete`) in history page header
- Added hidden delete form with sticky action bar (selected count + Delete Selected + Cancel)
- Added delete checkbox per shot row using `form="delete-form"` attribute to link across DOM boundary
- Added `toggleDeleteMode()` and `updateDeleteCount()` JS functions in `index.html`
- Added `POST /history/delete-batch` endpoint:
  - Reads `shot_ids` from form data, redirects immediately if empty
  - Identifies affected bean IDs before deletion
  - Bulk-deletes measurements with `synchronize_session=False`
  - Rebuilds BayBE campaign for each affected bean (with remaining measurements or empty DataFrame)
- Added `RedirectResponse` import to `history.py`
- Added `.delete-check` and `.delete-action-bar` CSS classes
- Added 4 new tests: removes measurements, rebuilds campaign, empty → redirect, multiple beans → 2 rebuilds

## Test Results

- History tests: **26/26 passed** (was 19, added 7 new)
- Full suite: **126/126 passed**

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `7113000` | feat(12-03): Manual badge in history rows and modal |
| Task 2 | `37a48c4` | feat(12-03): Batch delete with campaign rebuild |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ObjectDeletedError in test assertion**

- **Found during:** Task 2 test execution
- **Issue:** `test_delete_batch_removes_measurements` accessed `shot1.id` after `db_session.expire_all()` — SQLAlchemy raises `ObjectDeletedError` since the row was deleted and can no longer be refreshed
- **Fix:** Captured `id1, id2, id3 = shot1.id, shot2.id, shot3.id` before the delete call; used captured ints for post-delete assertions
- **Files modified:** `tests/test_history.py`
- **Commit:** `37a48c4`

## Next Phase Readiness

- **12-04** can proceed: Manual badge and batch delete are complete and tested
- No blockers or concerns

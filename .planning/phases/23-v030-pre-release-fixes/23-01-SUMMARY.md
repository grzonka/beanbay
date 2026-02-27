---
phase: 23-v030-pre-release-fixes
plan: 01
subsystem: ui
tags: [htmx, jinja2, tailwind, daisyui, history, recipe-card, filtering]

requires:
  - phase: 22-frontend-modernization-daisyui
    provides: daisyUI component system, input.css @layer components pattern
  - phase: 14-equipment-management
    provides: BrewSetup model with is_retired boolean and name field
  - phase: 21-new-brew-methods
    provides: history filtering by bean_id and min_taste

provides:
  - History page filtering by brew setup (active/non-retired setups only)
  - Visible amber circular "i" badge replacing near-invisible SVG info icon on recipe cards

affects:
  - 23-v030-pre-release-fixes (sibling plans 02, 03)
  - Any future phase modifying history.py or _recipe_card.html

tech-stack:
  added: []
  patterns:
    - "htmx hx-include cross-filter: each dropdown includes sibling filter names to pass all active filters on partial reload"
    - "Jinja2 include inherits parent context: setups/filter_setup_id passed to history/index.html are visible in _filter_panel.html include without explicit passing"

key-files:
  created: []
  modified:
    - app/routers/history.py
    - app/templates/history/_filter_panel.html
    - app/templates/brew/_recipe_card.html
    - app/static/css/input.css
    - app/static/css/main.css

key-decisions:
  - "Setup dropdown queries active (non-retired) setups only — retired setups are hidden from filter UI"
  - "setup_id passed as Optional[str] through both history_page() and history_shots_partial() — consistent with existing bean_id and min_taste filter params"
  - "param-info-icon uses primary amber color (oklch 65% 0.122 54) — matches theme accent, clearly visible against dark recipe-label background"
  - "SVG replaced entirely rather than just removing opacity-40 — SVG path was also not ideal at 3.5×3.5 size; circular badge is cleaner"

patterns-established:
  - "param-info-icon: 14px amber circle badge pattern for inline tooltip indicators on recipe params"

duration: 25min
completed: 2026-02-26
---

# Phase 23 Plan 01: v0.3.0 Pre-Release Fixes (Part 1) Summary

**History page setup filtering and visible amber "i" badge replacing near-invisible SVG tooltip icons on recipe cards**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-02-26T22:00:00Z
- **Completed:** 2026-02-26T22:27:27Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- History page now has a three-way filter: Bean, Brew Setup, and Min Taste — all filters cooperate via htmx hx-include so changing one dropdown reloads shots respecting the others
- Recipe card info icons upgraded from 40%-opacity SVG (visually hidden) to a clear 14px amber circular "i" badge matching the app's primary color
- All 408 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add brew setup filtering to history page** - `73d2084` (feat)
2. **Task 2: Enhance recipe card info icons for better visibility** - `b77d209` (feat)

**Plan metadata:** _(committed with this SUMMARY)_

## Files Created/Modified
- `app/routers/history.py` — BrewSetup import, setup_id filter in `_build_shot_dicts()`, both history routes updated
- `app/templates/history/_filter_panel.html` — Added setup dropdown, updated hx-include on all three dropdowns
- `app/templates/brew/_recipe_card.html` — Replaced SVG icon with `<span class="param-info-icon">i</span>`
- `app/static/css/input.css` — Added `.param-info-icon` in `@layer components` (amber circle, 14px, italic bold "i")
- `app/static/css/main.css` — Rebuilt artifact

## Decisions Made
- **Active setups only in filter dropdown:** `BrewSetup.is_retired == False` filter ensures retired setups don't appear as filter options even if historical shots reference them
- **param-info-icon in primary amber:** Using `oklch(65% 0.122 54)` (same as `--color-primary`) makes the icon clearly visible and thematically consistent
- **SVG fully replaced:** The SVG `h-3.5 w-3.5 opacity-40` approach was both too faint and too small to read at any size; circular badge is more legible at the same 14px footprint

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- `python3` resolved to Python 3.14 (no pytest), `python3.12` (no pytest) — `.venv/bin/python` (Python 3.11) has pytest. Used `.venv/bin/python -m pytest` throughout.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Tasks 1 and 2 complete. Phase 23 has two more plans (23-02, 23-03) running in parallel.
- Plan 23-03 also modifies `app/static/css/input.css` — if there are merge conflicts on that file, re-apply changes in a new section.

---
*Phase: 23-v030-pre-release-fixes*
*Completed: 2026-02-26*

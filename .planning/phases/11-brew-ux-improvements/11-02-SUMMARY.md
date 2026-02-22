---
phase: 11-brew-ux-improvements
plan: 02
subsystem: ui
tags: [fastapi, jinja2, htmx, ux, brew-flow]

# Dependency graph
requires:
  - phase: 10-responsive-nav-layout
    provides: base layout structure that brew/index.html extends
provides:
  - "No-bean prompt on /brew: renders page with 'Pick a bean first' message + link to /beans instead of silent 303 redirect"
affects: [12-manual-brew-input]

# Tech tracking
tech-stack:
  added: []
  patterns: ["No-bean graceful degradation: render page with contextual prompt instead of redirect"]

key-files:
  created: []
  modified:
    - app/routers/brew.py
    - app/templates/brew/index.html
    - tests/test_brew.py

key-decisions:
  - "Render brew/index.html with no_active_bean=True flag instead of redirecting — keeps user on /brew with context"
  - "Other brew routes (recommend, record, best) still redirect because they genuinely cannot function without a bean"

patterns-established:
  - "no_active_bean flag pattern: route passes flag to template, template conditionally renders prompt vs content"

# Metrics
duration: 1min
completed: 2026-02-22
---

# Phase 11 Plan 02: No-Bean Prompt on /brew Summary

**`/brew` without an active bean now renders a "Pick a bean first" prompt with a link to `/beans` instead of silently redirecting (HTTP 200, not 303)**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-22T18:36:29Z
- **Completed:** 2026-02-22T18:37:45Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments

- `brew_index` GET handler renders `brew/index.html` with `no_active_bean=True` when no bean is active — no more silent redirect
- `brew/index.html` conditionally shows the "Pick a bean first" prompt (with link button to `/beans`) or the normal action buttons
- Test renamed `test_brew_index_no_active_bean_shows_prompt`: asserts 200 + "Pick a bean" text + "/beans" link present
- All other brew routes (POST /recommend, GET /best, POST /record) still redirect to `/beans` as they cannot function without a bean

## Task Commits

Each task was committed atomically:

1. **Task 1: No-bean prompt on /brew** — `1fa2d60` (feat)

**Plan metadata:** *(pending docs commit)*

## Files Created/Modified

- `app/routers/brew.py` — `brew_index` renders template with `no_active_bean` flag instead of redirecting
- `app/templates/brew/index.html` — Wraps action content in `{% if no_active_bean %}` / `{% else %}` conditional; no-bean block shows empty-state div with prompt and button link
- `tests/test_brew.py` — Renamed test, updated to assert 200 + "Pick a bean" + "/beans" in response

## Decisions Made

- Render the page (200) rather than redirect (303) so users understand where they are and what to do next — silent redirects are confusing on mobile
- Used existing `empty-state` + `empty-state-text` CSS classes for consistency with other empty states in the app
- Link styled as `.btn.btn-primary` to make the call-to-action visually prominent
- Other brew routes keep their redirects — they trigger BayBE operations or DB writes that require a bean, so failing silently would be worse than redirecting

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 11 plan 02 complete. Phase 11 plan 01 (inactive taste slider + submit gate) is independent and can be executed now.
- Phase 12 (Manual Brew Input) depends on Phase 11 being complete — the no-bean prompt pattern established here may be reused in Phase 12.

---
*Phase: 11-brew-ux-improvements*
*Completed: 2026-02-22*

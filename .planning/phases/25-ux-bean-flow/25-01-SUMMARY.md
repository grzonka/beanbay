---
phase: 25-ux-bean-flow
plan: 01
subsystem: ui
tags: [jinja2, htmx, tailwind, daisyui, fastapi, sqlalchemy, insights, sidebar]

# Dependency graph
requires:
  - phase: 24-home-dashboard
    provides: Home dashboard route and template
  - phase: 22-frontend-tailwind
    provides: Tailwind + daisyUI sidebar/layout established in base.html
provides:
  - Sidebar without active-bean indicator (navigation-only)
  - Dashboard intro message
  - Insights page with bean picker dropdown and bean_id query param support
affects: [25-02, analytics, history]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Bean picker via select onchange navigation (/insights?bean_id=)
    - Insights page degrades gracefully when no bean selected (no redirect)
    - Query param with cookie fallback for bean resolution

key-files:
  created: []
  modified:
    - app/templates/base.html
    - app/templates/home.html
    - app/routers/insights.py
    - app/templates/insights/index.html
    - tests/test_beans.py
    - tests/test_insights.py

key-decisions:
  - "Sidebar active-bean indicator removed entirely — it added noise without clear value; active_bean variable kept in route contexts for other uses (brew, dashboard)"
  - "Insights no longer redirects to /beans when no active bean — renders minimal page with picker prompt instead"
  - "bean_id query param takes precedence over cookie for insights; cookie is fallback; empty state is graceful"
  - "select onchange navigation pattern for bean picker — zero JavaScript dependency, simple and fast"

patterns-established:
  - "Bean picker: <select onchange=\"window.location.href='/route?bean_id=' + this.value\"> with option[selected] driven by template context"
  - "Graceful no-bean state: {% if active_bean %}...{% else %}<prompt>{% endif %} in insights template"

# Metrics
duration: 2min
completed: 2026-02-27
---

# Phase 25 Plan 01: Sidebar Cleanup + Insights Bean Picker Summary

**Sidebar stripped to nav-only, dashboard intro added, and insights page gets a bean picker dropdown that eliminates the redirect-to-/beans dead-end**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-26T23:18:58Z
- **Completed:** 2026-02-26T23:20:58Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Removed active-bean indicator block (divider + card with bean name + deactivate button) from sidebar; sidebar is now navigation-only
- Added a one-line intro paragraph to the dashboard below the heading
- Insights page accepts `bean_id` query param with cookie fallback; no longer redirects to `/beans` when no bean is set
- Bean picker `<select>` dropdown added to top of insights page; pre-selects the active bean when one is set via cookie
- When no bean is selected, insights renders a clean "Select a bean above" prompt instead of a redirect

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove active-bean from sidebar, add dashboard intro** - `e351872` (feat)
2. **Task 2: Add bean picker to insights page** - `b85183c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/templates/base.html` - Removed divider + active-bean-indicator block from sidebar
- `app/templates/home.html` - Added intro paragraph below Dashboard heading
- `app/routers/insights.py` - Added `bean_id: Optional[str]` query param, cookie fallback, beans list, graceful no-bean render
- `app/templates/insights/index.html` - Added bean picker select dropdown; wrapped content in `{% if active_bean %}` conditional
- `tests/test_beans.py` - Removed stale `assert "No bean selected" in response2.text` from `test_deactivate_bean`
- `tests/test_insights.py` - Updated `test_insights_requires_active_bean` to expect 200 not 303; added `test_insights_bean_id_query_param`

## Decisions Made
- **Sidebar active-bean indicator removed entirely:** It added visual noise and was the only place that showed the deactivate button — but deactivate is already on the bean detail page. The sidebar is cleaner as nav-only. `active_bean` variable kept in route contexts for brew page and dashboard.
- **Insights: no redirect, graceful empty state:** Redirecting users to `/beans` when they hit `/insights` without an active bean was a dead-end UX trap. Now the page renders immediately with the picker.
- **Query param takes precedence over cookie:** Explicit URL selection (`?bean_id=`) always wins over ambient cookie state. This enables bookmarking specific bean insights.
- **`select onchange` navigation:** No JavaScript dependency needed for the picker — native browser event fires URL navigation. Simple and accessible.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 25 Plan 02 (analytics per-bean filter + history filter visible) can proceed
- All 410 tests pass; no regressions introduced
- Sidebar is now stable for any future nav changes — no active-bean state to keep in sync

---
*Phase: 25-ux-bean-flow*
*Completed: 2026-02-27*

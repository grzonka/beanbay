---
phase: 24
plan: 01
name: dashboard-route-and-template
subsystem: frontend-routing
tags: [fastapi, jinja2, dashboard, routing, templates]

dependency-graph:
  requires: [23-02]  # welcome.html + root route conditional branching established here
  provides: [home-dashboard, root-route-renders-html]
  affects: []  # no future phases planned yet

tech-stack:
  added: []
  patterns: [dashboard-data-assembly-in-route, stats-grid-reuse]

key-files:
  created:
    - app/templates/home.html
  modified:
    - app/main.py
    - app/templates/base.html
    - tests/test_beans.py

decisions:
  - id: D1
    choice: Inline data assembly in main.py route
    rationale: No separate service layer warranted for a single dashboard; keeps complexity low
  - id: D2
    choice: Reuse existing .stats-grid CSS class for dashboard tiles
    rationale: Avoids adding new CSS; consistent visual language with analytics page
  - id: D3
    choice: Remove unused RedirectResponse import caught by ruff pre-commit hook
    rationale: Auto-fixed by ruff --fix; cleaner imports after redirect logic removed

metrics:
  duration: "multi-session (prior research + ~15 min completion)"
  completed: "2026-02-26"
---

# Phase 24 Plan 01: Dashboard Route and Template Summary

**One-liner:** Root `/` now renders a stats dashboard (brews, beans, avg/best taste, active bean, recent shots) instead of redirecting to `/beans`.

## What Was Built

The home route (`GET /`) was converted from a redirect to a proper dashboard page for returning users. When at least one bean exists, the route assembles dashboard data and renders `home.html`. The zero-bean case continues to show `welcome.html` unchanged.

### Route changes (`app/main.py`)

- Added imports: `from sqlalchemy import func`, `from app.routers.beans import _get_active_bean`
- Dashboard data assembled:
  - **`stats`**: `total_brews`, `total_beans`, `avg_taste` (1 dp), `best_taste` (1 dp), `best_bean_name`
  - **`recent_brews`**: last 5 non-failed measurements as dicts (bean name, taste, date, brew method)
  - **`active_bean`**: active bean dict with `shots` count and `best_taste` (via `_get_active_bean`)
  - **`setup_count`**: count of non-retired brew setups
- `RedirectResponse` import removed (now unused; caught by ruff pre-commit hook)

### Navigation fix (`app/templates/base.html`)

- Mobile navbar brand `<a href="/beans">` → `<a href="/">`
- Sidebar brand `<a href="/beans">` → `<a href="/">`

### Dashboard template (`app/templates/home.html`)

- **Stats grid**: 4 tiles using `.stats-grid` — Total Brews, Beans Tracked, Avg Taste, Best Taste (with bean name)
- **Active bean card**: name + "Active" badge, shot count, best taste score, "Let's Brew" CTA — or a "No bean selected" prompt with a link to beans page
- **Recent brews list**: up to 5 compact rows showing taste score, bean name, date, method badge — or an empty state prompt
- **Quick actions**: "Let's Brew" primary button, "Beans" + "Equipment" secondary grid

### Test update (`tests/test_beans.py`)

- `test_root_redirects_to_beans_when_beans_exist` → `test_root_shows_dashboard_when_beans_exist`
- Now asserts HTTP 200 and `"Dashboard"` in response text (previously 303 redirect to `/beans`)

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Inline data assembly in main.py route | No separate service warranted; keeps complexity low for a single dashboard view |
| D2 | Reuse existing `.stats-grid` CSS for dashboard tiles | Avoids new CSS; consistent with analytics page visual language |
| D3 | Remove `RedirectResponse` import | Flagged as unused by ruff pre-commit hook; auto-fixed before commit |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed unused `RedirectResponse` import**

- **Found during:** Task 1 commit attempt
- **Issue:** Pre-commit ruff hook rejected commit — `RedirectResponse` was imported but no longer used after redirect logic was removed
- **Fix:** `uv run ruff check --fix app/main.py` removed the import automatically
- **Files modified:** `app/main.py`
- **Commit:** 12e66fe (included in same commit after fix)

## Test Results

- **409 tests passed**, 0 failed, 3 warnings (pre-existing torch deprecation warnings)
- All new dashboard assertions pass

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 12e66fe | feat | dashboard route and data assembly |
| 65b799c | feat | home dashboard template |

## Next Phase Readiness

- No blockers for future phases
- Dashboard is a standalone feature; no downstream phase dependencies introduced
- The `.stats-grid` pattern is now used in two places (analytics + home) — if ever refactored, update both

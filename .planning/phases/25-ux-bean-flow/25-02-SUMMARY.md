---
phase: 25-ux-bean-flow
plan: "02"
subsystem: analytics-ux
tags: [analytics, history, filtering, htmx, jinja2, daisyui]

dependency-graph:
  requires: []
  provides:
    - analytics per-bean filter via bean_id query param
    - history filter panel always visible (not collapsed)
  affects:
    - future analytics enhancements (per-bean trend charts, etc.)

tech-stack:
  added: []
  patterns:
    - optional query param filter (bean_id) on analytics route
    - onchange window.location navigation for dropdown filter

key-files:
  created: []
  modified:
    - app/routers/analytics.py
    - app/templates/analytics/index.html
    - tests/test_analytics.py
    - app/templates/history/index.html

decisions:
  - id: D1
    decision: "Pass beans list + selected_bean_id + selected_bean to analytics template for dropdown and conditional heading"
    rationale: "Template needs the full list for <option> rendering, the ID for selected state, and the object for the bean name in the stats card heading"
  - id: D2
    decision: "Pass comparison=[] when bean_id is set (skip _compute_comparison call)"
    rationale: "Cross-bean comparison is meaningless when already filtered to one bean; avoids wasted DB work"
  - id: D3
    decision: "Dropdown uses onchange window.location navigation (not htmx)"
    rationale: "Full page reload is simplest — analytics page is not a partial, and the entire stats context changes on filter switch; no htmx target available for the whole content"
  - id: D4
    decision: "Per-bean empty state shown inside the {% else %} block (after the dropdown renders)"
    rationale: "Dropdown must be visible even when selected bean has zero shots — user needs to be able to switch back to All beans"
  - id: D5
    decision: "History filter card removes collapse entirely, not just pre-checks the checkbox"
    rationale: "Collapse-arrow always starts closed in daisyUI unless JS or checked attribute is pre-set; removing it is simpler and produces the desired always-visible behaviour"

metrics:
  duration: "~8 minutes"
  completed: "2026-02-27"
---

# Phase 25 Plan 02: Analytics Bean Filter + History Filter Visibility Summary

**One-liner:** Per-bean analytics filter via `?bean_id=` query param and always-visible history filter panel.

## What Was Built

### Task 1: Analytics per-bean filtering

**`app/routers/analytics.py`**
- Added `from typing import Optional`
- Extended `_compute_stats(db, bean_id=None)` — when `bean_id` is set, measurements are filtered to that bean; `total_beans` is hardcoded to 1; best bean name comes from the filtered bean
- Updated `analytics_page` route to accept optional `bean_id: Optional[str] = None` query param
- Route queries all beans (`Bean.order_by(name)`) for the dropdown
- Passes `beans`, `selected_bean_id` (str or `""`), `selected_bean` (ORM object or `None`) to template
- When `bean_id` is truthy, `comparison=[]` — skips `_compute_comparison` entirely

**`app/templates/analytics/index.html`**
- Empty state guard now checks `not selected_bean_id` — shows global empty state only when truly no shots AND no filter
- Bean picker `<select>` added inside the `{% else %}` block, above stats card
- `onchange` sets `window.location.href` to `/analytics` or `/analytics?bean_id=...`
- Stats card heading shows `— {bean.name}` when a bean is selected
- Cross-bean comparison wrapped in `{% if not selected_bean_id %}` — hidden in per-bean view

**`tests/test_analytics.py`** — 3 new tests:
- `test_analytics_with_bean_filter` — verifies per-bean stats, comparison hidden
- `test_analytics_all_beans_default` — verifies aggregate view unchanged
- `test_analytics_bean_filter_invalid_id` — verifies graceful 200 for unknown bean_id

### Task 2: History filter always visible

**`app/templates/history/index.html`**
- Replaced `<div class="collapse collapse-arrow ...">` wrapper (with `<input type="checkbox"/>` and `collapse-title`) with `<div class="card bg-base-200 border border-base-300 mb-4">`
- Filter panel content (`_filter_panel.html` include) unchanged — just unwrapped from the accordion

## Test Results

- **Before:** 5 analytics tests, 413 total — all passing
- **After:** 8 analytics tests, 413 total — all passing
- **No regressions** across 413 tests

## Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Pass `beans`, `selected_bean_id`, `selected_bean` to template | Dropdown + conditional heading need all three |
| D2 | `comparison=[]` when `bean_id` set | Skip unnecessary cross-bean DB work |
| D3 | `onchange window.location` (not htmx) | Full context change; no partial target |
| D4 | Dropdown shown inside `{% else %}` block | Must remain visible when filtered bean has 0 shots |
| D5 | Remove collapse entirely (not pre-check checkbox) | Simpler and more reliable than JS/attribute tricks |

## Deviations from Plan

None — plan executed exactly as written. The only minor addition was the per-bean empty state message ("No shots for this bean yet") shown when filtering to a bean with zero shots, which was implied by the spec's `{% if stats.total_shots == 0 %}` nested block requirement.

## Next Phase Readiness

- Analytics bean filter is in place — future plans can extend to trend charts per bean
- History filter visibility UX is complete
- Phase 25 Plan 01 (sidebar cleanup, dashboard intro, insights bean picker) was executed separately

---
phase: 06-analytics-exploration
plan: 02
subsystem: ui
tags: [chart.js, scatter-chart, heatmap, insights, jinja2, fastapi]

# Dependency graph
requires:
  - phase: 05-insights-trust
    provides: Insights page with Chart.js progress chart, chart-container CSS, theming conventions
  - phase: 04-shot-history-feedback-depth
    provides: Measurement model with grind_setting, temperature, taste, is_failed fields
provides:
  - Parameter exploration scatter chart on insights page (grind vs temperature colored by taste score)
  - heatmap_data context variable in insights router (points with x/y/taste/is_failed)
  - _heatmap_chart.html partial (Chart.js scatter, dual datasets, taste color gradient)
affects: [future visualization phases, analytics improvements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Chart.js scatter chart with per-point pointBackgroundColor computed from JS taste color function
    - Dual-dataset scatter pattern for normal vs failed shots (different marker types)
    - Minimum data threshold guard (>= 3 shots) before building heatmap_data in router

key-files:
  created:
    - app/templates/insights/_heatmap_chart.html
  modified:
    - app/routers/insights.py
    - app/templates/insights/index.html
    - tests/test_insights.py

key-decisions:
  - "Chart.js scatter chart (not matrix plugin) for heatmap — no extra dependency needed"
  - "Taste color gradient: red<=3, muted<=6, amber<=8, green 9-10 — matches espresso quality intuition"
  - "Failed shots as grey crossRot markers (distinct shape, not just color) — accessible distinction"
  - "Minimum 3 shots threshold for heatmap_data — avoids near-empty uninformative charts"
  - "Canvas ID heatmapChart distinct from progressChart — required for two Chart.js instances on same page"

patterns-established:
  - "Multi-chart page pattern: Chart.js CDN loaded once by first partial (_progress_chart.html); subsequent partials omit CDN load"
  - "Per-point color pattern: JS function maps taste (1-10) to color string, passed as pointBackgroundColor array"
  - "Dynamic axis bounds: min/max computed from data points in JS with padding — avoids hardcoded axis ranges"

# Metrics
duration: ~5min
completed: 2026-02-22
---

# Phase 6 Plan 02: Parameter Exploration Heatmap Summary

**Chart.js scatter chart on insights page showing grind vs temperature colored by taste score (red→amber→green gradient), with failed shots as grey crossRot markers**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-22T03:30:00Z (approx)
- **Completed:** 2026-02-22T04:34:17Z
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Added parameter exploration scatter chart to the insights page, revealing where in the parameter space good shots cluster (grind × temperature, colored by taste score)
- Failed shots displayed as grey `crossRot` markers — distinct shape, not just color — for accessibility
- 3 heatmap-specific tests added (empty state, data rendering, failed shot distinction) — all 9 insights tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Heatmap data preparation and chart template** - `5281f13` (feat)
2. **Task 2: Heatmap tests** - `85f3220` (test)

**Plan metadata:** _(pending docs commit)_

## Files Created/Modified
- `app/templates/insights/_heatmap_chart.html` — Created: Chart.js scatter partial with dual datasets, taste color gradient function, dynamic axis bounds, tooltips, empty state
- `app/routers/insights.py` — Extended measurement dict comprehension to include temperature/dose_in/target_yield/preinfusion_pct/saturation; added `heatmap_data` building with 3-shot threshold; passed to template context
- `app/templates/insights/index.html` — Added "Parameter Map" card section between Progress chart and Quick actions
- `tests/test_insights.py` — Added 3 heatmap tests: empty state, data present, failed shots distinct

## Decisions Made
- **Chart.js scatter (not matrix plugin):** No additional dependency required; per-point `pointBackgroundColor` array computed from taste score in JS achieves equivalent visual result
- **Taste color thresholds:** red (≤3), muted/grey (≤6), amber (≤8), green (9-10) — matches intuitive espresso quality rating
- **Failed shots shape distinction:** `crossRot` point style for failed shots (not just color change) — remains distinguishable for color-blind users
- **3-shot minimum threshold:** `heatmap_data = None` when fewer than 3 measurements — a 1-2 point scatter conveys no spatial pattern
- **Canvas ID:** `heatmapChart` (not `progressChart`) — required for Chart.js to manage two independent instances on the same page

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
- **Pre-existing test failure (not introduced here):** `tests/test_analytics.py::test_analytics_improvement_rate` fails because the test calls `GET /analytics` without setting an active bean cookie, so the analytics page renders the global stats view (no improvement rate arrow `↑`). This was confirmed pre-existing before our changes (present with `git stash`). Originated in plan 06-01 scope. Not fixed here as it is out of scope for this plan.
- **Pre-existing untracked file:** `tests/test_analytics.py` appears as untracked (not committed by plan 06-01). Left as-is; no action required for this plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Phase 6 is now complete (2/2 plans done): analytics page (06-01) + parameter heatmap (06-02)
- All 22 requirements from ROADMAP.md are now covered across all 6 phases
- **Outstanding pre-existing issue:** `test_analytics_improvement_rate` in `tests/test_analytics.py` needs a fix — the test should set an active bean cookie before calling `GET /analytics` to get the bean-specific stats view
- **Untracked file:** `tests/test_analytics.py` from plan 06-01 was never committed; should be committed or the test failure fixed first

---
*Phase: 06-analytics-exploration*
*Completed: 2026-02-22*

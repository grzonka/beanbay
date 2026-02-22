---
phase: 12
plan: 02
title: Manual Brew Form
subsystem: brew-ui
tags: [fastapi, jinja2, forms, css, javascript, testing]
depends_on: ["12-01"]
provides: ["GET /brew/manual", "manual.html template", "window.toggleFailed", "param CSS classes"]
affects: ["12-03", "12-04"]
tech-stack:
  added: []
  patterns: ["slider+number bidirectional sync", "hidden+checkbox saturation pattern", "window.toggleFailed shared JS"]
key-files:
  created:
    - app/templates/brew/manual.html
  modified:
    - app/routers/brew.py
    - app/static/js/tags.js
    - app/templates/brew/recommend.html
    - app/templates/brew/best.html
    - app/static/css/main.css
    - tests/test_brew.py
decisions:
  - "name attribute on number inputs (not sliders) so form submission captures correct values"
  - "window.toggleFailed exposed from tags.js IIFE to avoid duplication across 3 templates"
  - "hidden input value=no + checkbox value=yes for saturation (HTML checkbox semantics)"
  - "midpoint pre-fill uses _round_value() for practical step alignment"
metrics:
  duration: "~4 minutes"
  completed: "2026-02-22"
  tests-added: 6
  tests-total: 35
---

# Phase 12 Plan 02: Manual Brew Form Summary

**One-liner:** Manual brew entry at `/brew/manual` with bidirectional slider+number param inputs, pre-filled from best measurement or bounds midpoint, `toggleFailed` extracted to shared `tags.js`.

## What Was Built

### Task 1 — GET /brew/manual route + manual.html template

**`app/routers/brew.py`** — added `GET /brew/manual` route:
- Requires active bean (redirects to `/beans` if none)
- Resolves bounds via `_resolve_bounds(bean.parameter_overrides)`
- Loads best measurement via `_best_measurement(bean.id, db)` for pre-fill
- Falls back to `_round_value((lo + hi) / 2, step)` per-param midpoint
- Generates UUID `manual_session_id` per request
- Also imported `_round_value` from optimizer

**`app/templates/brew/manual.html`** — full manual form:
- 5 continuous params (grind_setting, temperature, preinfusion_pct, dose_in, target_yield) as bidirectional slider+number pairs
- Saturation: hidden `name="saturation" value="no"` + checkbox `value="yes"` pattern
- Taste slider with `data-touched="false"` inactive pattern (Phase 11 style)
- Extraction time optional number input
- Failed shot toggle with inline `toggleFailed` (temporary, extracted in Task 2)
- `{% include "brew/_feedback_panel.html" %}` for notes/flavor dimensions/tags
- `name` attribute on NUMBER inputs (not sliders) for correct form submission
- POSTs to `/brew/record` with `is_manual=true` hidden input

### Task 2 — Extract toggleFailed + CSS + tests

**`app/static/js/tags.js`** — extracted `window.toggleFailed`:
- Added before the `init()` Bootstrap section
- Exposed as `window.toggleFailed` so inline `onchange="toggleFailed(this)"` works
- Identical logic as the inline versions (taste set to 1/reset, group dimmed/restored)

**`app/templates/brew/recommend.html`** — removed duplicate inline `<script>` block with `toggleFailed` (26 lines removed). Only `<script src="/static/js/tags.js">` remains.

**`app/templates/brew/best.html`** — same as above (26 lines removed).

**`app/templates/brew/manual.html`** — inline `toggleFailed` replaced by `tags.js` script tag.

**`app/static/css/main.css`** — added 6 new classes:
- `.param-input-row` — flex row for slider+number alignment
- `.param-slider` — flex:1, accent-color matches brand
- `.param-number` — fixed 80px width, styled input
- `.param-unit` — muted label showing range or unit
- `.saturation-toggle` — flex row checkbox label
- `.saturation-toggle-label` — secondary text color

**`tests/test_brew.py`** — 6 new tests (29 → 35):
- `test_manual_page_loads_with_active_bean` — 200, form present, is_manual hidden
- `test_manual_page_no_active_bean_redirects` — 303 → /beans
- `test_manual_page_prefills_from_best` — best measurement values in response
- `test_manual_page_prefills_midpoint_no_measurements` — midpoint values in response
- `test_record_manual_brew_end_to_end` — saves with is_manual=True, redirects to /brew
- `test_manual_page_shows_bean_bounds` — default bounds (15–25, 86–96) in HTML

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `name` on number inputs only (not sliders) | Sliders are for UX sync only; numbers carry the submitted value with correct precision |
| `window.toggleFailed` in tags.js IIFE | Three templates needed the same function; extracting avoids drift and reduces page weight |
| `hidden(no) + checkbox(yes)` for saturation | HTML checkbox submits nothing when unchecked; hidden ensures `saturation=no` always present |
| `_round_value()` for midpoint pre-fill | Keeps pre-fill values on practical step increments (e.g. 20.0 not 20.0000000001) |
| Saturation defaults to "yes" (no measurements) | Sensible espresso default; aligns with optimizer recommendations |

## Test Results

```
119 passed, 2 warnings in 2.33s
35 brew tests (6 new for /brew/manual)
```

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

- **12-03** can build on: `GET /brew/manual` route live, `manual.html` template complete, CSS classes available, `window.toggleFailed` in shared JS
- No blockers identified

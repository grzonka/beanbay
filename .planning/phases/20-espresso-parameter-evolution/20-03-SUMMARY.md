---
phase: 20
plan: 03
subsystem: brew-ui
tags: [templates, jinja2, javascript, localStorage, hints, badges, daisyui]

dependency-graph:
  requires:
    - "20-01: parameter registry + schema (preinfusion_pressure_pct rename)"
    - "20-02: param_defs wired into show_recommendation + show_best routes"
  provides:
    - "Dynamic hidden inputs in best.html driven by param_defs"
    - "One-time onboarding hints for Phase 20 params (localStorage-dismissed)"
    - "New-param badge logic (first encounter per bean, localStorage-tracked)"
    - "Categorical param badge styling in recipe card"
    - "data-param attributes on all recipe-param divs"
    - "head_extra block in base.html for per-page meta injection"
  affects:
    - "Phase 21+ templates: head_extra block available for meta injection"
    - "Future param additions: PARAM_HINTS in brew.py for new hint text"

tech-stack:
  added:
    - "hints.js (vanilla JS, no dependencies)"
  patterns:
    - "localStorage for client-side onboarding state (param_hints_seen, params_seen_per_bean)"
    - "Server-side hint text via PARAM_HINTS dict + data-param-hint HTML attrs"
    - "Meta tag injection via head_extra block for JS data passing"

key-files:
  created:
    - "app/static/js/hints.js"
    - ".planning/phases/20-espresso-parameter-evolution/20-03-SUMMARY.md"
  modified:
    - "app/templates/brew/best.html"
    - "app/templates/brew/recommend.html"
    - "app/templates/brew/_recipe_card.html"
    - "app/templates/base.html"
    - "app/routers/brew.py"
    - "tests/test_brew.py"

decisions:
  - id: D1
    decision: "Hint cards rendered server-side (hidden), revealed by hints.js on DOMContentLoaded"
    rationale: "Server-side rendering avoids flash of visible hints before JS runs; hidden class removed only for unseen params"
  - id: D2
    decision: "head_extra block added to base.html for meta tag injection"
    rationale: "Cleanest way to pass bean-id and rec-params to hints.js without JS globals or inline script tags"
  - id: D3
    decision: "New-badge uses data-param attrs on .recipe-param divs, injected by hints.js"
    rationale: "_recipe_card.html is shared across best.html and recommend.html; badges are only injected by hints.js which only runs on recommend.html"
  - id: D4
    decision: "Categorical params use badge badge-outline badge-sm instead of recipe-value-text"
    rationale: "Visual distinction between continuous (number+unit) and categorical (badge) params; daisyUI-consistent"

metrics:
  duration: "~25 minutes"
  completed: "2026-02-26"
  tests-before: 405
  tests-after: 408
---

# Phase 20 Plan 03: Brew UI Capability-Driven Parameter Display Summary

**One-liner:** Dynamic param-aware brew templates with localStorage-based onboarding hints and categorical badge styling for Phase 20 espresso params.

## What Was Built

### Task 1: Dynamic best.html hidden inputs
- Replaced 6 hardcoded `<input type="hidden">` lines in `best.html` with a `{% for p in param_defs %}` loop
- Mirrors the pattern already in `recommend.html` (added in Plan 02)
- Legacy passthrough for `preinfusion_pressure_pct` on ORM-backed campaigns
- Route already passed `param_defs` from Plan 02 — no brew.py changes needed

### Task 2: Recommendation hints + "new" badge + categorical styling
- **PARAM_HINTS dict** added to `brew.py` with hint text for all 9 Phase 20 espresso params
- **`param_hints` passed** to `show_recommendation` template context
- **`recommend.html`**: dismissible hint cards (`alert alert-info`) rendered server-side as `hidden`, revealed by `hints.js` for first-seen params; meta tags `bb-bean-id` and `bb-rec-params` injected via new `head_extra` block
- **`hints.js`**: `ParamHintManager` class tracks dismissed hints in `localStorage`; `applyNewBadges()` injects `badge badge-accent badge-sm` on first-encountered advanced params per bean
- **`_recipe_card.html`**: `data-param` attributes added to all `.recipe-param` divs; categorical params (`pressure_profile`, `brew_mode`, `saturation`) now use `badge badge-outline badge-sm` styling
- **`base.html`**: `{% block head_extra %}` added before `</head>` for per-page meta injection
- **3 new tests**: param_hints in recommendation context, PARAM_HINTS covers all Phase 20 params, best.html dynamic hidden input check

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Hint cards server-rendered as hidden, JS reveals | No flash of visible content before JS runs |
| D2 | head_extra block in base.html for meta tags | Clean data passing without inline globals |
| D3 | New-badge injected by hints.js via data-param attrs | Recipe card shared between pages; badges only on recommend.html |
| D4 | Categorical params: badge badge-outline badge-sm | daisyUI-consistent visual distinction from continuous params |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one minor scope clarification:

**Task 2b "new badge" complexity reduction:** The plan offered a simpler alternative (Tier-1 baseline comparison via localStorage) vs the optimizer-metadata approach. The simpler approach was implemented: `hints.js` tracks seen params per bean in `localStorage`; any param beyond the 4 Tier-1 baseline params gets a "new" badge on first encounter. No changes to `optimizer.py` needed.

## Verification

- `rg "preinfusion_pct" app/templates/` → zero matches ✓
- `best.html` contains `{% for p in param_defs %}` loop ✓
- `app/static/js/hints.js` exists ✓
- `PARAM_HINTS` in `brew.py` with 9 Phase 20 param entries ✓
- `data-param-hint` attrs on hint cards in `recommend.html` ✓
- `data-param` attrs on `.recipe-param` divs in `_recipe_card.html` ✓
- 408/408 tests pass ✓

## Next Phase Readiness

Phase 20 is now complete (all 3 plans done). Phase 21 (New Brew Methods) can begin.

No blockers or concerns carried forward.

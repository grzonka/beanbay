---
phase: 23
plan: "02"
name: brew-method-awareness-and-welcome-page
subsystem: brew-ui
tags: [brew, templates, welcome, htmx, ux, onboarding]
requires: [23-01]
provides: [method-aware-brew-evaluation, welcome-page]
affects: [23-03]
tech-stack:
  added: []
  patterns: [conditional-template-rendering, method-aware-ui]
key-files:
  created:
    - app/templates/welcome.html
  modified:
    - app/templates/brew/recommend.html
    - app/templates/brew/manual.html
    - app/templates/brew/best.html
    - app/main.py
    - tests/test_beans.py
decisions:
  - id: D001
    summary: "brew_method variable set at top of each rating block, defaults to 'espresso'"
    rationale: "Templates receive method from route; fallback ensures backward compat for any legacy path that lacks it"
  - id: D002
    summary: "cold-brew extraction time in minutes (max 2880), others in seconds (max 1800 or 120 for espresso)"
    rationale: "Cold brew steep time is measured in hours, not seconds — displaying 7200 seconds is confusing; minutes is natural for users"
  - id: D003
    summary: "Welcome page shown at / when bean count is 0, redirects to /beans otherwise"
    rationale: "Empty-DB users get onboarding; returning users go directly to their bean list with no extra click"
  - id: D004
    summary: "Root test split into two: empty-DB shows welcome (200), populated shows redirect (303)"
    rationale: "Behavior is now conditional; one test cannot cover both branches — two tests needed for correctness"
metrics:
  duration: "~25 minutes"
  completed: "2026-02-26"
  tests-before: 408
  tests-after: 409
---

# Phase 23 Plan 02: Brew Method Awareness and Welcome Page Summary

**One-liner:** Method-aware brew evaluation (terminology + time ranges per method) and welcome onboarding page for empty databases.

## What Was Built

### Task 1 — Brew evaluation method-aware (committed `55928e1`)

All three brew evaluation templates (`recommend.html`, `manual.html`, `best.html`) updated:

- **Heading:** "Rate This Shot" for espresso / "Rate This Brew" for all other methods
- **Failed toggle:** "Failed shot (choked / gusher)" for espresso / "Failed brew" for others
- **Extraction time range:**
  - Espresso: max 120 seconds (label "Extraction Time (s)", placeholder 27)
  - Cold brew: max 2880 **minutes** (label "Steep Time (min)", placeholder 720)
  - All other methods: max 1800 seconds (label "Brew Time (s)", placeholder 240)

Each template uses a `{% set brew_method = method if method is defined else 'espresso' %}` guard at the top of the rating section for safe fallback.

### Task 2 — Welcome page for new users (committed `aa79995`)

- **`app/templates/welcome.html`:** Hero banner with BeanBay name/tagline, 4 feature cards (Track Brews, Get Smarter Recipes, Multiple Methods, Equipment Profiles), and CTA buttons ("Add Your First Bean →" and "I already have beans").
- **`app/main.py`:** Root route now `async def root(request, db)` — queries bean count; shows welcome page on 0 beans, redirects to `/beans` otherwise. Added `Jinja2Templates`, `Depends`, `Request`, `HTMLResponse`, `Session`, `get_db` imports.
- **`tests/test_beans.py`:** Replaced single `test_root_redirects_to_beans` with two tests: `test_root_shows_welcome_when_empty` (200 + "Add Your First Bean") and `test_root_redirects_to_beans_when_beans_exist` (303 to /beans).

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D001 | `brew_method` defaults to `'espresso'` in templates | Backward compat for any legacy call path |
| D002 | Cold-brew time in minutes, others in seconds | Minutes are the natural unit for steeping; 7200s would confuse users |
| D003 | `/` shows welcome when empty, redirects when beans exist | Onboarding for new users; zero friction for returning users |
| D004 | Root test split into two test functions | New branching behavior requires independent test coverage |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing test `test_root_redirects_to_beans` expected unconditional 303 redirect**

- **Found during:** Task 2 test run
- **Issue:** Root route now returns 200 (welcome page) for empty DB, so the old assertion `assert response.status_code == 303` failed
- **Fix:** Replaced with two tests covering both branches
- **Files modified:** `tests/test_beans.py`
- **Commit:** `aa79995`

## Test Results

- **Before:** 408 passing
- **After:** 409 passing (net +1 from splitting one test into two)

## Next Phase Readiness

- Plan 23-03 can proceed — no blockers from this plan
- `method` is already passed to all brew templates; 23-03 may build on this if needed

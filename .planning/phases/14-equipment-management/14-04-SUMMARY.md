---
phase: 14-equipment-management
plan: "04"
subsystem: ui
tags: [jinja2, html, css, sqlalchemy, fastapi, wizard, brew-setup]

# Dependency graph
requires:
  - phase: 14-equipment-management
    provides: Grinder/Brewer/Paper/WaterRecipe CRUD routes and BrewSetup model (plans 01-03)
provides:
  - Multi-step brew setup assembly wizard (5 steps: Brewer → Grinder → Filter → Water → Name)
  - Brew Setups section on equipment page showing compact setup cards
  - Create and Edit routes for BrewSetup via wizard flow
affects:
  - 14-05-equipment-management (retire/restore lifecycle for setups, brew page setup selection)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-page wizard with JS show/hide step sections (no HTMX, no page reloads)"
    - "Radio-button option cards for equipment selection (label wraps hidden radio input)"
    - "Auto-resolve brew_method_id from brewer's first method at POST time"

key-files:
  created:
    - app/templates/equipment/_setup_wizard.html
    - app/templates/equipment/_setup_card.html
  modified:
    - app/routers/equipment.py
    - app/static/css/main.css
    - app/templates/equipment/index.html

key-decisions:
  - "brew_method_id resolved server-side from brewer's first method (not user-facing step)"
  - "Paper step is optional — 'None / Skip' option is always first in the list"
  - "Brew Setups section is open by default (collapsible-content open class set at render time)"
  - "Name auto-filled as '{brewer} + {grinder}' when entering step 5 if field is empty"
  - "Edit link on setup card navigates to full wizard page (not modal)"

patterns-established:
  - "Wizard step content: .wizard-step-content hidden by default, .active shows current step"
  - "Option card selection: label.wizard-option-card with position:absolute hidden radio input"

# Metrics
duration: 45min
completed: 2026-02-23
---

# Phase 14 Plan 04: Brew Setup Assembly Wizard Summary

**5-step single-page wizard lets users assemble a named brew setup (brewer + grinder + optional filter + water recipe), with compact setup cards displayed at the top of the equipment page.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-02-23
- **Completed:** 2026-02-23
- **Tasks:** 2 completed
- **Files modified:** 5

## Accomplishments

- Built complete 5-step wizard flow with JS navigation, per-step validation, and auto-filled name suggestion
- Created 4 routes: GET/POST `/equipment/setups/new` and GET/POST `/equipment/setups/{id}` (create + edit)
- Added Brew Setups collapsible section at the top of the equipment page, open by default, with compact setup cards

## Task Commits

Each task was committed atomically:

1. **Task 1: Brew setup wizard** — `6b9f6a2` (feat)
2. **Task 2: Setup cards + equipment index** — `e2ae077` (feat)

**Plan metadata:** (see below)

## Files Created/Modified

- `app/routers/equipment.py` — Added `_get_wizard_context()`, 4 new routes (new/create/edit/update), updated `equipment_index` to pass `setups` + `setup_count`
- `app/templates/equipment/_setup_wizard.html` — Full 5-step wizard template (Brewer, Grinder, Filter, Water, Name steps)
- `app/static/css/main.css` — Added wizard CSS (step indicator, option cards, nav, summary preview) and setup card CSS
- `app/templates/equipment/_setup_card.html` — Compact setup card (name, components row, edit link)
- `app/templates/equipment/index.html` — Added Brew Setups section at top with setup loop and Create New Setup button

## Decisions Made

- **brew_method_id auto-resolved**: `BrewSetup.brew_method_id` is non-nullable; wizard resolves it from the selected brewer's first associated method, falling back to the first method in the DB. Not exposed to the user.
- **Paper step skippable**: Submitting with empty `paper_id` sets `paper_id = None` on the model.
- **Brew Setups section open by default**: Uses `collapsible-content open` at render time since setups are the primary reason to visit this page.
- **Edit opens full wizard page**: Setup cards link to `/equipment/setups/{id}/edit` (full page), not a modal, because the wizard has 5 steps and needs full width.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all 170 tests passed without modification.

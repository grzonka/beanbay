---
phase: 14-equipment-management
plan: "02"
subsystem: ui-equipment
tags: [fastapi, jinja2, htmx, css, equipment, grinder, brewer, modal, crud]

# Dependency graph
requires:
  - phase: 14-01
    provides: Extended equipment models (Grinder with dial fields, Brewer with methods M2M, is_retired on all)
  - phase: 13-02
    provides: patterns for router structure, htmx partial responses, POST-redirect-GET
provides:
  - Equipment router at /equipment with full grinder and brewer CRUD
  - Equipment page with collapsible sections for all equipment types
  - Grinder create/edit with stepped/stepless dial config
  - Brewer create/edit with method multi-select (many-to-many)
  - Navigation updated with Equipment link and "Let's Brew" rename
  - Modal pattern (CSS overlay + htmx-loaded content) for equipment create/edit
affects:
  - 14-03 (paper/water recipe CRUD will extend same router and page sections)
  - 14-04 (brew setup wizard builds on same equipment page layout)
  - 14-05 (retire/restore adds buttons to grinder/brewer cards created here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - CSS modal overlay pattern (equipment-modal-overlay) with htmx content loading
    - is_(False) SQLAlchemy filter for boolean columns (satisfies ruff E712)
    - `hx-post` + `hx-target` on form for inline create with modal close on success
    - openEditModal() JS function fetches edit form via Fetch API with HX-Request header

# File tracking
key-files:
  created:
    - app/routers/equipment.py
    - app/templates/equipment/index.html
    - app/templates/equipment/_grinder_card.html
    - app/templates/equipment/_grinder_form.html
    - app/templates/equipment/_brewer_card.html
    - app/templates/equipment/_brewer_form.html
  modified:
    - app/main.py
    - app/templates/base.html
    - app/static/css/main.css

# Decisions
decisions:
  - id: EQUIP-01
    decision: Used CSS modal overlay (not <dialog>) for equipment create/edit
    rationale: Consistent with existing app patterns; simpler JS control; htmx content loading works cleanly
  - id: EQUIP-02
    decision: Edit modal uses openEditModal() JS function with fetch() + HX-Request header
    rationale: Avoids needing hx-get attributes on every card button; single reusable function
  - id: EQUIP-03
    decision: Add modal (create) uses hx-post directly on form, close modal via hx-on::after-request
    rationale: htmx handles create inline; card prepended to list without page reload
  - id: EQUIP-04
    decision: Filter is_retired using .is_(False) not == False
    rationale: ruff E712 rejects == False comparisons; .is_(False) is the correct SQLAlchemy idiom

# Metrics
metrics:
  duration: ~25 minutes
  completed: "2026-02-23"
  tasks-completed: 3
  tests-passing: 153
---

# Phase 14 Plan 02: Equipment Router, Page, and Grinder/Brewer CRUD Summary

**One-liner:** Equipment management page at /equipment with collapsible sections, grinder CRUD (stepped/stepless), brewer CRUD (method multi-select), and CSS modal pattern.

## What Was Built

### Equipment Router (`app/routers/equipment.py`)
- `GET /equipment` — lists all 4 equipment types, accepts `?show_retired=true`
- `POST /equipment/grinders` — create grinder with dial type + range config
- `GET /equipment/grinders/{id}/edit` — return edit form partial (htmx)
- `POST /equipment/grinders/{id}` — update grinder
- `POST /equipment/brewers` — create brewer with method multi-select
- `GET /equipment/brewers/{id}/edit` — return edit form partial (htmx)
- `POST /equipment/brewers/{id}` — update brewer (clears and re-sets methods)

### Equipment Page (`app/templates/equipment/index.html`)
- Collapsible sections for: Grinders, Brewers, Papers & Filters, Water Recipes
- Each section header shows count badge
- "Show retired" checkbox toggle reloads page with `?show_retired=true`
- Add buttons open create modals (grinder-add-modal, brewer-add-modal)
- Edit buttons call `openEditModal(url)` which loads form into shared edit modal
- Papers and Water Recipes sections show placeholder "coming next plan" text

### Grinder Cards + Form
- Card shows: name, dial type, step size (if stepped), min–max range
- Create/edit form: name + radio dial-type toggle + conditional stepped fields
- JS `updateDialFields()` shows/hides step_size when dial type changes

### Brewer Cards + Form
- Card shows: name + method tags (badges per associated method)
- Create/edit form: name + checkbox list for method multi-select
- Edit pre-checks currently associated methods

### Navigation
- `base.html`: "Brew" renamed to "Let's Brew" per CONTEXT.md
- `base.html`: Added "Equipment" nav link between "Let's Brew" and "History"

### CSS (`app/static/css/main.css`)
- `.equipment-modal-overlay` / `.equipment-modal-box` — CSS modal pattern
- `.method-tag` — small badge for brew method display on brewer cards
- `.checkbox-item` / `.radio-option` — 48px+ touch targets for method/dial selection
- `.badge-retired` — muted badge for retired equipment display
- `.card-actions` — action row at bottom of equipment cards

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| EQUIP-01 | CSS modal overlay (not `<dialog>`) | Consistent with app patterns; clean htmx integration |
| EQUIP-02 | Edit uses `openEditModal()` JS fetch | Reusable single function; avoids inline hx-get on every card |
| EQUIP-03 | Create uses `hx-post` with `hx-on::after-request` close | Inline add without page reload; card prepended to list |
| EQUIP-04 | `.is_(False)` for boolean filter | ruff E712 rejects `== False`; `.is_(False)` is correct SQLAlchemy idiom |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff pre-commit hook rejected `== False` comparisons**

- **Found during:** Task 1 commit attempt
- **Issue:** `Grinder.is_retired == False` triggers ruff E712 in equipment.py
- **Fix:** Replaced all `== False` comparisons with `.is_(False)` (SQLAlchemy column method)
- **Files modified:** `app/routers/equipment.py`
- **Commit:** Part of `1b735ae`

## Verification Results

- ✅ `/equipment` page loads with collapsible sections for all equipment types
- ✅ Nav drawer shows "Equipment" link and "Let's Brew" (renamed from "Brew")
- ✅ Grinder CRUD: create with stepped/stepless, edit, display in cards
- ✅ Brewer CRUD: create with method association, edit, display with method badges
- ✅ Modal pattern working for create and edit
- ✅ `curl -s http://localhost:8001/equipment | grep -c "Grinders"` → 2 ✅
- ✅ 153/153 tests pass — no regressions

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `1b735ae` | feat | Equipment router, page layout, nav update, modal CSS — all tasks |

## Next Phase Readiness

- **14-03** is ready to start: paper/water recipe CRUD extends the same router and fills in the placeholder sections
- No blockers
- The `brew_methods` variable is already passed to the equipment index page (needed for brewer form checkboxes)

---
phase: 13-data-model-evolution-bean-metadata
plan: "03"
subsystem: bean-ui
tags: [fastapi, jinja2, forms, bag-management, metadata, htmx]

dependency-graph:
  requires:
    - "13-01 (Bean model with roast_date/process/variety + Bag model)"
    - "13-02 (Alembic migration applied)"
  provides:
    - "Bean create/edit with roast_date, process, variety"
    - "Bag CRUD routes (add + delete)"
    - "Bean detail page with metadata + bags section"
    - "Bean list collapsible More Details form"
    - "Process badge on bean cards"
  affects:
    - "14+ (Equipment Management) — bean detail page structure established"
    - "Transfer learning (Phase 16+) — process/variety now capturable via UI"

tech-stack:
  added: []
  patterns:
    - "POST-redirect-GET for bag mutations"
    - "Collapsible sections for optional/secondary form fields"
    - "str Form('') + manual float/date parsing for optional numeric/date fields"
    - "_bean_with_shot_count dict pattern extended with new fields + bags"

key-files:
  created: []
  modified:
    - "app/routers/beans.py"
    - "app/templates/beans/detail.html"
    - "app/templates/beans/list.html"
    - "app/templates/beans/_bean_card.html"
    - "tests/test_beans.py"

decisions:
  - id: D-13-03-01
    choice: "Use collapsible 'More Details' in create form"
    rationale: "Keeps the primary create form clean (name only required) while exposing optional metadata"
    alternatives: "Always-visible fields; deferred to detail page only"
  - id: D-13-03-02
    choice: "Accept cost/weight_grams as str Form('') + parse to float manually"
    rationale: "Avoids FastAPI 422 on empty string for float fields; consistent with existing overrides pattern"
    alternatives: "Optional[float] = Form(None) — doesn't work with HTML forms sending empty strings"
  - id: D-13-03-03
    choice: "Bag routes ordered before /{bean_id}/delete to avoid route conflicts"
    rationale: "FastAPI matches routes in order; /{bean_id}/bags must precede /{bean_id}/delete"
    alternatives: "N/A — ordering is required for correctness"

metrics:
  duration: "~24 hours (across sessions)"
  completed: "2026-02-22"
  tasks-completed: 3
  tests-added: 9
  tests-total: 153
---

# Phase 13 Plan 03: Bean Metadata UI & Bag Management Summary

**One-liner:** Bean create/edit forms with roast_date/process/variety fields and full bag CRUD (add/delete) on the bean detail page.

## What Was Built

### Task 1: Updated bean routes (`app/routers/beans.py`)
- Added `from app.models.bag import Bag` import
- Extended `_bean_with_shot_count()` to include `roast_date`, `process`, `variety`, and `bags` (sorted by `created_at` desc)
- Updated `create_bean()` and `update_bean()` routes to accept `roast_date`, `process`, `variety` Form params with proper parsing
- Added `POST /{bean_id}/bags` (`add_bag`) — creates a Bag record, redirects to detail
- Added `POST /{bean_id}/bags/{bag_id}/delete` (`delete_bag`) — deletes bag by id+bean_id, redirects to detail

### Task 2: Updated templates
- **`detail.html`:** Added roast_date (date input), process (select with 5 options), variety (text) to the bean edit form. Added new "Bags" section after bean info card: lists existing bags with delete buttons, collapsible "Add Bag" form with purchase_date/cost/weight_grams/notes.
- **`list.html`:** Added collapsible "More Details" section between origin and the Add Bean button, containing roast_date/process/variety fields.
- **`_bean_card.html`:** Added process badge display (capitalized) below the roaster/origin subtitle.

### Task 3: 9 new tests (`tests/test_beans.py`)
| Test | What it covers |
|------|---------------|
| `test_create_bean_with_metadata` | POST with roast_date/process/variety stores and displays them |
| `test_create_bean_without_metadata` | Backward compat — name-only create still works |
| `test_update_bean_with_metadata` | POST to update with metadata fields |
| `test_update_bean_clear_metadata` | Empty process clears field to None in DB |
| `test_add_bag` | POST /bags stores cost/weight, shows on detail page |
| `test_add_bag_minimal` | All-empty bag fields creates valid minimal Bag record |
| `test_delete_bag` | POST /bags/{id}/delete removes bag from DB |
| `test_bean_detail_shows_bags` | Detail page renders all bags for a bean |
| `test_delete_bean_cascades_bags` | Bean deletion cascades to remove all bags |

## Verification Results

- `pytest tests/test_beans.py -v` — 32/32 pass (23 existing + 9 new)
- `pytest --tb=short` — 153/153 pass, zero regressions
- Templates parse without Jinja2 errors
- Router and app import without errors

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-13-03-01 | Collapsible "More Details" in create form | Keeps primary form clean |
| D-13-03-02 | `str Form("") + manual parse` for numeric/date fields | Avoids FastAPI 422 on empty strings |
| D-13-03-03 | Bag routes ordered before `/{bean_id}/delete` | Route ordering required for FastAPI matching |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added explicit `from app.models.bag import Bag` import**

- **Found during:** Task 1 verification
- **Issue:** The `Bag` class was used in routes but the explicit import was missing. The app worked at runtime due to SQLAlchemy lazy-loading the model through relationships, but this was fragile and would fail in isolation.
- **Fix:** Added `from app.models.bag import Bag` to the imports block.
- **Files modified:** `app/routers/beans.py`
- **Commit:** def2e2d

No other deviations — plan executed as written.

## Next Phase Readiness

Phase 13 Plan 03 completes the user-facing part of Phase 13. All three plans are done:
- 13-01: New models (Bag, BrewMethod, Grinder, Brewer, Paper, WaterRecipe, BrewSetup) + Bean/Measurement extensions
- 13-02: Alembic migration
- 13-03: Bean metadata UI + bag management (this plan)

**Ready for Phase 14:** Equipment Management (Grinder, Brewer, Paper models now have DB tables and can be exposed in UI).

**Blockers/Concerns for next phases:**
- None. Bean metadata and bag foundation is solid.

---
phase: 04-shot-history-feedback-depth
plan: 03
subsystem: ui
tags: [shot-modal, htmx-dialog, hx-swap-oob, hx-trigger, jinja2, vanilla-js, fastapi]

# Dependency graph
requires:
  - phase: 04-shot-history-feedback-depth
    plan: 02
    provides: history page with shot rows, modal scaffold (dialog + container div)

provides:
  - GET /history/{shot_id}: shot detail modal partial + HX-Trigger: openShotModal
  - GET /history/{shot_id}/edit: pre-populated edit form inside modal
  - POST /history/{shot_id}/edit: saves notes/flavors/tags, returns updated modal + oob shot row
  - _shot_modal.html: full shot detail view (recipe params, taste, notes, flavor bars, tags)
  - _shot_edit.html: edit form pre-populated with existing values
  - tags.js extended: edit modal IDs, htmx:afterSettle re-init, openShotModal listener
  - 9 new tests (19 total in test_history.py)

affects:
  - 05-insights-trust (retroactively enriched shot data is now available; flavor/tag data richer)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HX-Trigger response header → JS custom event → dialog.showModal()"
    - "hx-swap-oob='outerHTML:#shot-{id}' pattern for in-place list row update"
    - "htmx:afterSettle re-initialization for dynamically loaded JS-dependent content"
    - "Two-part htmx response: main content + oob fragment appended to same response body"

# File tracking
key-files:
  created:
    - app/templates/history/_shot_modal.html
    - app/templates/history/_shot_edit.html
  modified:
    - app/routers/history.py
    - app/static/css/main.css
    - app/static/js/tags.js
    - app/templates/history/index.html
    - tests/test_history.py

# Decisions
decisions:
  - id: hx-trigger-open-modal
    choice: "HX-Trigger: openShotModal header + JS addEventListener"
    rationale: "Server signals when to open dialog — keeps JS minimal, no polling or mutation observer needed"
    alternatives: ["JS MutationObserver on container", "Client-side hx-on attribute"]
  - id: oob-row-update
    choice: "Render _shot_modal.html as main body + append rendered _shot_row.html with hx-swap-oob"
    rationale: "htmx oob swap lets one POST response update two DOM locations atomically"
    alternatives: ["Two separate requests", "Full page reload"]
  - id: tags-js-fix
    choice: "Add {% block scripts %} to history/index.html to load tags.js"
    rationale: "openShotModal event listener lives in tags.js — without it, dialog.showModal() never fires"

# Metrics
metrics:
  duration: "~10 min"
  completed: "2026-02-22"
  tasks_total: 1
  tasks_completed: 1
  tests_added: 9
  tests_total: 87
---

# Phase 4 Plan 03: Shot Detail Modal & Edit Summary

**One-liner:** Tapping any history shot row opens a `<dialog>` modal with full recipe details, flavor profile bars, and tags — editable inline with htmx oob row sync.

## What Was Built

A complete shot detail and edit flow integrated into the history page:

- **`GET /history/{shot_id}`** — returns modal HTML partial; response carries `HX-Trigger: openShotModal` header so JS fires `dialog.showModal()` after htmx swaps the content into `#shot-modal-container`
- **`GET /history/{shot_id}/edit`** — returns pre-populated edit form inside the modal; notes, 6 flavor sliders (pre-set to saved values, "touched" state restored), and existing flavor tags rendered as removable chips
- **`POST /history/{shot_id}/edit`** — saves all editable fields; returns updated modal as main response + `_shot_row.html` with `hx-swap-oob="outerHTML:#shot-{id}"` to update the list row behind the modal simultaneously
- **`_shot_modal.html`** — detail view: bean name + timestamp header, large taste score, recipe params grid (grind/temp/pre-inf/dose/yield/saturation), brew ratio, notes block, flavor profile bar chart (only shown for rated dimensions), flavor tags as read-only chips, "Edit Feedback" footer button
- **`_shot_edit.html`** — edit form: notes textarea, 6 flavor sliders (pre-populated, brightened if previously rated), tag input with pre-populated chips, Cancel (returns to detail view) and Save buttons
- **`tags.js` extended** — added `removeEditTag()` global for pre-populated edit tag chips, `htmx:afterSettle` re-initialization (re-binds tag input behavior after modal content swaps), `openShotModal` custom event listener
- **Bug fix** — `history/index.html` was missing `{% block scripts %}` so `tags.js` never loaded on the history page; added the block with the script tag

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Detail/edit endpoints + modal templates + JS/CSS + 9 tests | 619b2b4 | history.py, _shot_modal.html, _shot_edit.html, main.css, tags.js, test_history.py |
| Fix | Load tags.js on history page ({% block scripts %}) | 1569cb4 | history/index.html |

## Decisions Made

1. **HX-Trigger → openShotModal:** The server signals the client to open the dialog by setting `HX-Trigger: openShotModal` on the GET response. htmx dispatches this as a custom event on the document body; `tags.js` listens and calls `dialog.showModal()`. This keeps JS minimal — no polling, no MutationObserver.

2. **hx-swap-oob for list row update:** After a POST edit, the response body contains the updated modal HTML as the primary content (swapped into `#shot-modal-container`) plus a rendered `_shot_row.html` fragment with `hx-swap-oob="outerHTML:#shot-{id}"`. htmx processes both in one response — the modal and the list row update atomically.

3. **tags.js fix (missing scripts block):** `history/index.html` did not include `{% block scripts %}`, so the page-level `<script src="/static/js/tags.js">` added for the edit modal never loaded. Without it, the `openShotModal` event listener was never registered, so `dialog.showModal()` was never called and modals appeared invisible. Fixed by adding the scripts block.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing {% block scripts %} in history/index.html**

- **Found during:** Checkpoint verification (human-verify)
- **Issue:** `history/index.html` did not have a `{% block scripts %}` block. `tags.js` was referenced in the plan to be loaded on the history page (it contains the `openShotModal` listener), but the template had no slot for the script tag. As a result, clicking a shot row loaded the modal HTML via htmx but `dialog.showModal()` was never called — modal was in the DOM but invisible.
- **Fix:** Added `{% block scripts %}<script src="/static/js/tags.js"></script>{% endblock %}` to `history/index.html`.
- **Files modified:** `app/templates/history/index.html`
- **Commit:** `1569cb4`

## Test Coverage

9 new tests added to `tests/test_history.py` (19 total, 87 overall):

| Test | What it verifies |
|------|-----------------|
| `test_shot_detail_returns_modal_html` | GET /history/{id} returns 200 with shot data |
| `test_shot_detail_includes_hx_trigger` | Response includes HX-Trigger: openShotModal |
| `test_shot_detail_nonexistent_returns_404` | GET /history/99999 → 404 |
| `test_shot_edit_form_loads` | GET /history/{id}/edit returns 200 with edit form |
| `test_shot_edit_saves_notes` | POST edit persists notes to DB |
| `test_shot_edit_saves_flavor_dimensions` | POST edit persists flavor dimension values |
| `test_shot_edit_saves_flavor_tags` | POST edit persists flavor_tags as JSON |
| `test_shot_edit_clears_notes` | POST with empty notes sets notes=None |
| `test_shot_edit_returns_oob_row_update` | POST response contains hx-swap-oob fragment |

All 87 tests pass.

## Next Phase Readiness

Phase 4 is complete. The shot history and feedback depth story is fully told:

- Feedback panel on both brew forms (notes, 6 flavor sliders, tags) ✓
- Shot history list with filtering ✓
- Shot detail modal with full recipe params and flavor profile ✓
- Retroactive editing of notes, flavors, and tags ✓
- All changes persist and sync to the list row immediately ✓

**Ready for Phase 5 (Insights & Trust):**
- Rich feedback data (acidity, sweetness, body, bitterness, aroma, intensity, flavor_tags) is in the DB and ready for trend analysis
- History page is the natural anchor for insight charts (Phase 5 can add tabs or panels)
- BayBE surrogate model already incorporates retro-edited measurements on next rebuild

---
*Phase: 04-shot-history-feedback-depth*
*Completed: 2026-02-22*

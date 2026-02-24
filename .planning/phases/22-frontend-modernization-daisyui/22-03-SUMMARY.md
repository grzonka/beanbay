---
phase: 22-frontend-modernization-daisyui
plan: 03
subsystem: ui
tags: [tailwind, daisyui, htmx, jinja2, html, equipment, modal, dialog, wizard, collapse]

# Dependency graph
requires:
  - phase: 22-01
    provides: Tailwind + daisyUI build pipeline, base layout, custom @layer component classes
  - phase: 14-equipment-management
    provides: Equipment CRUD routes, htmx patterns, setup wizard, retire/restore flow
provides:
  - 11 equipment/ templates restyled with daisyUI components
  - Native <dialog class="modal"> pattern replacing custom overlay modals
  - daisyUI collapse sections replacing JS classList toggle pattern
  - All equipment CRUD (create, edit, retire, restore) htmx flows preserved
affects: [22-06, future equipment feature phases]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native <dialog> modals: showModal()/close() instead of classList add/remove"
    - "daisyUI collapse: <input type=checkbox> pattern (not <details>) allows multiple open"
    - "form-control/input-bordered/select-bordered/textarea-bordered for all form inputs"
    - "card bg-base-200 border border-base-300 + keep identifying class for JS querySelector"

key-files:
  created: []
  modified:
    - app/templates/equipment/index.html
    - app/templates/equipment/_setup_wizard.html
    - app/templates/equipment/_setup_card.html
    - app/templates/equipment/_grinder_card.html
    - app/templates/equipment/_grinder_form.html
    - app/templates/equipment/_brewer_card.html
    - app/templates/equipment/_brewer_form.html
    - app/templates/equipment/_paper_card.html
    - app/templates/equipment/_paper_form.html
    - app/templates/equipment/_water_card.html
    - app/templates/equipment/_water_form.html

key-decisions:
  - "Native <dialog> replaces custom overlay: showModal()/close() native API, modal-backdrop form handles click-outside natively"
  - "Keep grinder-card/brewer-card/paper-card/water-card classes: used by htmx:afterSwap querySelector to remove empty-state"
  - "Keep wizard-steps/wizard-option-card/wizard-step-label/etc: defined in input.css @layer components, JS class toggles depend on them"
  - "mineral-grid kept as custom class: defined in input.css @layer components"
  - "wizard-add-link kept as custom class: defined in input.css @layer components"

patterns-established:
  - "Modal pattern: <dialog id='...' class='modal'> with <form method='dialog' class='modal-backdrop'> for click-outside close"
  - "Collapse pattern: <div class='collapse collapse-arrow bg-base-200 border border-base-300'> with <input type='checkbox'>"
  - "Form pattern: form-control mb-4 + label.label > span.label-text + input.input-bordered.w-full"
  - "Card pattern: card bg-base-200 border border-base-300 mb-2 + keep identifying class"

# Metrics
duration: 5min
completed: 2026-02-24
---

# Phase 22 Plan 03: Equipment Templates daisyUI Conversion Summary

**11 equipment/ templates converted to daisyUI — custom overlay modals → native `<dialog>` with showModal()/close(), JS toggle collapsibles → daisyUI checkbox collapse, all htmx CRUD preserved**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-02-24T00:46:22Z
- **Completed:** 2026-02-24T00:51:33Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Converted 5 custom `div.equipment-modal-overlay` modals to native `<dialog class="modal">` with `showModal()`/`close()` — eliminated all custom overlay CSS and JS
- Converted 5 collapsible sections to daisyUI `collapse collapse-arrow` checkbox pattern — eliminated all `onclick="this.nextElementSibling.classList.toggle('open')"` JS
- Restyled 10 card/form/wizard templates: `form-control`/`input-bordered`/`select-bordered`/`textarea-bordered`/`checkbox`/`radio` replacing all `form-group`/`form-input`/`form-label` custom classes
- Preserved all wizard JS (`showStep`, `validateStep`, `updateSummary`, `autoFillName`, `wizardNext`, `wizardBack`), Jinja2 data objects (`BREWERS`, `GRINDERS`, `PAPERS`, `WATER_RECIPES`), and all htmx attributes unchanged

## Task Commits

Each task was committed atomically:

1. **Task 1: Restyle equipment/index.html — daisyUI collapse + native dialog modals** - `6a6dda3` (feat)
2. **Task 2: Restyle 10 remaining equipment templates** - `f54a3b6` (feat)

**Plan metadata:** (see docs commit below)

## Files Created/Modified
- `app/templates/equipment/index.html` — 5 daisyUI collapse sections, 5 native `<dialog>` modals, updated JS
- `app/templates/equipment/_setup_card.html` — card bg-base-200, btn-ghost/btn-primary/btn-error actions
- `app/templates/equipment/_grinder_card.html` — card pattern + keep `grinder-card` class for JS targeting
- `app/templates/equipment/_brewer_card.html` — card pattern + keep `brewer-card`, method-tags as badge-outline
- `app/templates/equipment/_paper_card.html` — card pattern + keep `paper-card` class
- `app/templates/equipment/_water_card.html` — card pattern + keep `water-card` class
- `app/templates/equipment/_grinder_form.html` — form-control/input-bordered, radio-option pill buttons
- `app/templates/equipment/_brewer_form.html` — form-control/input-bordered/select-bordered, checkbox-primary for methods
- `app/templates/equipment/_paper_form.html` — form-control/input-bordered/textarea-bordered
- `app/templates/equipment/_water_form.html` — form-control/input-bordered, mineral-grid preserved
- `app/templates/equipment/_setup_wizard.html` — page-header→flex, form-group→form-control, wizard-* custom classes preserved, setup-summary as card bg-base-200

## Decisions Made
- **Native `<dialog>` replaces overlay:** `showModal()`/`close()` native browser API; `<form method="dialog" class="modal-backdrop">` handles click-outside-to-close without JS
- **Keep identifying card classes:** `grinder-card`, `brewer-card`, `paper-card`, `water-card` used by `htmx:afterSwap` handler in `index.html` to `querySelector` and remove empty-state placeholder — must be preserved
- **Keep all wizard custom classes:** `wizard-steps`, `wizard-option-card`, `wizard-step-label`, `wizard-step-connector`, `wizard-step-content`, `wizard-options` all defined in `input.css @layer components` and referenced by wizard JS — preserved verbatim
- **Keep `mineral-grid` and `wizard-add-link`:** Custom `@layer components` classes in `input.css`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- All 11 equipment/ templates using daisyUI — equipment UI modernization complete
- Phase 22 continues with Plan 04 (history/shots templates) and Plan 05 (insights), Plan 06 (analytics + remaining)
- Phase 17 Plan 03 (test fixture updates) can proceed independently

---
*Phase: 22-frontend-modernization-daisyui*
*Completed: 2026-02-24*

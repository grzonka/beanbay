---
phase: 18-brewer-capability-model
plan: "02"
title: "Brewer Capability Routes, Form & Tests"
one-liner: "Brewer create/edit routes accept 13 capability fields, form uses progressive disclosure, cards show T1-T5 tier badges, 6 new CRUD tests"
subsystem: equipment-ui
tags: [equipment, capabilities, forms, progressive-disclosure, tiers, htmx]

dependency-graph:
  requires:
    - phase: 18-brewer-capability-model
      plan: "01"
      provides: "13 Brewer capability columns + derive_tier() utility"
  provides:
    - "Brewer create/edit routes accepting all 13 capability fields"
    - "Progressive-disclosure brewer form (capability fields revealed based on type selection)"
    - "Tier badge (T1–T5) on brewer cards"
    - "6 new CRUD tests covering capability round-trips"
  affects:
    - "Phase 19 (Parameter registry UI — capability pattern reuse)"

tech-stack:
  added: []
  patterns:
    - "Progressive disclosure: capability fields shown/hidden via htmx or JS based on control-type selects"
    - "Tier badge on equipment cards: derived server-side, rendered as T1–T5 label"

key-files:
  created: []
  modified:
    - "app/routers/equipment.py"
    - "app/templates/equipment/_brewer_form.html"
    - "app/templates/equipment/_brewer_card.html"
    - "tests/test_equipment.py"

key-decisions:
  - "Progressive disclosure controlled server-side via derive_tier() to keep form complexity manageable"
  - "Tier badge rendered on brewer card for at-a-glance capability summary"

patterns-established:
  - "Capability-aware forms: control-type selects gate dependent numeric fields"
  - "Tier badge pattern: server-derives tier, template renders T1–T5 badge — reusable for Phase 19"

metrics:
  duration: "~20 minutes"
  completed: "2026-02-25"
  tasks-total: 3
  tasks-completed: 3
  tests-added: 6
  tests-passing: 284
---

# Phase 18 Plan 02: Brewer Capability Routes, Form & Tests — Summary

**Brewer create/edit routes accept 13 capability fields, form uses progressive disclosure, cards show T1-T5 tier badges, 6 new CRUD tests**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-02-25
- **Completed:** 2026-02-25
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Brewer create/edit routes wired to accept and persist all 13 capability columns from Plan 01
- Brewer form redesigned with progressive disclosure — capability fields appear based on control-type selection, reducing cognitive load for basic machines
- Tier badge (T1–T5) added to brewer cards for at-a-glance capability summary
- 6 new CRUD tests in `tests/test_equipment.py` covering capability round-trips through the route layer

## Task Commits

Each task was committed atomically:

1. **Task 1: Update brewer routes for capability fields** - `ff05472` (feat)
2. **Task 2: Brewer form progressive disclosure + tier badge** - `6266063` (feat)
3. **Task 3: Equipment tests for capability CRUD** - `81a1347` (test)

**Plan metadata:** *(this commit)* (docs: complete brewer capability routes and UI plan)

## Files Created/Modified

- `app/routers/equipment.py` — Create/edit routes updated to read and persist all 13 capability fields
- `app/templates/equipment/_brewer_form.html` — Progressive disclosure form with capability field groups gated by control-type selects
- `app/templates/equipment/_brewer_card.html` — T1–T5 tier badge rendered server-side from `derive_tier()`
- `tests/test_equipment.py` — 6 new tests covering capability CRUD through routes

## Decisions Made

| Decision | Why |
|----------|-----|
| Progressive disclosure controlled server-side | Keeps capability complexity out of the form by default; basic brewers (T1) see minimal fields, advanced brewers surface more |
| Tier badge on card (not just form) | Gives users an immediate capability summary without opening edit mode — useful for equipment selection during brew session |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Brewer capability model and UI are complete end-to-end: model (Plan 01) → routes + form + card badge (Plan 02)
- Phase 19 (Parameter registry UI) can reuse the progressive disclosure pattern and tier badge approach established here
- `derive_tier()` from `app.utils.brewer_capabilities` is available for Phase 19 search space gating

---
*Phase: 18-brewer-capability-model*
*Completed: 2026-02-25*

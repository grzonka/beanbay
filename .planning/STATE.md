# Project State: BeanBay

**Last updated:** 2026-02-22
**Current phase:** Phase 12 — Manual Brew Input (in progress)

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-22)

**Core value:** Every coffee brew teaches the system something — the app must make it effortless to capture that feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** v0.1.1 — UX Polish & Manual Brew

## Milestone History

| Milestone | Phases | Plans | Status | Date |
|-----------|--------|-------|--------|------|
| v1 MVP | 1-6 | 16 | ✅ Shipped | 2026-02-22 |
| v0.1.0 Release & Deploy | 7-9 | 5 | ✅ Shipped | 2026-02-22 |
| v0.1.1 UX Polish & Manual Brew | 10-12 | TBD | 🚧 In progress | — |

## Current Position

Phase: 12 of 12 (Manual Brew Input) — Plan 2 of TBD complete
Plan: 2 of TBD — 12-02 complete
Status: In progress — ready for Plan 12-03
Last activity: 2026-02-22 — Completed 12-02-PLAN.md (GET /brew/manual route, manual.html form, toggleFailed extracted to tags.js, CSS classes, 6 new tests)

Progress: [██████████████████████████████████████████░░] ~92% (27 plans complete, v0.1.1 in progress)

## Performance Metrics

**Velocity:**
  - Total plans completed: 27 (v1: 16, v0.1.0: 5, v0.1.1: 6)
  - v0.1.1 plans completed: 6 (phase 10: 2, phase 11: 2, phase 12: 2)
- v0.1.1 total plans: TBD (refined during planning)

## Accumulated Context

### Key Technical Decisions
See: .planning/PROJECT.md (Key Decisions table)

| Phase | Decision | Rationale |
|-------|----------|-----------|
| 11 | Render /brew with no_active_bean flag instead of redirect | Silent redirects are confusing on mobile; inline prompt keeps user in context |
| 11 | Other brew routes still redirect when no bean | POST /recommend, GET /best, POST /record genuinely require a bean to function |
| 11 | data-touched attribute on taste slider (not JS var) | State co-located with DOM element; easier to reset via toggleFailed; easier to inspect |
| 11 | Display "—" as initial taste slider label | 7.0 default looked like a deliberate choice; "—" clearly signals unset |
| 12 | Add POST /beans/set-active for bean picker form | Existing activate route uses path param; form <select> submits body field |
| 12 | Bounds validation only for is_manual == "true" | Optimizer recs always in-bounds; manual entries need validation |
| 12 | name attribute on number inputs (not sliders) | Sliders are for UX sync only; numbers carry submitted value with correct precision |
| 12 | window.toggleFailed exposed from tags.js IIFE | Three templates needed same function; single source of truth avoids drift |
| 12 | hidden(no) + checkbox(yes) for saturation | HTML checkbox submits nothing when unchecked; hidden ensures saturation=no always present |

### Branding
- **Name:** BeanBay | **Domain:** beanbay.coffee
- **Docker:** ghcr.io/grzonka/beanbay | **Release:** v0.1.0 live

### Quick Tasks Completed

| ID | Task | Date |
|----|------|------|
| 001 | Fix CI test DB isolation | 2026-02-22 |

## Session Continuity

### Last Session
- **Date:** 2026-02-22
- **What happened:** Executed 12-02-PLAN.md — GET /brew/manual route added with pre-fill logic (best measurement or bounds midpoint); manual.html template with bidirectional slider+number param inputs; saturation toggle with hidden+checkbox pattern; toggleFailed extracted from recommend.html and best.html into window.toggleFailed in tags.js; CSS classes .param-input-row, .param-slider, .param-number, .param-unit, .saturation-toggle added; 6 new tests (29→35 brew, 119 total).
- **Where we left off:** Phase 12 Plan 2 complete. Ready for Plan 12-03 (next plan in phase).

### Next Steps
1. Execute Phase 12 Plan 03 (see .planning/phases/12-manual-brew-input/12-03-PLAN.md)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-22 after completing 12-02 manual brew form*

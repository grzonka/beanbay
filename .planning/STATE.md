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

Phase: 12 of 12 (Manual Brew Input) — Plan 3 of TBD complete
Plan: 3 of TBD — 12-03 complete
Status: In progress — ready for Plan 12-04
Last activity: 2026-02-22 — Completed 12-03-PLAN.md (Manual badge in history rows/modal, batch delete with BayBE campaign rebuild, 7 new tests, 126 total)

Progress: [███████████████████████████████████████████░] ~94% (28 plans complete, v0.1.1 in progress)

## Performance Metrics

**Velocity:**
  - Total plans completed: 28 (v1: 16, v0.1.0: 5, v0.1.1: 7)
  - v0.1.1 plans completed: 7 (phase 10: 2, phase 11: 2, phase 12: 3)
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
| 12 | Delete checkbox uses form attribute (not nested) | Checkbox inside shot card, outside delete form; HTML form= attribute links it regardless of DOM nesting |
| 12 | Capture shot IDs before delete in tests | SQLAlchemy raises ObjectDeletedError accessing deleted instance attrs after expire_all() |

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
- **What happened:** Executed 12-03-PLAN.md — Manual badge (blue #3b82f6) in history rows and modal; `is_manual` added to all three shot dicts; batch delete via POST /history/delete-batch with BayBE campaign rebuild per affected bean; delete mode toggle button + sticky action bar + per-row checkboxes; 7 new tests (19→26 history, 126 total).
- **Where we left off:** Phase 12 Plan 3 complete. Ready for Plan 12-04 (next plan in phase).

### Next Steps
1. Execute Phase 12 Plan 04 (see .planning/phases/12-manual-brew-input/12-04-PLAN.md)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-22 after completing 12-03 manual badge + batch delete*

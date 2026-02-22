# Project State: BeanBay

**Last updated:** 2026-02-22
**Current phase:** Phase 12 — next phase (Phase 11 complete)

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

Phase: 12 of 12 (Manual Brew Input) — Plan 1 of TBD complete
Plan: 1 of TBD — 12-01 complete
Status: In progress — ready for Plan 12-02
Last activity: 2026-02-22 — Completed 12-01-PLAN.md (is_manual column, bean picker, Manual Input button, bounds validation)

Progress: [█████████████████████████████████████████░░░] 90%+ (26 plans complete, v0.1.1 in progress)

## Performance Metrics

**Velocity:**
  - Total plans completed: 26 (v1: 16, v0.1.0: 5, v0.1.1: 5)
  - v0.1.1 plans completed: 5 (phase 10: 2, phase 11: 2, phase 12: 1)
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
- **What happened:** Executed 12-01-PLAN.md — is_manual Boolean column added to Measurement model + Alembic migration applied; brew page restructured with bean picker dropdown and Manual Input button; POST /brew/record validates bounds when is_manual=true (422 with violations); POST /beans/set-active added for bean picker form.
- **Where we left off:** Phase 12 Plan 1 complete. Ready for Plan 12-02 (manual brew form at /brew/manual).

### Next Steps
1. Execute Phase 12 Plan 02 (manual brew form — the /brew/manual route + template)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-22 after completing 11-01 inactive taste slider + submit gate (Phase 11 complete)*

# Project State: BrewFlow

**Last updated:** 2026-02-21
**Current phase:** Phase 2 (COMPLETE — all plans executed, 43/43 tests passing)

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Every espresso shot teaches the system something — the app must make it effortless to capture feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** Phase 2 complete, ready for Phase 3

## Phase Status

| Phase | Name | Status | Plans | Progress |
|-------|------|--------|-------|----------|
| 1 | Foundation & Infrastructure | ● Complete | 3/3 | 100% |
| 2 | Bean Management & Mobile Shell | ● Complete | 2/2 | 100% |
| 3 | Optimization Loop | ○ Not started | 0/0 | 0% |
| 4 | Shot History & Feedback Depth | ○ Not started | 0/0 | 0% |
| 5 | Insights & Trust | ○ Not started | 0/0 | 0% |
| 6 | Analytics & Exploration | ○ Not started | 0/0 | 0% |

## Active Decisions

- Hybrid BayBE parameters confirmed: campaign JSON ~7.5KB (vs 20MB with discrete)
- Per-bean parameter overrides: JSON column on Bean, fingerprint-based campaign invalidation
- Out-of-range historical measurements preserved during campaign rebuild (informative for surrogate model)
- Mobile-first CSS: dark espresso theme, 48px+ touch targets, 375px primary width
- htmx v2.0.4 from CDN for dynamic UI updates
- Active bean stored in httponly cookie (single-user home app, no auth)
- TemplateResponse uses new signature (request, name, context) — no deprecation warnings

## Blockers

- Docker build not verified (daemon not available in dev environment). Dockerfile and docker-compose.yml ready for Unraid deployment.

## Accumulated Context

### Key Technical Decisions
- Stack: FastAPI + Jinja2/htmx + SQLite + Chart.js (from research)
- Single Docker container deployment
- Dual storage: SQLite (source of truth) + JSON files (BayBE campaign cache)
- Measurements-as-source-of-truth pattern (campaigns are rebuildable)
- CPU-only PyTorch to save ~1GB in Docker image
- Hybrid BayBE search space: 5 continuous + 1 categorical parameter
- Campaign file size: ~7.5KB (confirmed, down from 20MB discrete)
- Base.metadata.create_all() in lifespan alongside Alembic (safe — no-op if tables exist)
- Per-bean parameter overrides: Bean.parameter_overrides JSON column, bounds fingerprint (.bounds files) for invalidation detection
- BayBE add_measurements with numerical_measurements_must_be_within_tolerance=False for rebuild scenarios
- Active bean: httponly cookie "active_bean_id", 1-year expiry
- HTML form delete: POST /beans/{id}/delete (forms can't send DELETE method)

### Research Flags
- ~~Phase 1: Investigate discrete vs continuous BayBE parameters~~ RESOLVED: hybrid approach works, 7.5KB files
- Phase 3: Validate htmx + FastAPI integration patterns (HX-Request header detection) — PARTIALLY DONE: htmx integration working in Phase 2
- Phase 5: Research extracting uncertainty/confidence data from BayBE surrogate model

### Todos
None.

## Session Continuity

### Last Session
- **Date:** 2026-02-21
- **What happened:** Implemented per-bean parameter overrides (committed 93cefe2). Planned and executed Phase 2 — mobile shell (Jinja2 + htmx + dark theme CSS), bean CRUD router (list, create, detail, update, delete, activate, parameter overrides), all templates, and comprehensive tests. 43/43 tests passing.
- **Where we left off:** Phase 2 complete. Ready for Phase 3 (Optimization Loop).

### Next Steps
1. Plan Phase 3: Optimization Loop (recommendation UI, taste scoring, failed shots, repeat best)
2. Execute Phase 3
3. After Phase 3: app is usable for daily espresso optimization

---
*State initialized: 2026-02-21*

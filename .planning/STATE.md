# Project State: BrewFlow

**Last updated:** 2026-02-21
**Current phase:** Phase 1 (COMPLETE — all 3 plans executed, 12/12 tests passing)

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Every espresso shot teaches the system something — the app must make it effortless to capture feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** Phase 1 complete, ready for Phase 2

## Phase Status

| Phase | Name | Status | Plans | Progress |
|-------|------|--------|-------|----------|
| 1 | Foundation & Infrastructure | ● Complete | 3/3 | 100% |
| 2 | Bean Management & Mobile Shell | ○ Not started | 0/0 | 0% |
| 3 | Optimization Loop | ○ Not started | 0/0 | 0% |
| 4 | Shot History & Feedback Depth | ○ Not started | 0/0 | 0% |
| 5 | Insights & Trust | ○ Not started | 0/0 | 0% |
| 6 | Analytics & Exploration | ○ Not started | 0/0 | 0% |

## Active Decisions

- Hybrid BayBE parameters confirmed: campaign JSON ~7.5KB (vs 20MB with discrete)
- Fixed setuptools build backend from legacy `_Backend` to `setuptools.build_meta`
- Added package discovery config to exclude `data/` directory

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

### Research Flags
- ~~Phase 1: Investigate discrete vs continuous BayBE parameters~~ RESOLVED: hybrid approach works, 7.5KB files
- Phase 3: Validate htmx + FastAPI integration patterns (HX-Request header detection)
- Phase 5: Research extracting uncertainty/confidence data from BayBE surrogate model

### Todos
None.

## Session Continuity

### Last Session
- **Date:** 2026-02-21
- **What happened:** Phase 1 fully executed — all 3 waves (scaffolding+models, BayBE service, FastAPI+Docker+tests). 12/12 tests passing. FastAPI serves /health endpoint. OptimizerService creates hybrid campaigns, recommends with rounding, persists state.
- **Where we left off:** Phase 1 is complete. All code, tests, and Docker files in place. Ready for Phase 2 planning.

### Next Steps
1. Verify Phase 1 on Unraid (docker compose build && docker compose up)
2. Plan Phase 2: Bean Management & Mobile Shell
3. Execute Phase 2

---
*State initialized: 2026-02-21*

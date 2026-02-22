# Project State: BrewFlow

**Last updated:** 2026-02-22
**Current phase:** Phase 3 (UAT complete — 4/6 tests passed, 2 issues diagnosed, fix plan ready)

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Every espresso shot teaches the system something — the app must make it effortless to capture feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** Phase 3 complete — app is now usable for daily espresso optimization. Ready for Phase 4.

## Phase Status

| Phase | Name | Status | Plans | Progress |
|-------|------|--------|-------|----------|
| 1 | Foundation & Infrastructure | ● Complete | 3/3 | 100% |
| 2 | Bean Management & Mobile Shell | ● Complete | 2/2 | 100% |
| 3 | Optimization Loop | ● Complete | 1/1 | 100% |
| 4 | Shot History & Feedback Depth | ○ Not started | 0/0 | 0% |
| 5 | Insights & Trust | ○ Not started | 0/0 | 0% |
| 6 | Analytics & Exploration | ○ Not started | 0/0 | 0% |

**Overall progress:** ████████░░░░░░░░░░░░ ~40% (6/~15 estimated plans)

## Active Decisions

- Hybrid BayBE parameters confirmed: campaign JSON ~7.5KB (vs 20MB with discrete)
- Per-bean parameter overrides: JSON column on Bean, fingerprint-based campaign invalidation
- Out-of-range historical measurements preserved during campaign rebuild (informative for surrogate model)
- Mobile-first CSS: dark espresso theme, 48px+ touch targets, 375px primary width
- htmx v2.0.4 from CDN for dynamic UI updates
- Active bean stored in httponly cookie (single-user home app, no auth)
- TemplateResponse uses new signature (request, name, context) — no deprecation warnings
- Server-side `pending_recommendations` dict (app.state) for single-user session state — keyed by UUID, cleaned up after recording
- Deduplication via unique `recommendation_id` on Measurement table — safe to re-POST

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
- Failed shots: is_failed=true auto-sets taste=1 in router before DB write
- Best recipe: excludes failed shots (is_failed=False filter), highest taste wins

### Research Flags
- ~~Phase 1: Investigate discrete vs continuous BayBE parameters~~ RESOLVED: hybrid approach works, 7.5KB files
- ~~Phase 3: Validate htmx + FastAPI integration patterns~~ RESOLVED: htmx integration working, HX-Request header detection works
- Phase 5: Research extracting uncertainty/confidence data from BayBE surrogate model

### Todos
- **Backlog: Manual brew input** — User can manually enter all 6 recipe parameters (grind, temp, preinfusion%, dose, yield, saturation) and submit a taste score, bypassing BayBE recommendation. Manual entries are saved to the Measurement table identically to recommended shots (with a flag distinguishing them, e.g. `source="manual"`) and fed into BayBE via `add_measurement` — so human intuition accelerates surrogate model convergence just like optimizer-guided shots. Likely fits in Phase 3 gap fixes (03-02) or as a standalone plan. UI entry point: a "Manual Brew" option on `/brew` alongside "Get Recommendation".

## Session Continuity

### Last Session
- **Date:** 2026-02-22
- **What happened:** UAT for Phase 3. 4/6 tests passed. 2 issues found and diagnosed: (1) Repeat Best not updating — hardcoded recommendation_id in best.html; (2) No UI to clear active bean — missing deactivate endpoint. Fix plan 03-02 created and verified. Backlog item added: manual brew input.
- **Where we left off:** Phase 3 fix plan ready. Execute 03-02 to close gaps, then proceed to Phase 4.

### Next Steps
1. Execute Phase 3 fixes: `/gsd-execute-phase 3 --gaps-only` (plan 03-02)
   - Fix Repeat Best deduplication bug
   - Add active bean deselect UI
   - Consider folding manual brew input into 03-02 or as 03-03
2. Plan Phase 4: Shot History & Feedback Depth
3. After Phase 4: begin Phase 5 (Insights & Trust)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-22*

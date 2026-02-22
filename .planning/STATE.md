# Project State: BrewFlow

**Last updated:** 2026-02-22
**Current phase:** Phase 4 complete — ready for Phase 5 (Insights & Trust).

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Every espresso shot teaches the system something — the app must make it effortless to capture feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** Phase 5 (Insights & Trust) — BayBE confidence signals, trend charts, recommendation explanations.

## Phase Status

| Phase | Name | Status | Plans | Progress |
|-------|------|--------|-------|----------|
| 1 | Foundation & Infrastructure | ● Complete | 3/3 | 100% |
| 2 | Bean Management & Mobile Shell | ● Complete | 2/2 | 100% |
| 3 | Optimization Loop | ● Complete | 2/2 | 100% |
| 4 | Shot History & Feedback Depth | ● Complete | 3/3 | 100% |
| 5 | Insights & Trust | ○ Not started | 0/0 | 0% |
| 6 | Analytics & Exploration | ○ Not started | 0/0 | 0% |

**Overall progress:** ████████████░░░░░░░░ ~65% (12/~17 estimated plans)

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
- **[03-02]** Fresh UUID per `/brew/best` visit for `recommendation_id` — page-visit scoped, not stored
- **[03-02]** `POST /beans/deactivate` placed before `/{bean_id}` wildcard to avoid FastAPI routing ambiguity
- **[03-02]** Cookie deletion test pattern: assert `Max-Age=0` in Set-Cookie header, manually clear client cookie jar
- **[04-01]** `flavor_tags` stored as String (JSON-encoded) not JSON column type — SQLite compatibility
- **[04-01]** Untouched flavor sliders: JS strips `name` attribute on form submit — null not 0 saved to DB
- **[04-01]** Startup ALTER TABLE migration in lifespan for existing databases (inspect + ALTER TABLE)
  - **[04-02]** htmx filter pattern: each select uses hx-include to send sibling field — no submit button needed
  - **[04-02]** Shot enrichment in router: plain dicts with bean_name pre-computed — avoids lazy-load issues post-session
  - **[04-02]** min_taste normalized to int in router when whole number — ensures Jinja `selected` comparison works
  - **[04-03]** HX-Trigger: openShotModal header → JS custom event → dialog.showModal() — keeps JS minimal, no MutationObserver
  - **[04-03]** hx-swap-oob="outerHTML:#shot-{id}" pattern: POST edit returns updated modal + in-place list row update in one response
  - **[04-03]** history/index.html requires {% block scripts %} to load tags.js — openShotModal listener lives there

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
- Feedback panel: collapsible partial `_feedback_panel.html`, included in brew forms; notes + 6 flavor sliders + tag input
  - History view: GET /history (full page) + GET /history/shots (htmx partial); filters by bean + min taste; shot rows with date/taste/grind/failed/notes indicators; modal scaffold for Plan 03
  - Shot detail modal: GET /history/{id} → _shot_modal.html + HX-Trigger: openShotModal; GET/POST /history/{id}/edit → _shot_edit.html pre-populated; POST returns updated modal + oob row swap

### Research Flags
- ~~Phase 1: Investigate discrete vs continuous BayBE parameters~~ RESOLVED: hybrid approach works, 7.5KB files
- ~~Phase 3: Validate htmx + FastAPI integration patterns~~ RESOLVED: htmx integration working, HX-Request header detection works
- Phase 5: Research extracting uncertainty/confidence data from BayBE surrogate model

### Todos
- **Backlog: Manual brew input** — User can manually enter all 6 recipe parameters (grind, temp, preinfusion%, dose, yield, saturation) and submit a taste score, bypassing BayBE recommendation. Manual entries are saved to the Measurement table identically to recommended shots (with a flag distinguishing them, e.g. `source="manual"`) and fed into BayBE via `add_measurement` — so human intuition accelerates surrogate model convergence just like optimizer-guided shots. Likely Phase 4 or standalone plan.

## Session Continuity

### Last Session
- **Date:** 2026-02-22
- **What happened:** Executed plan 04-03 (shot detail modal + edit). Added GET/POST /history/{id} detail and edit endpoints, _shot_modal.html and _shot_edit.html templates, extended tags.js for edit modal IDs and htmx:afterSettle re-init, fixed missing {% block scripts %} in history/index.html. 9 new tests. 87/87 pass. Phase 4 complete.
- **Where we left off:** Phase 4 all 3/3 plans complete. Ready for Phase 5 (Insights & Trust).

### Next Steps
1. Begin Phase 5: Insights & Trust (BayBE confidence signals, trend charts, recommendation explanations)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-22*

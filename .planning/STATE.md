# Project State: BrewFlow

**Last updated:** 2026-02-22
**Current phase:** Phase 6 (Analytics & Exploration) — Complete (2/2 plans done).

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-21)

**Core value:** Every espresso shot teaches the system something — the app must make it effortless to capture feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** Phase 6 complete (2/2 plans). All 6 phases and 22 requirements delivered.

## Phase Status

| Phase | Name | Status | Plans | Progress |
|-------|------|--------|-------|----------|
| 1 | Foundation & Infrastructure | ● Complete | 3/3 | 100% |
| 2 | Bean Management & Mobile Shell | ● Complete | 2/2 | 100% |
| 3 | Optimization Loop | ● Complete | 2/2 | 100% |
| 4 | Shot History & Feedback Depth | ● Complete | 3/3 | 100% |
| 5 | Insights & Trust | ● Complete | 3/3 | 100% |
| 6 | Analytics & Exploration | ● Complete | 2/2 | 100% |

**Overall progress:** ████████████████████ 100% (16/16 plans complete across all 6 phases)

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
  - **[05-01]** get_recommendation_insights acquires _lock independently after recommend() — avoids deadlock
  - **[05-01]** Insights stored as rec["insights"] inside pending_recommendations dict — co-located with recipe params
  - **[05-01]** predicted_range uses em dash (–) not hyphen — typography convention
  - **[05-01]** Prediction threshold: >= 2 measurements for meaningful posterior stats
  - **[05-02]** Convergence detection: rule-based (n < 3 / n < 8 / trend comparison) — no BayBE convergence API exists
  - **[05-02]** Chart.js CDN loaded in `_progress_chart.html` partial (not base.html) — guaranteed script load order
  - **[05-03]** campaign.clear_cache() before campaign.recommend() — prevents UNSPECIFIED.__bool__() crash on 2nd+ recommend calls
  - **[05-03]** switch_after=5 on TwoPhaseMetaRecommender — random exploration lasts 5 shots (was ~1)
  - **[05-03]** Three-phase badge: random (0-4) / bayesian_early-Learning (5-7) / bayesian-Bayesian optimization (8+)
  - **[05-03]** insight-badge-bayesian_early CSS class (green-tinted, #2a3a32 bg, #7ae0a8 text)
  - **[06-02]** Chart.js scatter (not matrix plugin) for heatmap — no extra dependency; per-point `pointBackgroundColor` array from taste score JS function achieves equivalent visual
  - **[06-02]** Taste color thresholds: red (≤3), muted/grey (≤6), amber (≤8), green (9-10) — matches espresso quality intuition
  - **[06-02]** Failed shots as `crossRot` point style (not just color) — accessible distinction for color-blind users
  - **[06-02]** 3-shot minimum threshold for heatmap_data — avoids uninformative near-empty charts
  - **[06-02]** Multi-chart page: Chart.js CDN loaded once by first partial; subsequent partials omit CDN reload

## Blockers

- Docker build not verified (daemon not available in dev environment). Dockerfile and docker-compose.yml ready for Unraid deployment.
- **Pre-existing:** `tests/test_analytics.py::test_analytics_improvement_rate` fails — test doesn't set active bean cookie so global stats view renders instead of bean-specific stats. File is also untracked (not committed by plan 06-01). Needs fix before full test suite is clean.

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
  - Recommendation insights: OptimizerService.get_recommendation_insights() returns phase/explanation/predicted_range; partial `_recommendation_insights.html` shown on recommend page; phase detection via TwoPhaseMetaRecommender.select_recommender()
  - Progress chart: `/insights` page, Chart.js cumulative-best line + shot scatter, 5-state convergence badge, optimizer mode indicator
  - Heatmap: `/insights` page, Chart.js scatter grind×temperature colored by taste (red→amber→green), failed shots as crossRot grey markers, 3-shot threshold for empty state
  - Analytics page: `/analytics`, brew statistics (total shots, avg taste, personal best, improvement rate), cross-bean recipe comparison table

### Research Flags
- ~~Phase 1: Investigate discrete vs continuous BayBE parameters~~ RESOLVED: hybrid approach works, 7.5KB files
- ~~Phase 3: Validate htmx + FastAPI integration patterns~~ RESOLVED: htmx integration working, HX-Request header detection works
- ~~Phase 5: Research extracting uncertainty/confidence data from BayBE surrogate model~~ RESOLVED: `Campaign.posterior_stats()` returns taste_mean/taste_std; `TwoPhaseMetaRecommender.select_recommender()` detects explore vs exploit phase

### Todos
- **Backlog: Manual brew input** — User can manually enter all 6 recipe parameters (grind, temp, preinfusion%, dose, yield, saturation) and submit a taste score, bypassing BayBE recommendation. Manual entries are saved to the Measurement table identically to recommended shots (with a flag distinguishing them, e.g. `source="manual"`) and fed into BayBE via `add_measurement` — so human intuition accelerates surrogate model convergence just like optimizer-guided shots. Likely Phase 4 or standalone plan.

## Session Continuity

### Last Session
- **Date:** 2026-02-22
- **What happened:** Executed plan 06-02 (parameter exploration heatmap). Added Chart.js scatter chart to insights page showing grind vs temperature colored by taste score. Failed shots shown as grey crossRot markers. 3 new tests added (all 9 insights tests pass). Phase 6 now complete (2/2 plans).
- **Where we left off:** All 6 phases complete. 22/22 requirements delivered.

### Next Steps
1. Fix pre-existing `test_analytics_improvement_rate` failure in `tests/test_analytics.py` (needs active bean cookie in test)
2. Commit untracked `tests/test_analytics.py` once fix is applied
3. Deploy to Unraid (Docker build not yet verified)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-22*

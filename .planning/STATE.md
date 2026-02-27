# Project State: BeanBay

**Last updated:** 2026-02-27
**Current phase:** 25-ux-bean-flow (COMPLETE)

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-26)

**Core value:** Every coffee brew teaches the system something — the app must make it effortless to capture that feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** All milestones through v0.3.0 shipped. Ready for next milestone planning or v0.3.0 release.

## Milestone History

| Milestone | Phases | Plans | Status | Date |
|-----------|--------|-------|--------|------|
| v1 MVP | 1-6 | 16 | ✅ Shipped | 2026-02-22 |
| v0.1.0 Release & Deploy | 7-9 | 5 | ✅ Shipped | 2026-02-22 |
| v0.1.1 UX Polish & Manual Brew | 10-12 | 8 | ✅ Shipped | 2026-02-22 |
| v0.2.0 Multi-Method & Intelligence | 13-16 | 13 | ✅ Shipped | 2026-02-23 |
| v0.3.0 Equipment Intelligence & Parameter Evolution | 17-22 | 18 | ✅ Shipped & Archived | 2026-02-26 |

## Current Position

Phase: 25-ux-bean-flow (Plan 2 of 2 complete — PHASE COMPLETE)
Status: Phase 25 complete — UX bean flow polish done
Last activity: 2026-02-27 — Completed 25-02-PLAN.md (analytics per-bean filter + history filter visible)

Progress: All 5 milestones shipped (46 plans across 22 phases) + phase 23 complete (3/3) + phase 24 complete (1/1) + phase 25 complete (2/2)
Ready for: v0.3.0 release (git tag, Docker image, changelog)

## Performance Metrics

**Velocity:**
  - Total plans completed: 46 (v1: 16, v0.1.0: 5, v0.1.1: 8, v0.2.0: 13, v0.3.0: 18)
  - Total phases completed: 22
  - All milestones shipped same week (Feb 22-26, 2026)

## Accumulated Context

### Key Technical Decisions
See: .planning/PROJECT.md (Key Decisions table — 22+ decisions tracked)

### Phase 25 Plan 02 Key Decisions
- **Pass `beans`, `selected_bean_id`, `selected_bean` to analytics template:** Dropdown needs full list; conditional heading needs bean object; selected state needs string ID
- **`comparison=[]` when `bean_id` set:** Skip unnecessary cross-bean DB work; comparison is meaningless when already filtered to one bean
- **`onchange window.location` (not htmx) for analytics bean dropdown:** Full page context changes on filter switch; simpler than targeting a partial
- **History filter: remove collapse entirely:** Simpler than pre-checking checkbox; always-visible card produces the desired behavior without JS or attribute tricks

### Phase 25 Plan 01 Key Decisions
- **Sidebar active-bean indicator removed:** Nav is now navigation-only; `active_bean` variable kept in route contexts for brew page and dashboard (those still use it)
- **Insights: no redirect when no bean, graceful empty state:** Redirect-to-/beans was a UX dead-end; now renders picker prompt immediately
- **bean_id query param with cookie fallback on insights:** Explicit URL selection wins over ambient cookie; enables bookmarking specific bean insights
- **select onchange navigation for bean picker:** No JS dependency needed — native `onchange` fires URL navigation to `/insights?bean_id=`

### Phase 21 Plan 01 Key Decisions
- **Temperature hidden (not "N/A") for cold-brew:** `{% if rec.temperature is not none %}` wraps both the ORM and dict paths — cold-brew shots never show "Temp: None°C"; absence is more accurate than a placeholder
- **steep_time and bloom_weight placed after Dose in recipe card:** Natural brewing order (dose first, then steep/bloom); consistent with how non-espresso methods are documented
- **Method badge shown only for non-espresso on brew index:** Espresso is the implicit default; labeling it would be redundant noise for existing users; badge is `capitalize` for nice display of "french-press" → "french-press"
- **All Phase 20+21 columns added to `_load_shot_detail` in one pass:** Cleaner than incremental additions; model already had all columns — just needed to wire to dict
- **`brew_method` in shot list dicts defaults to `"espresso"`:** Backward compat for legacy shots without brew_setup; informational only for now, enables future display in shot row
- **Shot modal renders all params conditionally, no unconditional None display:** Replaces hardcoded 6-param grid; any method's shot can now display correctly in history

### Phase 20 Plan 03 Key Decisions
- **Hint cards server-rendered as hidden, JS reveals on DOMContentLoaded:** No flash of visible content before JS runs; `hidden` class removed only for params not yet in localStorage
- **head_extra block added to base.html:** Cleanest way to pass bean-id and rec-params to hints.js without inline script globals
- **New-badge uses data-param attrs on .recipe-param divs, injected by hints.js:** Recipe card (`_recipe_card.html`) is shared between best.html and recommend.html; hints.js only runs on recommend.html so badges are contextually correct
- **Categorical params use badge badge-outline badge-sm:** Visual distinction from continuous (number+unit) params; replaces recipe-value-text class

### Phase 20 Plan 02 Key Decisions
- **Two separate fingerprints:** `_param_set_fingerprint` (structural: params added/removed) vs `_bounds_fingerprint` (numeric range changes) — conflating them would miss structural changes or over-trigger rebuilds
- **`rebuild_declined` is Integer (0/1/2):** "remind once then quiet" needs three states — not declined / declined once (gets one more reminder) / permanently silenced
- **`is_campaign_outdated` returns False when no stored fingerprint:** Legacy campaigns predate fingerprinting; nagging users to rebuild legacy campaigns is disruptive
- **`was_rebuild_declined` returns True only at level 2:** Level 1 = declined once but gets one more reminder; level 2 = permanent silence
- **Campaign outdated UX shows diff vs Tier 1 (not vs stored fingerprint):** Simpler — always shows "new params your brewer adds vs baseline"
- **`history.py` delete_batch groups by (method, setup_id):** Multiple measurements under different setups → different campaign keys; flat bean_id grouping was a pre-existing bug

### Phase 20 Plan 01 Key Decisions
- **preinfusion_pct → preinfusion_pressure_pct is a pure column rename (no data conversion):** Column always stored pump pressure %; the conversion formula in f7a2c91b3d04 was factually wrong and removed
- **saturation is NOT deprecated/legacy:** Reworked to active boolean toggle gated by `flow_control_type in (manual_paddle, manual_valve, programmable)`
- **saturation_flow_rate on Brewer (not Measurement):** Fixed ml/s the brewer performs during saturation — not a per-shot BayBE optimization parameter
- **Boolean gate syntax `brewer.has_bloom == True`:** Extended `requires_check()` to handle `== True/False` in addition to `in (...)` membership tests
- **New params: preinfusion_pressure (1.0-6.0 bar), bloom_pause (0.0-10.0s), temp_profile [flat/ramp_up/ramp_down]**
- **Backward-compat re-exports kept in optimizer.py:** Routers can continue importing DEFAULT_BOUNDS etc. from optimizer until Plan 03 removes them (Plan 03 already did)
- **transfer_learning.py: _resolve_bounds no longer needed:** build_parameters_for_setup() accepts overrides directly; import of _resolve_bounds eliminated
- **test_optimizer.py imports from parameter_registry:** ESPRESSO_PARAMS/ESPRESSO_BOUNDS defined at module level from registry functions — tests no longer couple to optimizer's internal constant names

### Phase 19 Plan 03 Key Decisions
- **Router imports from parameter_registry directly:** brew.py, beans.py, history.py no longer import DEFAULT_BOUNDS or BAYBE_PARAM_COLUMNS from optimizer.py
- **"espresso" hardcoded with TODO(Phase 20) comments:** extend_ranges() and history.py param_columns lack brew method context; Phase 20 will make these dynamic
- **transfer_learning.py ghost references fixed:** _build_parameters/_get_param_columns/_resolve_bounds were removed from optimizer.py but transfer_learning.py still referenced them; replaced with build_parameters_for_setup/get_param_columns from parameter_registry

### Phase 19 Plan 01 Key Decisions
- **brewer=None + non-None condition → False (exclude gated params):** Produces legacy 6-param espresso set for backward compat. "No brewer context" = "don't assume advanced capabilities."
- **get_default_bounds() returns all continuous params unfiltered:** Bounds are method-level metadata; capability filtering happens at build_parameters_for_setup() / get_param_columns() time.
- **Phase is additive-only:** optimizer.py unchanged, all 284 existing tests still pass.

### Branding
- **Name:** BeanBay | **Domain:** beanbay.coffee
- **Docker:** ghcr.io/grzonka/beanbay | **Latest release:** v0.2.0

### v0.2.0 Key Design Decisions (from questioning phase)
- **Equipment as context:** Equipment defines the experiment context; BayBE optimizes recipe variables within that context. Comparison between equipment setups happens at analytics level, not optimizer level.
- **Transfer learning via TaskParameter:** BayBE's TaskParameter class enables cross-bean cold-start. Similar beans (by process + variety) provide training data; new bean is the test task. Search spaces must match for transfer learning to work.
- **Bean bags model:** A "coffee" can have multiple bags. Same coffee bought twice shares identity, enabling richer history and transfer learning similarity matching.
- **Beanconqueror import deferred:** Moved to backlog, not in v0.2 scope.

### v0.3.0 Key Design Decisions
- **Capability-driven, not tier-based:** A brewer declares what it can do (capability flags). Tiers are derived for UX progressive disclosure, not stored.
- **Parameter Registry pattern:** `PARAMETER_REGISTRY` dict maps method → parameter definitions. Adding new methods is trivial. Drives dynamic search space building.
- **preinfusion_pct → preinfusion_time:** Physical-unit seconds replaces opaque percentage. Linear migration for existing data.
- **saturation deprecated:** Redundant with preinfusion time (0 = no saturation).
- **Campaign files → DB:** Highest-priority architectural change. Campaign JSON moves to `campaigns` table; pending_recommendations.json moves to `pending_recommendations` table.
- **Frontend Phase 1:** htmx + Tailwind + daisyUI (coffee theme). Low effort, big visual improvement.
- **Espresso advanced params:** pump pressure (bar), flow rate (ml/s), pressure profiling (categorical), pre-infusion (multiple types), bloom/soak, temperature profiling, brew mode (pressure vs flow priority). All conditional on brewer capabilities.

### Phase 14 Key Decisions
- **Retire-only pattern (no deletion):** Preserves history; retired equipment hidden by default, shown with toggle
- **Cascade retire, manual restore:** Retiring a component auto-retires all setups using it; restoring does NOT cascade
- **active_setup_id cookie:** Same pattern as active_bean_id; 1-year expiry; cleared if setup is retired
- **Setup is context for brew page:** Brew action buttons require a bean but setup is optional (for future BayBE integration)

### Phase 15 Key Decisions
- **Campaign key format `bean__method__setup`:** Double-underscore separator avoids collisions with bean IDs that may contain underscores
- **Pour-over param set:** Adds `preinfusion_pct`, `target_yield`, `saturation` (all continuous, ranges tuned for V60-style brewing)
- **Legacy migration at startup:** `migrate_legacy_campaigns()` runs in `main.py` lifespan, transparently maps old `{bean_id}` keys to `{bean_id}__espresso__None`
- **brew_setup_name in shot dict:** Template has no ORM access, so `brew_setup_name` added as plain key to shot dicts in `_build_shot_dicts()` (not ORM relationship access)

### Phase 18 Plan 02 Key Decisions
- **Hardcoded select options in template:** Avoids passing constants through every route that renders the brewer form; values change rarely
- **Native `<details>` for progressive disclosure:** No JavaScript needed; auto-opens in edit mode when non-default capabilities are set
- **Tier badge as `badge badge-sm`:** Compact T1-T5 label next to brewer name; defensive `{% if derive_tier is defined %}` guard

### Phase 17 Plan 02 Key Decisions
- **try/finally/session.close() not context manager:** SessionLocal is a plain sessionmaker, not a context manager. Fixed bug in migration.py where `with session_factory() as session:` would fail at runtime.
- **Transfer metadata in CampaignState.transfer_metadata column:** Replaces .transfer sidecar file. In-memory `_transfer_metadata` dict caches alongside `_cache` and `_fingerprints`.
- **migrate_legacy_campaign_files() as standalone function in migration.py:** OptimizerService no longer has campaigns_dir, so moved from OptimizerService.migrate_legacy_campaigns(). Also renames .transfer sidecar files (bug fix vs original).
- **campaigns_dir = settings.data_dir / 'campaigns' in lifespan:** Avoids the side-effect of settings.campaigns_dir property (which called mkdir). Directory creation is now handled only by migration functions that need it.

### Phase 17 Plan 01 Key Decisions
- **campaign_json as opaque Text blob:** BayBE Campaign.to_json() output stored as raw Text, not decomposed. BayBE controls its own serialization format.
- **Migration functions accept session_factory as argument:** Not importing SessionLocal directly — enables testability with in-memory SQLite (same pattern OptimizerService will use in Plan 02).
- **Idempotency via check-before-insert:** Simple query before each insert, skip if row exists. Clear, auditable. No UPSERT complexity needed for a once-per-startup migration.
- **Original files left as backup after migration:** migrate_campaigns_to_db() and migrate_pending_to_db() do NOT delete the source files. Cleanup is manual after confirming successful migration.

### Phase 17 Plan 03 Key Decisions
- **Per-test ephemeral in-memory SQLite for migration tests:** Migration functions call session.commit()/close() internally, which breaks the shared db_session fixture's rollback isolation. Each migration test gets its own engine+session via migration_engine fixture — no cross-test contamination.
- **Session factory fixture pattern:** `def _test_session_factory(): return db_session` — simple closure lets OptimizerService share the test's DB connection for rollback-based cleanup.

### Phase 16 Key Decisions
- **Transfer metadata as .transfer sidecar file:** Consistent with .bounds sidecar pattern; easy presence-check without loading campaign
- **transfer_metadata stored in pending recommendation dict:** Survives server restarts; show_recommendation reads metadata without extra optimizer call
- **TYPE_CHECKING guard for Bean/Session imports in optimizer.py:** Avoids circular import at module load time; type hints only, not runtime
- **None return when no training data:** Even with matching similar_beans, if no actual DB measurements exist for those beans, returns None gracefully

### Phase 24 Plan 01 Key Decisions
- **Root `/` renders `home.html` for returning users:** Assembles stats, recent_brews, active_bean in-route; `welcome.html` path for zero-bean users unchanged
- **`.stats-grid` CSS reused on dashboard:** Consistent visual language with analytics page; no new CSS classes added
- **Brand nav links changed from `/beans` to `/`:** Both mobile and sidebar brand links now point to home dashboard

### Phase 23 Plan 03 Key Decisions
- **Error divs per-step (`id="step-N-error"`) rather than a single floating error:** Errors anchor visually to the step they belong to; clearer UX than a generic floating message
- **Delegated `change` listener on `wizard-form`** clears all errors on any selection change — no need to wire per-radio handlers
- **`tojson` filter for all four JS maps (BREWERS, GRINDERS, PAPERS, WATER_RECIPES):** Prevents XSS with equipment names containing quotes or apostrophes
- **Submit button `onclick` adds `.loading` + `disabled`:** Prevents double-submit and gives immediate visual feedback before server responds

### Phase 23 Plan 02 Key Decisions
- **`brew_method` defaults to `'espresso'` in templates:** Safe fallback for any legacy path that lacks `method` in context
- **Cold-brew time in minutes (max 2880), others in seconds (max 120 espresso / 1800 other):** Minutes are natural for cold-brew steeping; displaying 7200 seconds would confuse users
- **`/` shows welcome when bean count = 0, redirects when beans exist:** Onboarding for new users; zero extra click for returning users
- **Root test split into two test functions:** New conditional behavior requires independent test coverage for each branch

### Phase 23 Plan 01 Key Decisions
- **Setup filter queries active setups only:** `BrewSetup.is_retired == False` — retired setups hidden from history filter even if historical shots reference them
- **param-info-icon uses primary amber (oklch 65% 0.122 54):** Matches `--color-primary`; 14px circular badge with italic bold "i" replaces near-invisible SVG
- **hx-include cross-filter pattern:** Each dropdown's `hx-include` references all sibling filter names so changing one dropdown reloads shots respecting others

### Phase 22 Plan 06 Key Decisions
- **Custom espresso theme over daisyUI built-in coffee:** Built-in coffee theme had wrong palette; custom theme defined in `@plugin daisyui-theme.mjs` block to exactly match original hand-rolled CSS colors
- **oklch chroma boosted 3x from exact hex conversion:** Exact hex→oklch gives chroma ~0.010 for dark browns, which looks grey at low luminance. Human eye needs ~0.030 chroma for warmth to be perceptible.
- **Lightness set +4% above exact hex:** Exact values (20/27/30%) were slightly too dark for comfortable reading; 24/30/34% approved by user

### Phase 22 Plan 05 Key Decisions
- **Chart.js hex colors left as-is:** Colors like `#c87941`, `#b0a090` are Chart.js dataset config values, not CSS class references — preserved exactly
- **chart-container preserved:** Custom CSS class in input.css provides fixed height for canvas rendering
- **Custom layout classes preserved:** `stats-grid`, `comparison-list`, `comparison-bean`, `recipe-grid` are structural layout classes from input.css

### Phase 22 Plan 04 Key Decisions
- **daisyUI collapse (checkbox-based) replaces JS classList toggle:** Filter panel collapses/expands with zero JavaScript
- **modal-backdrop form[method=dialog]:** Enables click-outside-to-close natively via HTML dialog API
- **Custom CSS classes preserved alongside daisyUI:** recipe-params, flavor-bar, flavor-slider-row, .touched from input.css stay intact
- **Dynamic flavor-bar-fill width as inline style:** Required runtime percentage value; cannot be a Tailwind class

### Phase 22 Plan 03 Key Decisions
- **Native `<dialog>` replaces custom overlay:** `showModal()`/`close()` native browser API; `<form method="dialog" class="modal-backdrop">` handles click-outside natively
- **Keep identifying card classes:** `grinder-card`, `brewer-card`, `paper-card`, `water-card` used by `htmx:afterSwap` handler to `querySelector` and remove empty-state placeholder
- **Keep all wizard custom classes:** `wizard-steps`, `wizard-option-card`, `wizard-step-label`, `wizard-step-connector`, `wizard-step-content` defined in `input.css @layer components`; referenced by wizard JS
- **daisyUI checkbox collapse for equipment sections:** `<input type="checkbox">` allows multiple sections open simultaneously (details/summary does not)

### Phase 22 Plan 02 Key Decisions
- **`empty-state` stays as `id=`:** Used by `list.html`'s JavaScript `querySelector('#empty-state')` — NOT a CSS class; visual styling via Tailwind utilities
- **`_recipe_card.html` left unchanged:** All `recipe-params`/`recipe-param`/etc. already correct via `input.css @layer components`
- **`.touched` opacity pattern preserved:** Flavor sliders start at opacity 0.4 → 1 on interaction; driven by `input.css @layer components`; `oninput` JS preserved verbatim
- **Insight badge arbitrary colors:** `bg-sky-900/50 text-sky-300` (random), `bg-emerald-900/50 text-emerald-300` (bayesian_early), `bg-amber-900/50 text-amber-300` (bayesian)
- **Large brew action buttons:** `min-h-16 rounded-xl` for primary brew actions (phone-at-machine UX); `min-h-12` for standard form submits

### Phase 22 Plan 01 Key Decisions
- **Tailwind standalone CLI (no Node.js):** Downloaded binary in Docker Stage 0 — no npm, no package.json, clean minimal build
- **@plugin ./daisyui.mjs:** daisyUI v5 loaded as standalone .mjs plugin placed alongside input.css at compile time
- **Checkbox drawer replaces JS toggle:** `input[type=checkbox].drawer-toggle` + `label[for=drawer-toggle]` pattern is pure CSS; entire JS IIFE removed from base.html
- **lg:drawer-open:** Desktop permanent sidebar via Tailwind modifier; zero JS needed at any viewport
- **main.css gitignored:** Build artifact generated from input.css; custom component classes kept in @layer components

### Quick Tasks Completed

| ID | Task | Date |
|----|------|------|
| 001 | Fix CI test DB isolation | 2026-02-22 |
| 002 | Style brew select dropdowns to match dark theme | 2026-02-23 |

### Known Bugs

| Bug | Description | When to Fix |
|-----|-------------|-------------|
| B001 | Non-espresso brewer still shows "Espresso" on equipment card | Phase 18 or quick task |

## Session Continuity

### Last Session
- **Date:** 2026-02-27
- **What happened:** Executed Phase 25 Plan 02. Added per-bean filter to analytics page (`?bean_id=` query param), made history filter panel always visible (removed collapse wrapper). 413 tests passing.
- **Where we left off:** Phase 25 complete (both plans done). Ready for v0.3.0 release.
- **Stopped at:** Completed 25-02-PLAN.md
- **Resume file:** None

### Next Steps
1. v0.3.0 release (git tag, Docker image, changelog)
2. Phase 25 post-ship retrospective (optional)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-27 — Phase 25 Plan 02 complete (Phase 25 DONE)*

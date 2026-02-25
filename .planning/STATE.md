# Project State: BeanBay

**Last updated:** 2026-02-26
**Current phase:** Phase 22 — Frontend Modernization daisyUI ✅ COMPLETE

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Every coffee brew teaches the system something — the app must make it effortless to capture that feedback from a phone at the espresso machine and return increasingly better recommendations.
**Current focus:** v0.3.0 — Equipment intelligence, capability-driven parameters, new brew methods, campaign DB migration, frontend modernization

## Milestone History

| Milestone | Phases | Plans | Status | Date |
|-----------|--------|-------|--------|------|
| v1 MVP | 1-6 | 16 | ✅ Shipped | 2026-02-22 |
| v0.1.0 Release & Deploy | 7-9 | 5 | ✅ Shipped | 2026-02-22 |
| v0.1.1 UX Polish & Manual Brew | 10-12 | 8 | ✅ Shipped | 2026-02-22 |
| v0.2.0 Multi-Method & Intelligence | 13-16 | 13 | ✅ Shipped | 2026-02-23 |
| v0.3.0 Equipment Intelligence & Parameter Evolution | 17-22 | TBD | 🔄 Planned | — |

## Current Position

Phase: 22 COMPLETE. Phase 17 COMPLETE. Phase 18 COMPLETE. Wave 1 done.
Plan: 17-01 ✅, 17-02 ✅, 17-03 ✅, 18-01 ✅, 18-02 ✅, 22-01 ✅, 22-02 ✅, 22-04 ✅, 22-05 ✅, 22-06 ✅ — 10 plans complete
Status: Phases 17, 18, 22 all COMPLETE. Next: Phase 19 (parameter evolution) or Phase 20/21.
Last activity: 2026-02-26 — Completed Phase 22 Plan 06 (cleanup + espresso theme human-approved)

Progress: [████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] ~25% (11/~18 v0.3.0 plans)

## Performance Metrics

**Velocity:**
  - Total plans completed: 44 (v1: 16, v0.1.0: 5, v0.1.1: 8, v0.2.0: 13, v0.3.0: 5 so far)
  - Total phases completed: 18 complete
  - All milestones shipped same day (Feb 22-23, 2026)

## Accumulated Context

### Key Technical Decisions
See: .planning/PROJECT.md (Key Decisions table — 22+ decisions tracked)

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
- **Date:** 2026-02-26
- **What happened:** Completed Phase 22 Plan 06 (cleanup + verification). Fixed custom `espresso` daisyUI theme through 3 iterations: (1) wrong oklch values were ~half correct lightness, (2) correct lightness but chroma too low (0.010) so backgrounds looked grey, (3) final: chroma boosted 3x (0.030) + lightness +4% for comfortable warmth. Human visually approved. 284 tests pass, Docker build succeeds.
- **Where we left off:** Phases 17, 18, 22 all complete. Wave 1 of v0.3.0 done.

### Next Steps
1. Plan Phase 19 — Parameter Registry & Dynamic Search Space (depends on Phase 18 ✅)
2. Plan Phase 20 — Advanced Espresso Parameters (depends on Phase 19)
3. Phase 21 — Pour-over / Aeropress parameter sets (depends on Phase 19)

---
*State initialized: 2026-02-21*
*Last updated: 2026-02-25 — Phase 18 COMPLETE (Brewer Capability Model — 2 plans, 34 new tests, 284 total passing)*

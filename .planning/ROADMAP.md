# Roadmap: BeanBay

## Milestones

- ✅ **v1 MVP** — Phases 1-6 (shipped 2026-02-22)
- ✅ **v0.1.0 Release & Deploy** — Phases 7-9 (shipped 2026-02-22)
- ✅ **v0.1.1 UX Polish & Manual Brew** — Phases 10-12 (shipped 2026-02-22)
- ✅ **v0.2.0 Multi-Method & Intelligence** — Phases 13-16 (shipped 2026-02-23)
- 🔄 **v0.3.0 Equipment Intelligence & Parameter Evolution** — Phases 17-22

## Phases

<details>
<summary>✅ v1 MVP (Phases 1-6) — SHIPPED 2026-02-22</summary>

6 phases, 16 plans. Full MVP: bean management, BayBE optimization, feedback flow, charts, dashboard. See milestones/v1-MILESTONE-AUDIT.md.

</details>

<details>
<summary>✅ v0.1.0 Release & Deploy (Phases 7-9) — SHIPPED 2026-02-22</summary>

3 phases, 5 plans. Rebrand to BeanBay, tech debt cleanup, README/LICENSE, GitHub Actions CI/CD, Docker image (ghcr.io/grzonka/beanbay), Unraid CA template, v0.1.0 GitHub release. See milestones/v1-MILESTONE-AUDIT.md.

</details>

<details>
<summary>✅ v0.1.1 UX Polish & Manual Brew (Phases 10-12) — SHIPPED 2026-02-22</summary>

3 phases, 8 plans. Mobile hamburger/drawer nav, desktop sidebar layout, inactive taste slider with submit gate, no-bean prompt on /brew, manual brew input with BayBE integration, manual badge in history, batch delete with campaign rebuild, adaptive parameter range extension. See milestones/v0.1.1-MILESTONE-AUDIT.md.

</details>

<details>
<summary>✅ v0.2.0 Multi-Method & Intelligence (Phases 13-16) — SHIPPED 2026-02-23</summary>

4 phases, 13 plans. Equipment management (grinders, brewers, papers, water), brew setups, multi-method brewing (espresso + pour-over), method-scoped campaigns, enhanced bean metadata (process, variety, bags), cross-brew transfer learning via BayBE TaskParameter. 240 tests.

</details>

---

## v0.3.0 — Equipment Intelligence & Parameter Evolution

**Theme:** Make BeanBay's optimizer aware of what your machine can actually do. Replace hardcoded parameter sets with a capability-driven system where the Brewer declares its capabilities, and BayBE's search space is built dynamically. Add 5 new brew methods, migrate campaign storage to DB, and modernize the frontend with daisyUI.

**Key decisions:**
- Equipment modeling is **capability-driven, not tier-based**. A brewer declares what it can do (capability flags). Tiers are derived for UX progressive disclosure, not stored.
- `preinfusion_pct` (55-100%) is replaced with physical-unit `preinfusion_time` (seconds) + optional `preinfusion_pressure` (bar).
- `saturation` parameter is deprecated — redundant with preinfusion time (0 = no saturation, >0 = saturation).
- Parameter Registry pattern (`PARAMETER_REGISTRY` dict) makes adding new methods trivial and drives dynamic search space building.
- Campaign JSON files migrate into a `campaigns` DB table. `pending_recommendations.json` moves to DB. Data separate from app for easy backups.
- Frontend Phase 1: htmx + Tailwind + daisyUI (coffee theme) — low effort, big visual improvement.

**Research basis:** `.planning/research/ESPRESSO_MACHINE_CAPABILITIES.md`, `.planning/research/BREWING_PARAMETERS.md`

```
Dependency Graph:

   17 (Campaign DB) ─────────────────────────┐
                                              │
   18 (Brewer Caps) → 19 (Param Registry)    ├── v0.3.0
                       ├→ 20 (Espresso Evo)  │
                       └→ 21 (New Methods)    │
                                              │
   22 (Frontend daisyUI) ────────────────────┘

Wave 1: Phases 17, 18, 22 (independent — parallel)
Wave 2: Phase 19 (depends on 18)
Wave 3: Phases 20, 21 (parallel — both depend on 19)
```

### Phase 17: Campaign Storage Migration

**Goal:** Campaign state and pending recommendations live in SQLite instead of JSON files on disk — cleaner data management, atomic operations, easier backup/restore, and data lives separate from app code

**Depends on:** Nothing (independent architectural improvement)
**Requirements:** Campaign JSON → DB table, pending_recommendations.json → DB table, backward-compatible migration, campaign rebuild from measurements still works

**Why this phase:** Campaign files (JSON on disk) are the most fragile part of BeanBay's architecture. Moving them to SQLite enables atomic writes, proper backup (single DB file), and eliminates file I/O race conditions. This is the highest-priority architectural change identified in research. Independent of capability work — can run in parallel.

**What gets built:**
- New `Campaign` SQLAlchemy model: `id`, `campaign_key` (unique), `campaign_json` (text blob), `bounds_fingerprint`, `transfer_metadata` (nullable JSON), `created_at`, `updated_at`
- New `PendingRecommendation` model: `id`, `campaign_key`, `recommendation_data` (JSON), `recommendation_id` (unique), `created_at`
- OptimizerService refactored: reads/writes campaign state to DB instead of `{key}.json` files
- Migration script: reads existing `.json`/`.bounds`/`.transfer` files, inserts into DB
- Startup migration: runs once, moves all campaign files to DB, leaves originals as backup
- `rebuild_campaign` still works (measurements in SQLite are source of truth)
- Data directory becomes optional (only for legacy compatibility during migration)

**Plans:** 3 plans

Plans:
- [x] 17-01-PLAN.md — New models (CampaignState, PendingRecommendation) + migration service
- [x] 17-02-PLAN.md — OptimizerService + brew.py + lifespan refactor to DB-backed storage
- [x] 17-03-PLAN.md — Test fixture updates + test assertions + new migration tests

**Success Criteria:**
1. All campaign state stored in SQLite `campaigns` table
2. Pending recommendations stored in `pending_recommendations` table
3. Existing campaign files migrated automatically on first startup after upgrade
4. OptimizerService works identically (same API, thread-safe, in-memory cache + DB persistence)
5. Campaign rebuild from measurements works as before
6. All existing tests pass; new storage tests added
7. Data directory can be deleted after successful migration (campaigns + pending_recs)

### Phase 18: Brewer Capability Model

**Goal:** Brewers declare their capabilities (temperature control, pre-infusion, pressure profiling, flow control) via structured flags, enabling the optimizer to build equipment-aware search spaces

**Depends on:** Nothing (model extension, independent of campaign storage)
**Requirements:** Capability columns on Brewer, create/edit UI for capabilities, existing brewers get sensible defaults

**Why this phase:** The Brewer model currently has no concept of what a machine can do — it's just a name. The entire capability-driven parameter system depends on brewers having capability flags. This is Phase A from the espresso machine capabilities research: "Low effort, high impact."

**What gets built:**
- Brewer model extended with capability columns:
  - `temp_control_type`: enum `none` / `preset` / `pid` / `profiling` (default: `pid`)
  - `temp_min`, `temp_max`, `temp_step`: floats for temperature range/resolution
  - `preinfusion_type`: enum `none` / `fixed` / `timed` / `adjustable_pressure` / `programmable` / `manual` (default: `none`)
  - `preinfusion_max_time`: float (seconds)
  - `pressure_control_type`: enum `fixed` / `opv_adjustable` / `electronic` / `manual_profiling` / `programmable` (default: `fixed`)
  - `pressure_min`, `pressure_max`: floats (bar)
  - `flow_control_type`: enum `none` / `manual_paddle` / `manual_valve` / `programmable` (default: `none`)
  - `has_bloom`: boolean (default: `false`)
  - `stop_mode`: enum `manual` / `timed` / `volumetric` / `gravimetric` (default: `manual`)
- Alembic migration adding columns with defaults (non-breaking for existing data)
- Brewer create/edit forms updated with capability fields (progressive disclosure — basic fields shown first, advanced expandable)
- `derive_tier(brewer)` utility function for UX tier labels (Tier 1-5, derived not stored)
- Existing brewers default to `temp_control_type="pid"`, all others at `none`/`fixed`/`false`

**Plans:** 2 plans

Plans:
- [x] 18-01-PLAN.md — Brewer model extension + Alembic migration + derive_tier() utility + tests
- [x] 18-02-PLAN.md — Route updates + form progressive disclosure + tier badge + CRUD tests

**Success Criteria:**
1. Brewer model has all capability columns with appropriate defaults
2. Alembic migration runs cleanly on existing databases
3. Existing brewers retain their data and get sensible default capabilities
4. Brewer create/edit UI shows capability fields with progressive disclosure
5. `derive_tier()` correctly classifies machines (Gaggia stock → T1, Sage DB → T3, Decent DE1 → T5)
6. No impact on existing optimizer behavior (capabilities stored but not yet consumed)
7. All existing tests pass; new capability model tests added

### Phase 19: Parameter Registry & Dynamic Search Space

**Goal:** Replace hardcoded `_build_parameters()` with a data-driven `PARAMETER_REGISTRY` that maps method → parameter definitions, enabling dynamic search space construction based on method + brewer capabilities

**Depends on:** Phase 18 (brewer capabilities must exist to drive parameter selection)
**Requirements:** PARAMETER_REGISTRY dict for all 7 methods, capability-aware parameter building, backward-compatible with existing campaigns

**Why this phase:** The current optimizer has hardcoded espresso and pour-over parameter sets. Adding any new method or making espresso parameters equipment-aware requires replacing this with a registry pattern. This is the architectural pivot that unlocks Phases 20 and 21.

**What gets built:**
- `PARAMETER_REGISTRY` dict defining core + advanced parameters for all 7 methods (espresso, pour-over, french-press, aeropress, turkish, moka-pot, cold-brew) with `requires` capability conditions
- `build_parameters_for_setup(method, brewer, overrides)` function replacing `_build_parameters()`
- Dynamic parameter filtering: parameters with `requires` conditions are included/excluded based on brewer capability flags
- Default bounds and rounding rules moved into registry (eliminating separate `DEFAULT_BOUNDS`, `POUR_OVER_DEFAULT_BOUNDS`, etc.)
- Backward compatibility: espresso with `temp_control_type=pid` + no other capabilities → produces same 5+1 params as current
- Pour-over backward compatibility: same 5 params as current
- Method-specific grind range suggestions via `METHOD_GRIND_PERCENTAGES` (percentage-based defaults from grinder range)

**Plans:** 3 plans

Plans:
- [x] 19-01-PLAN.md — Parameter Registry module + comprehensive tests (Wave 1)
- [x] 19-02-PLAN.md — Optimizer + transfer_learning refactor to use registry (Wave 2)
- [x] 19-03-PLAN.md — Router import migration: brew, beans, history (Wave 2, parallel with 19-02)

**Success Criteria:**
1. `PARAMETER_REGISTRY` defines parameters for all 7 brew methods
2. `build_parameters_for_setup()` dynamically builds BayBE parameters from registry + capabilities
3. Espresso campaigns with current default brewer produce identical parameters as before (backward compatible)
4. Pour-over campaigns produce identical parameters as before
5. Parameters correctly filtered by brewer capabilities (e.g., no temperature if `temp_control_type=none`)
6. Grind range suggestions work for all method × grinder combinations
7. All existing tests pass; registry and dynamic building tests added

### Phase 20: Espresso Parameter Evolution

**Goal:** Espresso parameters evolve from the current flat set to a capability-driven model — `preinfusion_pct` renamed to `preinfusion_pressure_pct` (it was always pump pressure %), `saturation` reworked as active boolean toggle (not deprecated), new parameters available based on machine capabilities, campaign transition with rebuild prompt

**Depends on:** Phase 18 (brewer capabilities), Phase 19 (parameter registry for dynamic building)
**Requirements:** Schema corrections per CONTEXT.md overrides, brewer wired into campaign creation, campaign outdated detection, UI hints for new params

**Why this phase:** This is where the research hits the codebase. Users with capable machines (Sage DB, Lelit Bianca, Decent DE1) get parameters their machines actually support. Users with basic machines see only what they can control. Campaigns are now brewer-aware.

**What gets built:**
- `preinfusion_pct` → `preinfusion_pressure_pct` column rename (Alembic migration, NOT a data conversion — always was pump pressure %)
- `saturation` reworked: NOT deprecated, becomes boolean toggle gated by `flow_control_type != 'none'`, `saturation_flow_rate` added to Brewer model
- Missing registry entries: `preinfusion_pressure`, `bloom_pause`, `temp_profile` with capability gates
- Brewer threaded through all campaign creation (optimizer, transfer learning, brew router)
- Campaign structural fingerprinting: detect when brewer capabilities change the param set
- Campaign rebuild prompt: "Your brewer now supports [params]. Rebuild?" with "remind once then quiet"
- Dynamic hidden inputs in best.html (replaces hardcoded 6-param list)
- One-time parameter onboarding hints, "new" badge after campaign rebuild
- Flat ordered recommendation display with categorical badge styling

**Plans:** 3 plans

Plans:
- [ ] 20-01-PLAN.md — Schema & Registry: rename preinfusion_pct, saturation rework, missing registry entries, Alembic migration
- [ ] 20-02-PLAN.md — Brewer wiring: thread brewer into campaigns, structural fingerprint, outdated detection, rebuild prompt
- [ ] 20-03-PLAN.md — Template & UI: dynamic best.html, param hints, "new" badge, flat ordered display

**Success Criteria:**
1. `preinfusion_pct` renamed to `preinfusion_pressure_pct` across entire codebase
2. `saturation` is active boolean toggle gated by `flow_control_type != 'none'` (NOT deprecated)
3. `preinfusion_pressure`, `bloom_pause`, `temp_profile` in registry with correct capability gates
4. Campaigns created with brewer context use capability-appropriate parameters
5. Campaign outdated detection prompts user when brewer capabilities change
6. "Remind once then quiet" behavior for rebuild prompts
7. best.html uses dynamic hidden inputs (works for any param count)
8. One-time onboarding hints for new params, "new" badge after rebuild
9. All existing tests pass; Phase 20 tests added

### Phase 21: New Brew Methods

**Goal:** Add 5 new brew methods (french-press, aeropress, turkish, moka-pot, cold-brew) with method-specific parameters from the registry, extending BeanBay from 2 methods to 7

**Depends on:** Phase 19 (parameter registry must exist to define method parameters)
**Requirements:** New methods in BrewMethod table, new param columns on Measurement, method-specific brew forms, campaign creation for new methods

**Why this phase:** The parameter registry (Phase 19) makes adding new methods trivial — each method is a dict entry. This phase exercises that architecture by adding 5 methods at once. Users who brew with AeroPress, French Press, etc. can now optimize those too.

**What gets built:**
- 5 new BrewMethod seed entries: `french-press`, `aeropress`, `turkish`, `moka-pot`, `cold-brew`
- New nullable columns on Measurement for method-specific params not already present:
  - `water_amount` (ml — french-press, aeropress, turkish, moka-pot, cold-brew)
  - `steep_time` (seconds — french-press, aeropress, cold-brew; minutes stored for cold-brew display)
  - `agitation` (categorical — french-press, aeropress)
  - `num_pours` (discrete — pour-over advanced)
  - `heat_level` (categorical — turkish, moka-pot)
  - `preheat_water` (categorical — moka-pot)
  - `brew_temp` (categorical — cold-brew: fridge/room_temp)
  - `brew_method_variant` (categorical — aeropress: standard/inverted)
  - `num_boils` (discrete — turkish)
- Method-specific brew forms (dynamic, driven by registry):
  - Core params always shown
  - Advanced params in expandable section
- Method selection in equipment → brewer assignment (brewer can be linked to multiple methods)
- Brewer-method association extended: new methods linkable to brewers

**Plans:** 0 plans

Plans:
- [ ] TBD — to be created by /gsd-plan-phase

**Success Criteria:**
1. All 7 brew methods available in BeanBay (espresso, pour-over, french-press, aeropress, turkish, moka-pot, cold-brew)
2. Each method's parameters come from PARAMETER_REGISTRY
3. Method-specific brew forms show correct parameters
4. Campaigns created per method with correct search spaces
5. BayBE optimization works for all new methods (recommend + record cycle)
6. New measurement columns nullable (no impact on existing data)
7. All existing tests pass; new method tests added for at least 3 of the 5 new methods

### Phase 22: Frontend Modernization — daisyUI

**Goal:** Replace the current hand-rolled CSS with Tailwind CSS + daisyUI component library using the built-in `coffee` theme — consistent design system, responsive components, dark mode support, dramatically improved visual polish

**Depends on:** Nothing (independent of backend phases — can run in parallel with any wave)
**Requirements:** Tailwind + daisyUI integrated, all pages restyled, existing functionality preserved, phone-first responsive

**Why this phase:** The current CSS is hand-rolled and growing unwieldy. daisyUI provides a complete component library (buttons, cards, modals, forms, drawers) with a built-in `coffee` theme that matches BeanBay's identity perfectly. This is the "Phase 1" frontend recommendation from research: low effort, big visual improvement.

**What gets built:**
- Tailwind CSS + daisyUI installed and configured
- `coffee` theme activated as default (daisyUI built-in — warm browns, cream accents)
- Base template updated with Tailwind/daisyUI classes
- All pages restyled with daisyUI components:
  - Buttons → `btn`, `btn-primary`, `btn-ghost`
  - Cards → `card`, `card-body`
  - Forms → `input`, `select`, `range`, `toggle`
  - Navigation → `navbar`, `drawer` (replaces custom hamburger/drawer)
  - Modals → `modal` (replaces custom modal pattern)
  - Tables → `table` (replaces custom table styles)
  - Badges → `badge` (replaces custom badge styles)
  - Alerts/toasts → `alert`
- Responsive layout preserved (phone-first, desktop sidebar)
- 48px+ touch targets maintained
- Dark theme via daisyUI theme system (no custom CSS variables needed)
- Custom CSS reduced to layout-specific overrides only

**Plans:** 6 plans

Plans:
- [ ] 22-01-PLAN.md — Infrastructure + Base Layout (Tailwind CLI, input.css, base.html drawer, Dockerfile CSS stage)
- [ ] 22-02-PLAN.md — Beans + Brew Pages (4 beans + 7 brew templates)
- [ ] 22-03-PLAN.md — Equipment Pages (11 templates, modal conversion, wizard)
- [ ] 22-04-PLAN.md — History Pages (6 templates, shot modal, filter collapse)
- [ ] 22-05-PLAN.md — Insights + Analytics Pages (7 templates, Chart.js preserved)
- [ ] 22-06-PLAN.md — Cleanup + Verification (stale class audit, tests, Docker, human verify)

**Success Criteria:**
1. Tailwind CSS + daisyUI installed and configured with `coffee` theme
2. All pages render correctly with new styling
3. Responsive behavior preserved (phone hamburger/drawer, desktop sidebar)
4. Touch targets remain ≥48px on phone
5. Visual consistency across all pages (same component patterns everywhere)
6. Custom CSS reduced by >60% (daisyUI handles most styling)
7. All existing functionality works unchanged
8. All existing tests pass

---

## Phase Ordering Rationale (v0.3.0)

```
Wave 1 (parallel):  17 (Campaign DB)     18 (Brewer Caps)     22 (Frontend daisyUI)
                                                ↓
Wave 2:                                  19 (Param Registry)
                                          ↓            ↓
Wave 3 (parallel):                  20 (Espresso)  21 (New Methods)
```

**Three independent roots:** Phases 17, 18, and 22 have no dependencies on each other and can execute in parallel (Wave 1). Campaign DB migration is pure infrastructure. Brewer capabilities extend the model. Frontend modernization is CSS-only — no backend changes.

**Phase 19 is the architectural pivot:** It depends on Phase 18 (brewer capability flags must exist for capability-driven parameter filtering) but is independent of Phases 17 and 22. The Parameter Registry replaces hardcoded `_build_parameters()` and unlocks both espresso evolution and new methods.

**Phases 20 and 21 are parallel leaves:** Both consume the Parameter Registry from Phase 19 but don't depend on each other. Espresso evolution modifies existing parameters while new methods add entirely new ones — no file conflicts.

**Phase 22 (daisyUI) runs independently** at any point — it only touches templates and static assets.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1 MVP | 16/16 | Complete | 2026-02-22 |
| 7-9 | v0.1.0 | 5/5 | Complete | 2026-02-22 |
| 10-12 | v0.1.1 | 8/8 | Complete | 2026-02-22 |
| 13 | v0.2.0 | 3/3 | Complete | 2026-02-22 |
| 14 | v0.2.0 | 5/5 | Complete | 2026-02-23 |
| 15 | v0.2.0 | 3/3 | Complete | 2026-02-23 |
| 16 | v0.2.0 | 2/2 | Complete | 2026-02-23 |
| 17 | v0.3.0 | 3/3 | Complete | 2026-02-24 |
| 18 | v0.3.0 | 2/2 | Complete | 2026-02-25 |
| 19 | v0.3.0 | 3/3 | Complete | 2026-02-26 |
| 20 | v0.3.0 | 0/3 | Planned | — |
| 21 | v0.3.0 | 0/? | Planned | — |
| 22 | v0.3.0 | 6/6 | Complete | 2026-02-26 |

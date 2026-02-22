# Roadmap: BeanBay

## Milestones

- ✅ **v1 MVP** — Phases 1-6 (shipped 2026-02-22)
- ✅ **v0.1.0 Release & Deploy** — Phases 7-9 (shipped 2026-02-22)
- ✅ **v0.1.1 UX Polish & Manual Brew** — Phases 10-12 (shipped 2026-02-22)
- 🔄 **v0.2.0 Multi-Method & Intelligence** — Phases 13-16

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

### Phase 13: Data Model Evolution & Bean Metadata

**Goal:** Database schema supports equipment, brew methods, brew setups, and enhanced bean metadata — the foundation everything else builds on

**Depends on:** Nothing (schema-first, no UI yet)
**Requirements:** DATA-01, DATA-02, DATA-03, META-01, META-02, META-03, UI-03

**Why this first:** Every subsequent phase (equipment UI, brew method selection, transfer learning) depends on these models existing. The data model is the most expensive thing to change later. This phase also extends the bean model with process/variety/bags — metadata that transfer learning (Phase 16) needs for similarity matching.

**What gets built:**
- New SQLAlchemy models: BrewMethod, Grinder, Brewer, Paper, WaterRecipe, BrewSetup
- Extended Bean model: roast_date, process, variety fields
- New Bag model (multiple bags per coffee, optional cost)
- Measurement updated to reference BrewSetup
- Alembic migrations for all schema changes
- Data migration: existing measurements get a default "espresso" method + default setup
- Bean detail page updated to show/edit enhanced metadata (process, variety, roast date, bags)

**Plans:** 3 plans

Plans:
- [x] 13-01-PLAN.md — New SQLAlchemy models + extended Bean/Measurement + model tests
- [x] 13-02-PLAN.md — Alembic migration with data migration for existing measurements
- [x] 13-03-PLAN.md — Bean metadata UI + bag management on detail page

**Success Criteria:**
1. All new models exist with proper relationships and constraints
2. Alembic migration runs cleanly on existing database with data
3. Existing measurements are associated with a default espresso brew setup
4. Bean create/edit forms include optional process, variety, roast_date fields
5. Bag management (add bag, view bags) works on bean detail page
6. All existing tests pass; new model tests added

### Phase 14: Equipment Management

**Goal:** User can create and manage all equipment types (grinders, brewers, papers, water recipes) and assemble them into brew setups

**Depends on:** Phase 13 (models must exist)
**Requirements:** EQUIP-01, EQUIP-02, EQUIP-03, EQUIP-04, EQUIP-05, EQUIP-06, UI-01

**What gets built:**
- Equipment management section in navigation
- Grinder CRUD: name, dial type (stepped with step size, or stepless)
- Brewer CRUD: name, associated method type
- Paper/filter CRUD: name, optional description
- Water recipe CRUD: name, mineral composition (GH, KH, Ca, Mg, Na, Cl, SO4 — all optional), notes
- Brew setup assembly: pick grinder + brewer + paper + water → named setup
- Grind setting range becomes grinder-specific (not global default)

**Plans:** 5 plans

Plans:
- [ ] 14-01-PLAN.md — Schema migration + model updates (equipment fields, retire lifecycle, brewer-method association)
- [ ] 14-02-PLAN.md — Equipment router, page layout, grinder/brewer CRUD with modal forms
- [ ] 14-03-PLAN.md — Paper/water recipe CRUD + equipment tests
- [ ] 14-04-PLAN.md — Brew setup assembly wizard (multi-step)
- [ ] 14-05-PLAN.md — Retire/restore lifecycle, brew page setup selection, comprehensive tests

**Success Criteria:**
1. User can create, edit, retire/restore grinders with stepped/stepless dial configuration
2. User can create, edit, retire/restore brewers with method association
3. User can create, edit, retire/restore papers/filters
4. User can create, edit, retire/restore water recipes with optional mineral details and notes
5. User can assemble equipment into named brew setups via wizard
6. Equipment pages are accessible from main navigation
7. Phone-first UI with 48px+ touch targets maintained
8. Brew page shows setup + bean selection panels
9. Retire-only lifecycle with auto-cascade to setups

### Phase 15: Multi-Method Brewing & Setup Integration

**Goal:** Brew flow supports multiple methods — user selects a brew setup before getting recommendations, and each method+setup+bean combo gets its own BayBE campaign

**Depends on:** Phase 14 (equipment + setups must exist)
**Requirements:** METHOD-01, METHOD-02, METHOD-03, UI-02, UI-04

**What gets built:**
- Brew method selection in brew flow (espresso, pour-over, other)
- Method-specific parameter sets: espresso keeps current 6 params; pour-over adds bloom (g or % of brew volume)
- Brew setup selection/creation integrated into brew page
- Campaign scoping: campaign key = bean_id + method + setup_id (not just bean_id)
- OptimizerService updated to handle method-specific parameters and setup-scoped campaigns
- Existing data migration: all existing campaigns mapped to default espresso setup
- Backward compatibility: espresso-only users see no disruption

**Success Criteria:**
1. User can select a brew method when starting a brew session
2. Pour-over method shows bloom parameter; espresso shows current 6 params
3. User can select or create a brew setup before getting recommendations
4. Each bean+method+setup combination has its own BayBE campaign
5. Existing espresso data works seamlessly with a default setup
6. History, insights, analytics pages show method/setup context
7. All existing tests pass; new method-specific tests added

### Phase 16: Cross-Brew Transfer Learning

**Goal:** New beans with known properties get smarter first recommendations by learning from similar beans in history, instead of starting from random exploration

**Depends on:** Phase 13 (bean metadata — process, variety for similarity matching), Phase 15 (method-scoped campaigns with matching search spaces)
**Requirements:** INTEL-01, INTEL-02, INTEL-03, INTEL-04

**Why this last:** Transfer learning requires: (a) bean metadata for similarity matching (Phase 13), (b) method-scoped campaigns with matching parameter spaces (Phase 15), and (c) enough historical data structure to find "similar" beans. It's the capstone feature — the key differentiator that makes BeanBay smarter over time.

**What gets built:**
- Similarity matching service: find beans with matching process + variety that have measurements in the same method+parameter configuration
- BayBE TaskParameter integration: training tasks from similar beans, test task for new bean
- Transfer learning activation logic: only when search spaces match and similar beans exist
- UI indicator: show when transfer learning was applied, which beans contributed
- Fallback: graceful degradation to standard random exploration when no similar beans found

**Success Criteria:**
1. When creating a campaign for a bean with process+variety metadata, system finds similar beans
2. Similar beans' measurements are fed as training tasks via BayBE TaskParameter
3. First recommendation for new bean is informed by similar beans (not purely random)
4. Transfer learning only activates when search spaces match
5. User can see transfer learning status and contributing beans
6. Falls back gracefully to random exploration when no matches found
7. Existing beans without metadata work normally (no transfer learning, no errors)

---

## Phase Ordering Rationale

```
Phase 13 (Data Model)
    ↓
Phase 14 (Equipment UI)
    ↓
Phase 15 (Multi-Method Brewing)
    ↓
Phase 16 (Transfer Learning)
```

**Sequential, not parallel.** Each phase builds directly on the previous:
- 13 creates the models that 14 needs to build CRUD for
- 14 creates the equipment/setups that 15 needs for brew flow integration
- 15 creates method-scoped campaigns that 16 needs for matching search spaces
- 16 is the capstone — it needs everything else in place

**Why not parallel phases?** Unlike v0.1.1 where nav and taste UX were independent, every v0.2.0 feature depends on the data model (Phase 13). Equipment UI can't exist without equipment models. Methods can't be selected without setups existing. Transfer learning can't match without metadata + method-scoped campaigns.

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1 MVP | 16/16 | Complete | 2026-02-22 |
| 7-9 | v0.1.0 | 5/5 | Complete | 2026-02-22 |
| 10-12 | v0.1.1 | 8/8 | Complete | 2026-02-22 |
| 13 | v0.2.0 | 3/3 | Complete | 2026-02-22 |
| 14 | v0.2.0 | 0/5 | Pending | — |
| 15 | v0.2.0 | 0/TBD | Pending | — |
| 16 | v0.2.0 | 0/TBD | Pending | — |

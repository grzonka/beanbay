# Roadmap: BeanBay

## Milestones

- ✅ **v1 MVP** — Phases 1-6 (shipped 2026-02-22)
- ✅ **v0.1.0 Release & Deploy** — Phases 7-9 (shipped 2026-02-22)
- ✅ **v0.1.1 UX Polish & Manual Brew** — Phases 10-12 (shipped 2026-02-22)
- ✅ **v0.2.0 Multi-Method & Intelligence** — Phases 13-16 (shipped 2026-02-23)
- ✅ **v0.3.0 Equipment Intelligence & Parameter Evolution** — Phases 17-22 (shipped 2026-02-26)
- ✅ **v0.3.0 Pre-Release Fixes** — Phase 23 (shipped 2026-02-26)

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

<details>
<summary>✅ v0.3.0 Equipment Intelligence & Parameter Evolution (Phases 17-22) — SHIPPED 2026-02-26</summary>

6 phases, 18 plans, 408 tests. Campaign storage migrated from JSON files to SQLite (Phase 17). Brewer capability model with progressive disclosure UI (Phase 18). Data-driven PARAMETER_REGISTRY replacing hardcoded params for all 7 brew methods (Phase 19). Capability-driven espresso parameters with campaign outdated detection (Phase 20). Method-aware templates for french-press, aeropress, turkish, moka-pot, cold-brew (Phase 21). Tailwind + daisyUI frontend with custom espresso theme (Phase 22).

</details>

### Phase 23: v0.3.0 Pre-Release Fixes ✅ COMPLETE

**Goal:** Fix bugs and polish UX issues found during testing — setup wizard broken, method-agnostic terminology, missing history filters, welcome page, and recipe card info icons.
**Plans:** 3 plans

Plans:
- [x] 23-01-PLAN.md — History setup filter + recipe card info icons
- [x] 23-02-PLAN.md — Method-aware brew evaluation + welcome page
- [x] 23-03-PLAN.md — Setup wizard bug fix + UX polish

### Phase 24: Home Dashboard ✅ COMPLETE

**Goal:** Create a home dashboard page for returning users at `/` — showing at-a-glance brew stats, recent brews, active bean info, and quick actions instead of redirecting to the bean list.
**Plans:** 1 plan

Plans:
- [x] 24-01-PLAN.md — Dashboard route + template with stats, recent brews, and quick actions

### Phase 25: UX Bean Flow Polish ⏳ IN PROGRESS

**Goal:** Clean up bean selection UX — remove active-bean from sidebar, add bean pickers to Insights and Analytics, make history filter visible by default, add dashboard intro message.
**Plans:** 2 plans

Plans:
- [ ] 25-01-PLAN.md — Sidebar cleanup, dashboard intro, Insights bean picker
- [ ] 25-02-PLAN.md — Analytics per-bean filter, history filter always visible

---

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
| 20 | v0.3.0 | 3/3 | Complete | 2026-02-26 |
| 21 | v0.3.0 | 1/1 | Complete | 2026-02-26 |
| 22 | v0.3.0 | 6/6 | Complete | 2026-02-26 |
| 23 | v0.3.0 Fixes | 3/3 | Complete | 2026-02-26 |
| 24 | Home Dashboard | 1/1 | Complete | 2026-02-26 |
| 25 | UX Bean Flow Polish | 0/2 | In Progress | — |

# Roadmap: BeanBay

## Milestones

- ✅ **v1 MVP** — Phases 1-6 (shipped 2026-02-22)
- ✅ **v0.1.0 Release & Deploy** — Phases 7-9 (shipped 2026-02-22)
- 🚧 **v0.1.1 UX Polish & Manual Brew** — Phases 10-12 (in progress)

## Phases

<details>
<summary>✅ v1 MVP (Phases 1-6) — SHIPPED 2026-02-22</summary>

6 phases, 16 plans. Full MVP: bean management, BayBE optimization, feedback flow, charts, dashboard. See milestones/v1-MILESTONE-AUDIT.md.

</details>

<details>
<summary>✅ v0.1.0 Release & Deploy (Phases 7-9) — SHIPPED 2026-02-22</summary>

### Phase 7: Rebrand & Cleanup ✓

**Goal:** Rename BrewFlow to BeanBay, remove legacy artifacts, fix tech debt.
**Plans:** 2 plans

Plans:
- [x] 07-01: Rename BrewFlow to BeanBay across codebase
- [x] 07-02: Fix 5 tech debt items

### Phase 8: Documentation & Release ✓

**Goal:** README, LICENSE, GitHub Actions CI, v0.1.0 release.
**Plans:** 2 plans

Plans:
- [x] 08-01: Create README.md
- [x] 08-02: GitHub Actions CI/CD + v0.1.0 release

### Phase 9: Deployment Templates ✓

**Goal:** Docker + Unraid deployment configs.
**Plans:** 1 plan

Plans:
- [x] 09-01: Docker compose + Unraid CA template

</details>

### 🚧 v0.1.1 UX Polish & Manual Brew (In Progress)

**Milestone Goal:** Make the app feel right on every screen, eliminate lazy-default UX traps, and let users record brews without waiting for BayBE recommendations.

#### Phase 10: Responsive Navigation & Layout ✅ COMPLETE

**Goal:** App layout adapts to any screen — hamburger/drawer on mobile, sidebar on desktop, active bean indicator never overflows
**Depends on:** Nothing (CSS/HTML changes, independent of backend)
**Requirements:** NAV-01, NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. On mobile (<768px), navigation is a hamburger icon that opens a drawer/overlay with all nav links — no horizontal tab row visible
  2. On desktop (≥768px), navigation is a fixed sidebar and main content uses full available width — not a 480px centered column
  3. Active bean indicator displays cleanly in both mobile drawer and desktop sidebar without text wrapping or overflow, even with long bean names
  4. All existing pages remain functional and visually correct after layout changes (no broken layouts)
**Plans:** 2 plans

Plans:
- [x] 10-01-PLAN.md — Mobile hamburger + drawer navigation
- [x] 10-02-PLAN.md — Desktop sidebar layout + responsive container

#### Phase 11: Brew UX Improvements

**Goal:** Brew flow interactions are deliberate and guided — no lazy defaults, no silent dead ends
**Depends on:** Nothing (can run parallel to Phase 10)
**Requirements:** UX-01, UX-02, FLOW-01
**Success Criteria** (what must be TRUE):
  1. Taste score slider starts inactive/greyed (opacity 0.4, untouched state) and user cannot submit the brew form until they explicitly touch/interact with it
  2. When "Failed Shot" toggle is activated, taste score is overridden to 1 and the slider becomes disabled — same as existing behavior, preserved through the new inactive-start pattern
  3. When user navigates to /brew without an active bean, they see a clear "Pick a bean first" message with a direct link to bean selection — no silent redirect
**Plans:** 2 plans

Plans:
- [ ] 11-01-PLAN.md — Inactive taste slider + submit gate (UX-01, UX-02)
- [x] 11-02-PLAN.md — No-bean prompt on /brew (FLOW-01)

#### Phase 12: Manual Brew Input

**Goal:** User can record any brew manually with all parameters and a taste score, and it feeds into BayBE optimization
**Depends on:** Phase 11 (taste slider inactive pattern applies to manual form; no-bean prompt pattern reused)
**Requirements:** FLOW-02, FLOW-03, FLOW-04
**Success Criteria** (what must be TRUE):
  1. From the brew page, user can choose "Manual Input" to enter all 6 recipe parameters (grind, temp, preinfusion, dose, yield, saturation) plus taste score and submit
  2. Submitted manual brew is saved and fed to BayBE via add_measurement — it counts as an optimization data point (visible in recommendation reasoning)
  3. Manual brews are visually distinguishable from BayBE-recommended brews in shot history (e.g., badge, icon, or label)
  4. Manual brew form validates inputs within existing parameter ranges before submission
**Plans:** TBD

Plans:
- [ ] 12-01: TBD
- [ ] 12-02: TBD

## Progress

**Execution Order:** 10 → 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-6 | v1 MVP | 16/16 | Complete | 2026-02-22 |
| 7 | v0.1.0 | 2/2 | Complete | 2026-02-22 |
| 8 | v0.1.0 | 2/2 | Complete | 2026-02-22 |
| 9 | v0.1.0 | 1/1 | Complete | 2026-02-22 |
| 10. Responsive Nav & Layout | v0.1.1 | 2/2 | ✅ Complete | 2026-02-22 |
| 11. Brew UX Improvements | v0.1.1 | 1/2 | In progress | - |
| 12. Manual Brew Input | v0.1.1 | 0/TBD | Not started | - |

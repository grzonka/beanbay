# Roadmap: BrewFlow

**Created:** 2026-02-21
**Depth:** comprehensive
**Phases:** 6
**Requirements:** 22 mapped / 22 total

## Phase 1: Foundation & Infrastructure

**Goal:** The project has a working skeleton — database, BayBE integration layer, and Docker container — deployable on the Unraid server and accessible from any device on the network.

**Requirements:**
- INFRA-02: App deploys as a single Docker container on Unraid
- INFRA-03: App is accessible from any device on the local network

**Success Criteria:**
1. Running `docker compose up` starts the app and it responds to HTTP requests on the local network
2. SQLite database is created on first run with beans and measurements tables in a persistent volume
3. BayBE service layer can create a campaign, generate a recommendation, and accept a measurement (verified via automated test, not UI)
4. Campaign state persists across container restarts (JSON files in mounted volume)
5. Stopping and restarting the container preserves all data (DB + campaigns survive)

**Plans:** 3 plans

Plans:
- [ ] 01-01-PLAN.md — Project scaffolding, config, SQLAlchemy models, Alembic migrations
- [ ] 01-02-PLAN.md — BayBE optimizer service layer (hybrid campaigns, thread-safe)
- [ ] 01-03-PLAN.md — FastAPI app skeleton, Docker deployment, comprehensive tests

**Depends on:** None

---

## Phase 2: Bean Management & Mobile Shell

**Goal:** Users can manage their coffee beans from their phone — create beans, select one for optimization, and see their collection — with a mobile-first layout that works with messy hands.

**Requirements:**
- BEAN-01: User can create a new bean with name and optional roaster/origin
- BEAN-02: User can select an active bean for optimization
- BEAN-03: User can view list of all beans with shot counts
- INFRA-01: App has mobile-first responsive layout with large touch targets (48px+)

**Success Criteria:**
1. User can create a new bean by typing a name (and optionally roaster/origin) and tapping a single button, all with one thumb on a phone
2. User can tap a bean from the list to select it as the active bean for optimization
3. User can see all their beans listed with the number of shots pulled for each
4. All interactive elements (buttons, inputs, list items) are at least 48px tall with generous spacing, usable with wet hands on a 375px screen

**Depends on:** Phase 1

---

## Phase 3: Optimization Loop

**Goal:** Users can run the complete espresso optimization cycle from their phone — get a recommendation, brew, rate the shot (or mark it failed), and recall the best recipe to re-brew.

**Requirements:**
- OPT-01: User can request a BayBE-powered recipe recommendation for the active bean
- OPT-02: User can see recommended params (grind, temp, preinfusion%, dose, yield, saturation) in large scannable text
- OPT-03: User can see brew ratio (dose:yield) alongside recommendation
- OPT-04: User can submit a taste score (1-10, 0.5 steps) after brewing
- OPT-05: User can mark a shot as failed (choked/gusher), auto-setting taste to 1
- OPT-06: User can view and re-brew the current best recipe with one tap
- SHOT-03: User can record actual extraction time in seconds

**Success Criteria:**
1. User taps "Get Recommendation" and sees 6 recipe parameters displayed in large, scannable text (readable from arm's length at the espresso machine) with the brew ratio shown alongside
2. After brewing, user can submit a taste score (1-10 in 0.5 steps) and optional extraction time, then immediately get the next recommendation — the full cycle takes under 30 seconds of phone interaction
3. User can mark a shot as "failed" (choked or gusher) with a single prominent toggle, which auto-sets taste to 1 and skips unnecessary inputs
4. User can tap "Repeat Best" to instantly see the highest-rated recipe for this bean, without triggering a new BayBE recommendation
5. Subsequent recommendations demonstrably differ from previous ones — BayBE is learning from submitted measurements

**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Brew router, optimization loop (recommend, record, repeat best)
- [ ] 03-02-PLAN.md — Gap closure: fix Repeat Best dedup, add bean deactivate UI

**Depends on:** Phase 2

---

## Phase 4: Shot History & Feedback Depth

**Goal:** Users can review their brewing history for any bean and optionally capture richer feedback (flavor dimensions, notes) for shots they want to analyze more deeply.

**Requirements:**
- SHOT-01: User can view shot history for a bean in reverse chronological order
- SHOT-02: User can add optional free-text notes to any shot
- VIZ-03: User can optionally rate 6 flavor dimensions (acidity, sweetness, body, bitterness, aroma, intensity) via expandable panel

**Success Criteria:**
1. User can scroll through a reverse-chronological list of all shots for a bean, seeing the recipe parameters, taste score, and timestamp for each
2. User can add free-text notes to a shot (either at submission time or retroactively) without disrupting the quick feedback flow
3. User can expand a flavor profile panel during shot rating to score 6 dimensions (acidity, sweetness, body, bitterness, aroma, intensity) — but this panel is collapsed by default and never blocks the quick taste-score path

**Depends on:** Phase 3

---

## Phase 5: Insights & Trust

**Goal:** Users can see that the optimizer is learning and understand why it suggests what it suggests — building confidence to keep experimenting.

**Requirements:**
- VIZ-01: User can see optimization progress chart (cumulative best taste over time)
- VIZ-02: User can see why a recipe was suggested (exploring vs exploiting)
- VIZ-05: User can see exploration/exploitation balance indicator (how converged the optimizer is)

**Success Criteria:**
1. User can view a chart showing cumulative best taste score over time for a bean, with individual shot scores visible — demonstrating that the optimizer is finding better recipes
2. Each recommendation displays whether BayBE is exploring (trying new parameter regions) or exploiting (refining near known good recipes), in plain language
3. User can see a convergence indicator showing roughly how far along the optimization is (e.g., "Early exploration" → "Narrowing in" → "Likely near optimal")

**Depends on:** Phase 3 (needs recommendation data), Phase 4 (needs history display patterns)

---

## Phase 6: Analytics & Exploration

**Goal:** Users with accumulated data across multiple beans can compare recipes, explore parameter relationships, and see their overall brewing statistics.

**Requirements:**
- VIZ-04: User can see parameter exploration heatmaps (grind x temp colored by taste)
- ANLYT-01: User can compare best recipes across beans side-by-side
- ANLYT-02: User can view brew statistics (total shots, averages, personal records, improvement rate)

**Success Criteria:**
1. User can view a heatmap (or colored scatter) of grind setting vs temperature colored by taste score, revealing where in the parameter space good shots cluster
2. User can see a side-by-side comparison of the best recipe for each bean (parameters + taste score), highlighting how different beans prefer different settings
3. User can view aggregate statistics including total shots pulled, average taste score, personal best, and improvement trend across all beans

**Depends on:** Phase 4 (needs history data), Phase 5 (reuses chart patterns)

---

## Phase Dependencies

```
Phase 1: Foundation & Infrastructure
  └─► Phase 2: Bean Management & Mobile Shell
       └─► Phase 3: Optimization Loop
            ├─► Phase 4: Shot History & Feedback Depth
            │    ├─► Phase 5: Insights & Trust (also depends on Phase 3)
            │    └─► Phase 6: Analytics & Exploration (also depends on Phase 5)
            └─► Phase 5: Insights & Trust
                 └─► Phase 6: Analytics & Exploration
```

**Critical path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6

**Note:** After Phase 3 completes, the app is usable for daily espresso optimization. Phases 4-6 add depth and analytical capability.

## Coverage Validation

| Requirement | Phase | Category |
|-------------|-------|----------|
| BEAN-01 | Phase 2 | Bean Management |
| BEAN-02 | Phase 2 | Bean Management |
| BEAN-03 | Phase 2 | Bean Management |
| OPT-01 | Phase 3 | Optimization Loop |
| OPT-02 | Phase 3 | Optimization Loop |
| OPT-03 | Phase 3 | Optimization Loop |
| OPT-04 | Phase 3 | Optimization Loop |
| OPT-05 | Phase 3 | Optimization Loop |
| OPT-06 | Phase 3 | Optimization Loop |
| SHOT-01 | Phase 4 | Shot Tracking |
| SHOT-02 | Phase 4 | Shot Tracking |
| SHOT-03 | Phase 3 | Shot Tracking |
| VIZ-01 | Phase 5 | Visualization |
| VIZ-02 | Phase 5 | Visualization |
| VIZ-03 | Phase 4 | Visualization |
| VIZ-04 | Phase 6 | Visualization |
| VIZ-05 | Phase 5 | Visualization |
| ANLYT-01 | Phase 6 | Analytics |
| ANLYT-02 | Phase 6 | Analytics |
| INFRA-01 | Phase 2 | Infrastructure |
| INFRA-02 | Phase 1 | Infrastructure |
| INFRA-03 | Phase 1 | Infrastructure |

**Coverage: 22/22 requirements mapped ✓**
**Orphaned: 0**
**Duplicated: 0**

---
*Roadmap created: 2026-02-21*
*Depth: comprehensive — 6 phases derived from 22 requirements across 6 categories*

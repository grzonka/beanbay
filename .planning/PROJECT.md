# BeanBay

## What This Is

A phone-first web application for optimizing coffee recipes using Bayesian optimization (BayBE). Runs on a homeserver (Unraid/Docker) or any machine with Docker, letting the user dial in any coffee bean by iterating: get a recommendation, brew, taste, rate, repeat. BayBE learns from each shot to suggest better recipes over time.

Built with FastAPI + Jinja2/htmx + SQLite + Chart.js. Deployed as a single Docker container.

**Website:** beanbay.coffee

## Core Value

Every coffee brew teaches the system something — the app must make it effortless to capture that feedback from a phone at the espresso machine and return increasingly better recommendations.

## Current State

**Shipped:** v1 MVP, v0.1.0, v0.1.1 (2026-02-22), v0.2.0 (2026-02-23), v0.3.0 (2026-02-26)
**Active milestone:** None — ready for next milestone planning
**Codebase:** ~10K+ LOC (Python, HTML, CSS/JS), 408 tests passing
**Stack:** FastAPI, Jinja2/htmx, SQLite, Chart.js, BayBE, Tailwind/daisyUI, Docker

## Requirements

### Validated

- ✓ Manage coffee beans (create, select, view per-bean history) — v1
- ✓ Get BayBE-powered recipe recommendations with transparent reasoning (why this suggestion, exploration vs exploitation) — v1
- ✓ Quick feedback flow: taste score (1-10) with optional expandable flavor profile (acidity, sweetness, body, bitterness, aroma, intensity) and notes — v1
- ✓ Shot failure tracking (choked/gusher auto-sets taste to 1) — v1
- ✓ Optimization progress visualization (cumulative best over time per bean) — v1
- ✓ Parameter exploration charts (heatmaps/scatter of grind, temp vs taste) — v1
- ✓ Cross-bean comparison (best recipes side by side) — v1
- ✓ Brew statistics dashboard (total shots, averages, personal records) — v1
- ✓ Mobile-first responsive UI that works well with messy hands — v1
- ✓ Docker deployment for homeserver — v1
- ✓ Accessible from anywhere on the local network — v1
- ✓ Mobile hamburger/drawer navigation, desktop sidebar layout — v0.1.1
- ✓ Active bean indicator displays cleanly without overflow in all viewports — v0.1.1
- ✓ Taste score slider starts inactive and must be touched before submission — v0.1.1
- ✓ Failed shot toggle preserves override behavior with new inactive pattern — v0.1.1
- ✓ No-bean prompt on /brew with direct link to bean selection — v0.1.1
- ✓ Manual brew input with all 6 parameters + taste score — v0.1.1
- ✓ Manual brews feed into BayBE optimization via add_measurement — v0.1.1
- ✓ Manual brews visually distinguishable in shot history (blue badge) — v0.1.1

### Active

No active milestone. Ready for next milestone planning.

### Completed (v0.3.0)

- ✓ Campaign DB migration — Campaign JSON files and pending_recommendations.json moved into SQLite tables. Single DB file for all state. Atomic operations, easier backup/restore.
- ✓ Brewer capability model — Brewers declare their capabilities (temperature control, pre-infusion type, pressure profiling, flow control) via structured flags. Capabilities drive parameter selection.
- ✓ Parameter Registry — Data-driven `PARAMETER_REGISTRY` dict mapping method → parameter definitions with capability conditions. Dynamic search space construction for all 7 brew methods.
- ✓ Espresso parameter evolution — `preinfusion_pct` → `preinfusion_pressure_pct`, `saturation` reworked as active boolean toggle. New capability-conditional parameters. Campaign outdated detection with rebuild prompt.
- ✓ New brew methods — Added french-press, aeropress, turkish, moka-pot, cold-brew (5 new methods → 7 total). Method-aware templates and history.
- ✓ Frontend modernization (Phase 1) — Tailwind CSS + daisyUI with custom espresso theme. Phone-first responsive. 408 tests passing.

### Completed (v0.2.0)

- ✓ Multi-method brewing — espresso + pour-over with method-specific parameters
- ✓ Equipment management — grinders, brewers, papers, water recipes with retire/restore lifecycle
- ✓ Brew setups — assemble equipment into named setups; campaign = bean + method + setup
- ✓ Enhanced bean metadata — roast date, process, variety, bags model
- ✓ Cross-brew transfer learning — BayBE TaskParameter for cold-start from similar beans

### Out of Scope (current milestone)

- Multi-user accounts — future milestone
- Community/shared database — future milestone
- Beanconqueror import — backlog (deferred from v0.2)
- SvelteKit migration — Phase 2 frontend (when htmx is outgrown)
- Capacitor native app — Phase 3 frontend (if needed)

## Context

- **Shipped v1:** 6 phases, 16 plans, 108 tests, ~7,632 LOC across Python/HTML/CSS/JS
- **Shipped v0.1.0:** 3 phases, 5 plans. Rebrand, CI/CD, Docker image, Unraid template.
- **Shipped v0.1.1:** 3 phases, 8 plans, 130 tests, ~8,295 LOC. Responsive nav, taste UX, manual brew.
- **Shipped v0.2.0:** 4 phases, 13 plans, 240 tests. Equipment management (grinders, brewers, papers, water), brew setups, multi-method (espresso + pour-over), enhanced bean metadata (bags, process, variety), cross-brew transfer learning via BayBE TaskParameter.
- **Shipped v0.3.0:** 6 phases, 18 plans, 408 tests. Campaign DB migration, brewer capability model, parameter registry (7 brew methods), espresso parameter evolution, method-aware templates, Tailwind + daisyUI frontend.
- **Hardware setup:** Sage Dual Boiler (Slayer mod) + DF83v grinder. Parameters tuned to this specific machine's ranges.
- **BayBE:** Hybrid search space (5+ continuous + categorical), campaigns stored in SQLite. Three-phase optimization: random (0-4 shots) -> Learning (5-7) -> Bayesian optimization (8+).
- **Usage pattern:** Primarily phone at the espresso machine. Quick interactions most days, occasional deep tasting sessions on laptop.
- **Deployment:** Unraid server via Docker. Single container, SQLite for all state (measurements, campaigns, equipment). Also available to any Docker user.
- **Known tech debt:** Non-espresso brewer card shows "Espresso" label (bug B001). Pre-existing LSP type warnings on SQLAlchemy Column types (cosmetic, not functional).

## Constraints

- **Backend language**: Python — BayBE is a Python library, no way around it
- **Optimization engine**: BayBE — already proven, campaign state is JSON-serializable
- **Parameters**: Configurable per brew method — espresso has 6 params (current), pour-over has its own set. Grind setting is grinder-specific.
- **Single user**: Personal use only, no auth needed
- **Self-hosted**: Must run on local server via Docker (Unraid or any Docker host)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Migrate away from Marimo | Marimo requires laptop, no phone support, no remote access | ✓ Good — full webapp shipped |
| Start fresh (no data migration) | Existing data is limited, clean start preferred | ✓ Good — clean schema design |
| Phone-first UI design | Primary usage is at the espresso machine with phone | ✓ Good — dark theme, 48px+ targets |
| Quick + expandable feedback | Fast taste score by default, optional flavor breakdown for deep sessions | ✓ Good — collapsible panel pattern |
| Docker deployment on Unraid | Matches existing homeserver infrastructure | ✓ Good — single container ready |
| Transparent recommendations | Show why BayBE suggests a recipe (exploration vs exploitation, uncertainty) | ✓ Good — 3-phase badges + predicted taste |
| FastAPI + Jinja2/htmx stack | Server-rendered, no SPA complexity, htmx for dynamic updates | ✓ Good — simple, fast, low overhead |
| Hybrid BayBE parameters | 5 continuous + 1 categorical vs all-discrete | ✓ Good — 7.5KB vs 20MB campaign files |
| SQLite as database | Single-user, embedded, no separate DB server | ✓ Good — zero ops overhead |
| Chart.js for visualization | CDN-loaded, no build step, rich chart types | ✓ Good — progress charts + heatmaps working |
| Measurements as source of truth | Campaigns rebuildable from measurement data | ✓ Good — disaster recovery works |
| Rebrand to BeanBay | Better name — "bean" first, "bay" as gathering place + Bayesian hint | ✓ Good — v0.1.0 shipped |
| Hamburger/drawer on mobile | Tab row overflowed with many nav items + long bean name | ✓ Good — clean on all screen sizes |
| Desktop sidebar layout | Centered 480px column wasted widescreen space | ✓ Good — full-width usage |
| Inactive taste slider (data-touched) | Default 7.0 encouraged lazy submissions; "---" label signals unset | ✓ Good — deliberate scoring |
| Inline no-bean prompt | Silent redirect confusing on mobile; keeps user in context | ✓ Good — clear guidance |
| Manual brew with BayBE integration | Users need to record brews outside recommendation flow | ✓ Good — feeds optimization |
| Adaptive parameter ranges | Manual brews may exceed default ranges; confirm + extend | ✓ Good — flexible without breaking optimizer |
| Equipment as context (v0.2) | Equipment defines experiment context; BayBE optimizes recipe variables within that context | Decided — comparison between setups at analytics level |
| Transfer learning via TaskParameter (v0.2) | BayBE TaskParameter enables cross-bean cold-start seeding from similar beans | Validated — feasible with matching search spaces |
| Bean bags model (v0.2) | A "coffee" can have multiple bags; same coffee bought twice shares identity | Decided — supports transfer learning similarity matching |
| Capability-driven brewer model (v0.3) | Brewer declares capabilities (flags), not tiers. Tiers derived for UX only | Decided — drives dynamic parameter selection |
| Parameter Registry (v0.3) | Data-driven dict replaces hardcoded `_build_parameters()` | Decided — adding new methods becomes trivial |
| preinfusion_pct → preinfusion_time (v0.3) | Physical-unit seconds replaces opaque 55-100% percentage | Decided — linear migration for existing data |
| saturation deprecated (v0.3) | Redundant with preinfusion_time (0 = no saturation) | Decided — column kept for history |
| Campaign files → DB (v0.3) | JSON files on disk are fragile; SQLite enables atomic writes and single-file backup | Decided — highest priority architectural change |
| htmx + Tailwind + daisyUI (v0.3) | Phase 1 frontend: low effort, big visual improvement; daisyUI has built-in coffee theme | Decided — SvelteKit deferred to Phase 2 |

---
*Last updated: 2026-02-26 after v0.3.0 milestone archived*

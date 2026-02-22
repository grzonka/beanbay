# Project Milestones: BeanBay

## v0.1.1 UX Polish & Manual Brew (Shipped: 2026-02-22)

**Delivered:** Responsive navigation (mobile hamburger/drawer, desktop sidebar), deliberate taste scoring (inactive slider with submit gate), no-bean prompt, and full manual brew input that feeds directly into BayBE optimization.

**Phases completed:** 10-12 (8 plans total)

**Key accomplishments:**
- Mobile hamburger/drawer navigation replacing overflow-prone tab row, desktop sidebar layout using full screen width
- Taste score slider starts inactive with "---" label --- user must deliberately interact before submitting (no more lazy 7.0 defaults)
- Manual brew input with all 6 parameters + taste score, fed to BayBE via add_measurement as real optimization data
- Manual brews distinguished with blue "Manual" badge in shot history
- Batch delete with automatic BayBE campaign rebuild from remaining measurements
- Adaptive parameter range extension --- users can exceed default ranges with confirmation prompt

**Stats:**
- 17 files modified
- +1,418 / -71 lines of code
- 3 phases, 8 plans, 130 tests (25+ added)
- Completed: 2026-02-22

**Git range:** `feat(10-01)` -> `docs(v0.1.1): milestone audit`

---

## v0.1.0 Release & Deploy (Shipped: 2026-02-22)

**Delivered:** Rebranded from BrewFlow to BeanBay, resolved v1 tech debt, created documentation and CI/CD, published first Docker image and Unraid template.

**Phases completed:** 7-9 (5 plans total)

**Key accomplishments:**
- Full rebrand: BrewFlow -> BeanBay (beanbay.coffee, ghcr.io/grzonka/beanbay)
- Resolved 5 tech debt items from v1 audit
- README.md, LICENSE, GitHub Actions CI/CD pipeline
- Docker image published to ghcr.io with multi-stage build
- Unraid Community Apps XML template for one-click install
- GitHub release v0.1.0 with changelog

**Stats:**
- 3 phases, 5 plans
- Completed: 2026-02-22

**Git range:** `feat(07-01)` -> `feat(09-01)`

---

## v1 MVP (Shipped: 2026-02-22)

**Delivered:** Phone-first espresso optimization app powered by Bayesian optimization --- manage beans, get BayBE-powered recipe recommendations, rate shots, track history, and visualize optimization progress, all from a phone at the espresso machine.

**Phases completed:** 1-6 (16 plans total)

**Key accomplishments:**
- Full BayBE-powered espresso optimization loop --- recommend, brew, rate, repeat --- with hybrid search space (7.5KB campaigns vs 20MB discrete)
- Mobile-first dark espresso theme with 48px+ touch targets, usable with wet hands at the machine
- Shot history with filtering, detail modals, retroactive editing, and expandable 6-dimension flavor profiles
- Insights dashboard with Chart.js progress charts, 3-phase convergence badges, and parameter exploration heatmaps
- Analytics page with aggregate brew statistics and cross-bean best recipe comparison
- Docker deployment ready for Unraid homeserver (FastAPI + SQLite + BayBE in single container)

**Stats:**
- 108 files created/modified
- ~7,632 lines of code (Python, HTML, CSS/JS)
- 6 phases, 16 plans, 108 tests
- 1 day from start to ship (Feb 21-22, 2026)

**Git range:** `docs: initialize project` -> `docs(v1): create milestone audit report`

---

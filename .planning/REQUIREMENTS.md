# Requirements: BeanBay v0.2.0 — Multi-Method Brewing & Intelligence

**Defined:** 2026-02-22
**Core Value:** Every coffee brew teaches the system something — the app must make it effortless to capture that feedback from a phone at the espresso machine and return increasingly better recommendations.

## v0.2.0 Requirements

Requirements for this release. Each maps to roadmap phases.

### Data Model & Schema

- [ ] **DATA-01**: Database schema supports brew methods, equipment (grinders, brewers, papers, water recipes), and brew setups as first-class entities with Alembic migrations
- [ ] **DATA-02**: Bean model extended with optional metadata: roast_date, process, variety. A "coffee" can have multiple bags (same coffee bought twice shares identity) with optional cost per bag
- [ ] **DATA-03**: Measurement model links to brew setup (method + equipment combo) instead of directly to bean only

### Brew Methods

- [ ] **METHOD-01**: User can select a brew method (espresso, pour-over, other) when starting a brew session
- [ ] **METHOD-02**: Each brew method has its own parameter set — espresso keeps current 6 params, pour-over adds bloom (g or % of total brew volume), and other methods are configurable
- [ ] **METHOD-03**: BayBE campaigns are scoped to bean + method + equipment combo — each combination gets its own optimization campaign

### Equipment Management

- [ ] **EQUIP-01**: User can create and manage grinders with name and dial type (stepped with configurable step size, or stepless)
- [ ] **EQUIP-02**: User can create and manage brewers/machines (name, type/method association)
- [ ] **EQUIP-03**: User can create and manage paper/filter types (name, optional description)
- [ ] **EQUIP-04**: User can create and manage water recipes with name, optional mineral composition (GH, KH, Ca, Mg, Na, Cl, SO4), and notes field for how it was made
- [ ] **EQUIP-05**: User can assemble equipment into "brew setups" (grinder + brewer + paper + water) and select a setup when brewing
- [ ] **EQUIP-06**: Equipment is context for optimization, not a BayBE variable — grind setting range is specific to the selected grinder

### Enhanced Bean Metadata

- [ ] **META-01**: Bean creation/edit form includes optional fields: roast_date, process (washed, natural, honey, anaerobic, other), variety (freeform text)
- [ ] **META-02**: A coffee can have multiple "bags" — when buying the same coffee again, user creates a new bag under the existing coffee entry
- [ ] **META-03**: Optional cost per bag for tracking spend

### Cross-Brew Intelligence (Transfer Learning)

- [ ] **INTEL-01**: When creating a new campaign for a bean, the system finds similar beans by process + variety from existing history
- [ ] **INTEL-02**: Similar beans' measurements are fed as training tasks via BayBE's TaskParameter, seeding the new campaign with informed priors instead of random exploration
- [ ] **INTEL-03**: Transfer learning only activates when search spaces match (same method + same parameter configuration) — falls back to standard random exploration otherwise
- [ ] **INTEL-04**: User can see when transfer learning was applied and which beans contributed training data

### UI & Navigation

- [ ] **UI-01**: Equipment management is accessible from navigation — CRUD screens for grinders, brewers, papers, water recipes
- [ ] **UI-02**: Brew setup selection is integrated into the brew flow — user picks or creates a setup before getting recommendations
- [ ] **UI-03**: Bean detail page shows enhanced metadata (process, variety, roast date, bags, cost)
- [ ] **UI-04**: Existing espresso-only users experience a smooth migration — their existing data continues to work, defaulting to "espresso" method with a default equipment setup

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user accounts | v3 vision — no auth needed for personal tool |
| Community/shared database | v3 vision |
| Beanconqueror import | Deferred to backlog — complex format mapping |
| JavaScript framework (React, Vue, etc.) | Staying with Jinja2/htmx |
| PWA/offline mode | BayBE requires server |
| Equipment comparison analytics | v0.2 focuses on setup as context; comparison in future milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 13 | Complete |
| DATA-02 | Phase 13 | Complete |
| DATA-03 | Phase 13 | Complete |
| EQUIP-01 | Phase 14 | Pending |
| EQUIP-02 | Phase 14 | Pending |
| EQUIP-03 | Phase 14 | Pending |
| EQUIP-04 | Phase 14 | Pending |
| EQUIP-05 | Phase 14 | Pending |
| EQUIP-06 | Phase 14 | Pending |
| METHOD-01 | Phase 15 | Pending |
| METHOD-02 | Phase 15 | Pending |
| METHOD-03 | Phase 15 | Pending |
| META-01 | Phase 13 | Complete |
| META-02 | Phase 13 | Complete |
| META-03 | Phase 13 | Complete |
| INTEL-01 | Phase 16 | Pending |
| INTEL-02 | Phase 16 | Pending |
| INTEL-03 | Phase 16 | Pending |
| INTEL-04 | Phase 16 | Pending |
| UI-01 | Phase 14 | Pending |
| UI-02 | Phase 15 | Pending |
| UI-03 | Phase 13 | Complete |
| UI-04 | Phase 15 | Pending |

**Coverage:**
- v0.2.0 requirements: 23 total
- Covered by phases: 23 ✓
- Not yet covered: 0

---
*Defined: 2026-02-22 for v0.2.0 milestone*

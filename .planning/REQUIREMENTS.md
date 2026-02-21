# Requirements: BrewFlow

**Defined:** 2026-02-21
**Core Value:** Every espresso shot teaches the system something — the app must make it effortless to capture feedback from a phone at the espresso machine and return increasingly better recommendations.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Bean Management

- [ ] **BEAN-01**: User can create a new bean with name and optional roaster/origin
- [ ] **BEAN-02**: User can select an active bean for optimization
- [ ] **BEAN-03**: User can view list of all beans with shot counts

### Optimization Loop

- [ ] **OPT-01**: User can request a BayBE-powered recipe recommendation for the active bean
- [ ] **OPT-02**: User can see recommended params (grind, temp, preinfusion%, dose, yield, saturation) in large scannable text
- [ ] **OPT-03**: User can see brew ratio (dose:yield) alongside recommendation
- [ ] **OPT-04**: User can submit a taste score (1-10, 0.5 steps) after brewing
- [ ] **OPT-05**: User can mark a shot as failed (choked/gusher), auto-setting taste to 1
- [ ] **OPT-06**: User can view and re-brew the current best recipe with one tap

### Shot Tracking

- [ ] **SHOT-01**: User can view shot history for a bean in reverse chronological order
- [ ] **SHOT-02**: User can add optional free-text notes to any shot
- [ ] **SHOT-03**: User can record actual extraction time in seconds

### Visualization & Insights

- [ ] **VIZ-01**: User can see optimization progress chart (cumulative best taste over time)
- [ ] **VIZ-02**: User can see why a recipe was suggested (exploring vs exploiting)
- [ ] **VIZ-03**: User can optionally rate 6 flavor dimensions (acidity, sweetness, body, bitterness, aroma, intensity) via expandable panel
- [ ] **VIZ-04**: User can see parameter exploration heatmaps (grind x temp colored by taste)
- [ ] **VIZ-05**: User can see exploration/exploitation balance indicator (how converged the optimizer is)

### Analytics

- [ ] **ANLYT-01**: User can compare best recipes across beans side-by-side
- [ ] **ANLYT-02**: User can view brew statistics (total shots, averages, personal records, improvement rate)

### Infrastructure

- [ ] **INFRA-01**: App has mobile-first responsive layout with large touch targets (48px+)
- [ ] **INFRA-02**: App deploys as a single Docker container on Unraid
- [ ] **INFRA-03**: App is accessible from any device on the local network

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Tracking Enhancements

- **TRACK-01**: User can record actual extraction time in seconds (D9)

### Multi-User

- **MULTI-01**: Multiple users can have separate accounts and data

### Advanced Optimization

- **ADV-01**: User can customize parameter ranges per bean
- **ADV-02**: Offline caching of last recommendation for network blips

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Bluetooth scale integration (A1) | Massive complexity, patchy WebBluetooth support, out of scope per PROJECT.md |
| Timer/stopwatch during brew (A2) | Complexity, phone near splash zone, time is outcome not BayBE parameter |
| Multi-user auth (A3) | v1 is single-user personal tool on homeserver |
| Custom param ranges per bean (A4) | Breaks BayBE campaign architecture, current ranges cover all cases |
| Photo capture per shot (A5) | Unreliable camera in PWA, slows down quick feedback flow |
| Social/sharing features (A6) | Orthogonal to optimization mission, massive scope |
| Bean database/barcode scanner (A7) | Massive effort, minimal payoff for personal tool |
| Grinder/machine control (A8) | No standard API, most home grinders have manual dials |
| Real-time shot graphing (A9) | Requires BLE pressure transducers, machine-specific |
| Full offline/PWA (A11) | Can't run BayBE in browser, server IS the optimization engine |
| SCA flavor wheel (A10) | Too complex for quick phone input, 6-dimension profile sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BEAN-01 | Phase 2 | Pending |
| BEAN-02 | Phase 2 | Pending |
| BEAN-03 | Phase 2 | Pending |
| OPT-01 | Phase 3 | Pending |
| OPT-02 | Phase 3 | Pending |
| OPT-03 | Phase 3 | Pending |
| OPT-04 | Phase 3 | Pending |
| OPT-05 | Phase 3 | Pending |
| OPT-06 | Phase 3 | Pending |
| SHOT-01 | Phase 4 | Pending |
| SHOT-02 | Phase 4 | Pending |
| SHOT-03 | Phase 3 | Pending |
| VIZ-01 | Phase 5 | Pending |
| VIZ-02 | Phase 5 | Pending |
| VIZ-03 | Phase 4 | Pending |
| VIZ-04 | Phase 6 | Pending |
| VIZ-05 | Phase 5 | Pending |
| ANLYT-01 | Phase 6 | Pending |
| ANLYT-02 | Phase 6 | Pending |
| INFRA-01 | Phase 2 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22 ✓
- Unmapped: 0

---
*Requirements defined: 2026-02-21*
*Last updated: 2026-02-21 after initial definition*

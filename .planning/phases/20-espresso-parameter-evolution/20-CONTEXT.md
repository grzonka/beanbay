# Phase 20: Espresso Parameter Evolution - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Espresso parameters evolve from a flat set to a capability-driven model. New parameters (preinfusion_time, brew_pressure, pressure_profile, bloom_pause, flow_rate, temp_profile, brew_mode) become available based on brewer capabilities. `preinfusion_pct` is renamed for clarity, `saturation` is reworked as a boolean toggle. Existing data is preserved and migrated. The brew form dynamically shows parameters appropriate to the brewer's tier.

</domain>

<decisions>
## Implementation Decisions

### preinfusion_pct Correction (ROADMAP OVERRIDE)
- **preinfusion_pct is pump pressure percentage during pre-infusion, NOT a time proxy.** The roadmap's linear mapping (pct → time) is incorrect.
- preinfusion_pct → renamed to `preinfusion_pressure_pct` via Alembic DB column rename. Existing data stays, column just gets a clearer name.
- `preinfusion_time` (seconds) is a **new, separate parameter** — not a replacement for pct. These are independent dimensions.
- No data migration/conversion between the two — they measure different things.

### Saturation Rework (ROADMAP OVERRIDE)
- **Saturation is NOT deprecated.** The roadmap assumed saturation was redundant with preinfusion_time, but that was based on the incorrect pct-as-time assumption.
- Saturation = boolean toggle (on/off): "perform reduced-flow-rate pre-wetting until puck is evenly saturated, or skip."
- `saturation_flow_rate` (ml/s) is a **fixed brewer-level setting** (stored on Brewer model), not a per-shot BayBE optimization parameter. Example: 1.5 ml/s for Sage DB with slayer mod.
- Saturation is gated by `flow_control_type != 'none'` — any brewer with flow control can use it.
- The existing saturation column data is preserved; the parameter type changes from continuous to categorical (boolean) in new campaigns.

### Campaign Transition Behavior
- **Prompted before brew:** When brewer capabilities change such that the campaign's parameter set is outdated, the user sees a prompt: "Your brewer now supports [new params]. Rebuild campaign to include them?" User chooses yes/no.
- **Migrate with recency bias:** On rebuild, old measurements are migrated into the new campaign's training data, but BayBE weights recent data higher via recency weighting. No data is lost.
- **Remind once, then quiet:** If user declines the rebuild prompt, remind them once more next session. After that, stop asking — campaign stays on old params until they choose to rebuild manually.
- **One-time prompted rebuild:** Each capability change triggers at most one prompt cycle (prompt → optional reminder → quiet).

### OpenCode's Discretion
- Exact mechanism for detecting "campaign parameter set is outdated" (fingerprint comparison, param count diff, etc.)
- BayBE recency weighting configuration details
- How to store the "user declined rebuild" state (flag on campaign, session-based, etc.)

</decisions>

<specifics>
## Specific Ideas

- Saturation workflow reference: Sage Dual Boiler with slayer mod — set water flow to ~1.5 ml/s during saturation phase, hold until puck is evenly saturated (can take 20-25 seconds). Binary choice: do it or don't. Can't do "half saturation" because you can't see into the puck.
- For the Sage DB specifically, saturation is practically a toggle because the flow rate is hard to adjust between shots — it's a "set once" brewer setting.

</specifics>

<decisions>
## Recommendation Display Decisions

### Parameter Layout
- **Flat list, ordered by importance:** Core params first (grind, dose, yield, temp), advanced params after. No visual grouping or expandable sections.
- Keeps the recommendation view simple even as param count grows to 6-8.

### New Parameter Onboarding
- **One-time hint per new param:** First time a parameter appears in a recommendation, show a brief dismissible hint explaining what it is (e.g., "Preinfusion Time: 5 sec — hold at low pressure for this duration before ramping up"). Hint disappears after first encounter.

### Categorical vs Continuous Display
- **OpenCode's discretion** on how to visually distinguish categorical (pressure_profile, brew_mode) from continuous (brew_pressure, flow_rate) parameters. General direction: categorical gets a label/badge, continuous gets a number with unit.

### Post-Rebuild Recommendations
- **Badge new params:** After a campaign rebuild, parameters that weren't in the previous campaign get a "new" badge on the first recommendation. Badge goes away after first use.

### OpenCode's Discretion
- Exact hint text per parameter
- Badge styling and dismissal mechanism
- Display format per parameter type (categorical badge vs number+unit)

</decisions>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 20-espresso-parameter-evolution*
*Context gathered: 2026-02-26*

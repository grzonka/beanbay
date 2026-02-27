# Espresso Machine Capabilities Research

**Domain:** BeanBay espresso machine capability modeling
**Researched:** 2026-02-24
**Purpose:** Model the full spectrum of espresso machine controllable parameters so BayBE can optimize within any machine's capabilities — from $300 Bambino to $3500 Decent DE1.

---

## Executive Summary

Espresso machines vary enormously in what they let the user control. BeanBay's current model treats espresso as a flat parameter set (`grind_setting`, `temperature`, `preinfusion_pct`, `dose_in`, `target_yield`, `saturation`) regardless of the machine. This research defines a **capability-driven model** where the Brewer declares what it can do, and BayBE's search space is built dynamically based on those capabilities.

**Key insight:** The right abstraction is NOT "what tier is this machine?" but rather "what can this machine control?" A $400 Gaggia Classic with a $30 dimmer mod gains pre-infusion capability. A $2000 Profitec Pro 600 with a $200 flow control kit gains flow profiling. Capabilities are composable, not tiered.

**Second key insight:** For BayBE optimization, we must avoid over-parameterizing. BayBE works well with 4-6 parameters and <50 observations. Arbitrary pressure curves are not optimizable — but named profile categories and phase-based simplifications are.

---

## 1. Pressure Control

### 1.1 Real-World Machine Behaviors

| Pressure Capability | How It Works | Example Machines | User Controls |
|---------------------|-------------|------------------|---------------|
| **Fixed pump + OPV** | Vibratory pump delivers ~15 bar; OPV bleeds excess back, targeting ~9 bar at group. User cannot adjust. | Gaggia Classic (stock), DeLonghi Dedica, Breville Bambino | Nothing — pressure is fixed |
| **Adjustable OPV** | Same pump, but user can turn a screw/knob to set the OPV between ~6-12 bar. Set once, stays fixed during shot. | Gaggia Classic (OPV mod), Rancilio Silvia (adjustable OPV), many E61 machines | `brew_pressure`: 6.0-12.0 bar (set once per recipe, not varied during shot) |
| **Electronic pump control** | Pump speed is electronically controlled; machine allows setting target pressure. Still fixed during shot. | Breville/Sage Dual Boiler (internal setting), some Lelit machines | `brew_pressure`: 6.0-12.0 bar |
| **Pressure profiling (manual)** | User manually varies flow via paddle/valve during the shot, which indirectly controls pressure. | Lelit Bianca (paddle), La Marzocco GS3 MP (paddle), Profitec Pro 700 + Flow Control Device, E61 + aftermarket flow control | Manual — not parameterizable in BayBE per-second, but the *style* of profile is a categorical choice |
| **Pressure profiling (programmatic)** | Machine executes a user-defined pressure curve automatically. | Decent DE1 (0-13 bar, arbitrary curves), Synesso MVP Hydra, La Marzocco Strada EP | Named profiles as categorical, OR phase-based parameters |
| **Spring lever** | Spring provides naturally declining pressure: ~8-9 bar peak declining to ~2-3 bar over 25-30 seconds. Fixed curve shape. | La Pavoni Europiccola, Flair Signature/Pro, Cafelat Robot, Londinium | `lever_spring_pressure` is implicit — effectively a fixed declining profile |
| **Manual lever** | User controls pressure directly via lever force. Maximum ~9-10 bar, varies by strength. | La Pavoni Professional (manual), Flair 58 (with lever pressure gauge) | Similar to manual paddle — profile shape is categorical |
| **Robotic lever (motorized piston)** | A motorized piston replaces the traditional pump AND the manual lever. The piston pushes water directly through the puck — no pump vibration, immediate puck saturation, and full programmatic control of pressure AND flow curves. Replicates lever-style water distribution (even, gravity-like) with digital precision and repeatability. Can emulate any other machine type's profile. | Meticulous Espresso | Full programmatic control: pressure profiling, flow profiling, temperature profiling, auto-stop via gravimetric scale. Community profiles replicate Slayer, Italian, turbo, bloom, and lever-style declining shots. Key innovation: flow-priority mode where the machine targets a constant flow rate (e.g., 2.2 ml/s) and pressure becomes a *consequence* of puck resistance — the inverse of traditional machines. |

### 1.2 Real-World Pressure Values

| Context | Typical Range | Notes |
|---------|---------------|-------|
| Traditional espresso | 9 bar | The "standard" since the 1960s |
| Modern specialty | 6-9 bar | Lower pressures trending for light roasts |
| Turbo shots | 4-6 bar | Very fine grind, fast flow, low pressure — gaining popularity |
| Blooming espresso | 2-4 bar preinfusion → 6-9 bar extraction | Decent DE1 blooming profiles |
| Slayer-style | 2-3 bar for 20-30s → 9 bar | Very slow pre-brew ramp |
| Spring lever peak | 8-9 bar declining to 2-3 bar | Natural exponential decay curve |
| Absolute maximum | 13 bar | Decent DE1 max; most machines cap at 9-10 bar via OPV |
| Minimum meaningful | 1-2 bar | Line pressure pre-infusion; below this, very little flow |

### 1.3 How to Model for BayBE

**Recommendation: Two-layer model — `brew_pressure` (continuous) + `pressure_profile` (categorical)**

**Layer 1: `brew_pressure`** (NumericalContinuous, 5.0-13.0 bar, rounding 0.5)
- For machines with adjustable pressure (OPV, electronic, or profiling)
- Represents the *peak* or *primary extraction* pressure
- Machines without adjustable pressure: omit this parameter (fixed at ~9 bar)

**Layer 2: `pressure_profile`** (Categorical)
- Only for machines with pressure profiling capability
- Values: `flat`, `declining`, `ramp_up`, `blooming`, `slayer_prebrew`, `lever`
- The optimizer learns which profile category works best per bean
- Users with manual profiling (paddle/lever) select the profile they're aiming for

**Why NOT parameterize the full curve:**
- An arbitrary pressure curve is a function, not a scalar — BayBE optimizes scalar parameters
- With <50 shots per bean, you cannot learn a curve shape
- Named profiles capture 95% of what people actually do
- Even Decent DE1 users predominantly use a few named profile templates

**Phase-based alternative for Tier 5 machines:**
For users who want more granularity than named profiles, offer phase-specific pressures:
- `preinfusion_pressure`: 1.0-5.0 bar
- `extraction_pressure`: 5.0-13.0 bar  
- `decline_target`: 2.0-7.0 bar (ending pressure for declining profiles)

This gives BayBE 3 continuous params instead of 1 categorical, which is reasonable if the machine supports it. But this should be **optional** — most users should use the categorical profile.

---

## 2. Flow Control

### 2.1 Real-World Machine Behaviors

| Flow Capability | How It Works | Example Machines | User Controls |
|-----------------|-------------|------------------|---------------|
| **No flow control** | Pump delivers whatever flow results from pressure vs puck resistance. Typical: 1.5-3.5 ml/s for a well-prepared puck at 9 bar. | Most machines | Nothing — flow is a consequence |
| **Flow rate limiting** | Needle valve or paddle restricts maximum flow. User sets a limit, actual flow may be less if puck resists. | Lelit Bianca paddle, Profitec Flow Control Device, E61 flow control kits | Qualitative (open/restricted/closed) — not a precise ml/s target |
| **Programmatic flow targeting** | Machine targets a specific flow rate in ml/s and adjusts pump pressure to maintain it. | Decent DE1 (flow profiling mode, 0-8 ml/s), Synesso MVP Hydra | `flow_rate`: 1.0-6.0 ml/s |
| **Flow priority mode** | Machine lets user choose whether pressure or flow takes priority when they conflict. | Decent DE1 (flow vs pressure priority toggle) | Categorical: `pressure_priority` / `flow_priority` |

### 2.2 Real-World Flow Values

| Context | Flow Rate | Notes |
|---------|-----------|-------|
| Normal espresso | 1.5-2.5 ml/s | Standard 9-bar flat profile |
| Turbo shot | 3.0-5.0 ml/s | High flow, low pressure, fine grind |
| Blooming pre-infusion | 0.5-1.5 ml/s | Low-pressure initial soak |
| Slayer-style pre-brew | 0.5-1.0 ml/s | Very restricted flow for 20-30s |
| Lever decline phase | 1.0-0.3 ml/s | Declining as spring pressure drops |
| Maximum pump delivery | 6.0-8.0 ml/s | No puck resistance (backflush, etc.) |

### 2.3 How to Model for BayBE

**Recommendation: `flow_rate` (NumericalContinuous) only for machines with programmatic flow targeting**

- Range: 1.0-6.0 ml/s, rounding 0.5
- Only include in search space if `brewer.has_flow_profiling == True`
- For machines with manual flow control (paddle/valve): model as categorical flow behavior, not ml/s
  - Use `pressure_profile` categorical values instead (which implicitly encode flow behavior)

**Why NOT model manual flow control as a continuous variable:**
- Manual paddle position is not reproducible to ml/s precision
- Users think in terms of "fully open", "half restricted", "barely cracked"
- The pressure profile categorical already captures this: "flat" = fully open, "slayer_prebrew" = restricted then open, etc.

---

## 3. Pre-infusion

### 3.1 Real-World Pre-infusion Types

| Pre-infusion Type | How It Works | Typical Parameters | Example Machines |
|-------------------|-------------|-------------------|------------------|
| **None** | Pump goes straight to full pressure. First drops appear in 3-8 seconds depending on grind. | N/A | Gaggia Classic (stock), many basic machines |
| **Timed (pump)** | Pump runs at reduced pressure for a set duration, then ramps to full. | Duration: 0-15 seconds; Pressure: ~3-5 bar (not usually adjustable) | Breville/Sage Dual Boiler (0-15s), Breville Barista Pro (0-15s), Lelit Elizabeth |
| **Line pressure** | Machine opens solenoid to water mains pressure (~2-3 bar) before engaging pump. Plumbed-in machines only. | Duration: varies (user-set or until first drip detected); Pressure: 2-3 bar (mains dependent) | La Marzocco Linea Mini (plumbed), E61 machines with plumbing, La Marzocco GS3 |
| **Pump at adjustable pressure** | Pump runs at a user-set lower pressure for a duration. | Duration: 0-30s; Pressure: 1.0-5.0 bar (both adjustable) | Decent DE1 (fully programmable), Lelit Bianca (via paddle), La Marzocco Strada |
| **Bloom / soak** | Wet puck at low pressure, **pause** (no flow for X seconds), then extract. The pause lets the puck absorb water evenly before extraction pressure. | Bloom duration: 5-30s; Bloom pressure: 2-4 bar; Pause: 5-30s | Decent DE1 (blooming profile), some manual lever routines |
| **Slayer-style pre-brew** | Very slow flow (0.5-1.0 ml/s) for 20-40 seconds at low pressure, then transition to full extraction. | Duration: 20-40s; Flow: 0.5-1.0 ml/s; Pressure: 2-3 bar | Slayer (commercial), Decent DE1 (Slayer profile), Lelit Bianca (paddle restricted) |
| **Auto-detect (first drip)** | Machine runs low-pressure water until sensors detect flow through puck, then ramps to extraction pressure. | Automatic — no user control over duration. | Decent DE1 ("move on if" conditions), some Nuova Simonelli commercial machines |

### 3.2 Pre-infusion Modeling for BayBE

**Current model: `preinfusion_pct` (55-100%)**

This is a percentage-based proxy. It works but is semantically unclear — 100% means "max pre-infusion" but doesn't map to any physical quantity.

**Recommended replacement model:**

| Parameter | BayBE Type | Range | Rounding | Requires | Notes |
|-----------|-----------|-------|----------|----------|-------|
| `preinfusion_time` | NumericalContinuous | 0-30 seconds | 1.0 | `has_preinfusion` | Duration of pre-infusion. 0 = no pre-infusion. |
| `preinfusion_pressure` | NumericalContinuous | 1.0-5.0 bar | 0.5 | `has_adjustable_preinfusion_pressure` | Pressure during pre-infusion. Only for machines that allow adjusting PI pressure separately. |
| `bloom_pause` | NumericalContinuous | 0-30 seconds | 5.0 | `has_bloom` | Pause duration after initial wetting (bloom soak). 0 = no pause. |

**Migration from `preinfusion_pct`:**
- `preinfusion_pct` = 100 → `preinfusion_time` = max (15s on SDB)
- `preinfusion_pct` = 55 → `preinfusion_time` = ~0s (effectively none)
- Linear mapping: `preinfusion_time = ((pct - 55) / 45) * max_preinfusion_seconds`

**Why this is better:**
- Physical units (seconds, bar) are meaningful to the user
- Directly maps to machine controls
- BayBE can learn "8 seconds of pre-infusion at 3 bar is optimal for this light roast"
- The percentage was an abstraction that obscured the actual parameter

---

## 4. Temperature

### 4.1 Real-World Temperature Control

| Temp Capability | How It Works | Accuracy | Example Machines |
|----------------|-------------|----------|------------------|
| **No control (thermostat)** | Simple bimetallic thermostat. Cycles on/off around a setpoint. Actual brew temp varies ±5-10°C depending on shot timing. | ±5-10°C | Gaggia Classic (stock), DeLonghi EC-series, Mr. Coffee |
| **Preset temperatures** | PID-controlled but only offers 3-5 preset levels (Low/Med/High or similar). | ±2-3°C | Breville Bambino Plus (3 presets: ~88/92/96°C), Nespresso machines |
| **PID continuous** | Digital PID controller. User sets exact temperature (typically 0.5-1°C resolution). Maintains ±0.5-2°C during shot depending on group design. | ±0.5-2°C | Breville/Sage Dual Boiler (0.5°C steps, 86-96°C), Lelit Bianca (1°C steps), Rancilio Silvia + PID mod, La Marzocco Linea Mini (1°C steps), Profitec Pro 600/700 |
| **Temperature profiling** | PID can change target temperature *during* the shot. User programs a temperature curve. | ±1°C | Decent DE1 (0.1°C resolution, 20-105°C, arbitrary curves), Synesso MVP Hydra |

### 4.2 Temperature Ranges in Practice

| Context | Range | Notes |
|---------|-------|-------|
| Light roast espresso | 92-96°C | Higher temp for harder, denser beans |
| Medium roast espresso | 90-93°C | Mid-range |
| Dark roast espresso | 86-90°C | Lower temp to avoid harsh bitterness |
| Declining temp profile | 96°C → 88°C | Decent DE1 style — hot start, cool finish |
| Blooming profile | 80-85°C bloom → 92°C extraction | Low-temp bloom to reduce astringency |
| Absolute range (all machines) | 85-96°C | Practical brewing range (not including specialty outliers) |
| Decent DE1 full range | 20-105°C | Includes non-coffee uses (tea, etc.) |

### 4.3 Group Head Thermal Stability

This matters for understanding temperature accuracy, but is **not a BayBE parameter** — it's equipment context:

| Group Type | Thermal Stability | Warm-up Time | Notes |
|------------|-------------------|--------------|-------|
| **Saturated group** | Excellent (±0.5°C) | 20-30 min | Water circulates through group head constantly. La Marzocco, Decent DE1. |
| **E61 group** | Good after warm-up (±1-2°C) | 30-45 min | Large brass thermal mass, slow to heat. Most prosumer machines. |
| **Thermocoil/thermoblock** | Moderate (±2-3°C) | 30-90 seconds | Fast heat-up but less stable. Breville/Sage machines. |
| **Single boiler** | Poor (±5-10°C) | 15-20 min | Must temperature surf. Gaggia Classic, Rancilio Silvia. |

### 4.4 How to Model for BayBE

**Recommendation: Keep current `temperature` parameter but make it capability-conditional**

| Capability | BayBE parameter | Range | Notes |
|------------|----------------|-------|-------|
| No temp control | Omit `temperature` from search space | N/A | Machine has fixed temp; can't optimize what you can't control |
| Preset temps | `temperature` as CategoricalParameter | values from presets (e.g., `["88", "92", "96"]`) | Few discrete choices |
| PID continuous | `temperature` as NumericalContinuous | `[brewer.temp_min, brewer.temp_max]`, rounding 0.5-1.0°C | Current model, works well |
| Temp profiling | `temperature` + `temp_profile` as Categorical | Base temp + profile shape | See below |

**Temperature profiling (Tier 5 only):**
- Add `temp_profile` categorical: `flat`, `declining`, `rising`, `bloom_cool`
- `temperature` becomes the *starting* temperature
- BayBE learns which combination of start temp + profile shape works best
- This keeps the search space manageable (1 continuous + 1 categorical vs. parameterizing a curve)

### 4.5 Temperature Offset Consideration

Some machines display **boiler temperature**, not **group head temperature**. The offset can be 5-15°C depending on group design. This is NOT something BayBE needs to know — the user sets what their machine displays, and the optimizer learns within that frame of reference. As long as the user consistently uses their machine's displayed temperature, BayBE will optimize correctly. The absolute Celsius value doesn't matter for optimization; relative consistency does.

---

## 5. Dose (Input)

### 5.1 Ranges by Basket

| Basket | Dose Range | Common Default | Notes |
|--------|-----------|----------------|-------|
| Single (7-12g) | 7.0-12.0g | 9.0g | Rarely used for optimization — hard to make consistent |
| Double (14-20g) | 14.0-20.0g | 18.0g | The standard for home espresso |
| Triple (20-22g) | 20.0-22.0g | 21.0g | Commercial-style, or dense light roasts |
| Precision baskets (VST/IMS) | Same as above but more consistent | Same as above | Better flow uniformity, higher extraction ceilings |

### 5.2 How to Model for BayBE

**Current model works well.** `dose_in` as NumericalContinuous (14.0-22.0g, rounding 0.5g).

The user's basket size constrains the range. This should be controlled via `parameter_overrides` on the Bean or as default bounds inferred from BrewSetup context.

**Recommendation:** No change needed. Bean-level `parameter_overrides` for `dose_in` already handles basket constraints.

---

## 6. Yield / Output

### 6.1 Stop Mechanisms

| Mechanism | Accuracy | How It Works | Example Machines |
|-----------|----------|-------------|------------------|
| **Manual stop** | ±2-5g | User watches stream and presses button. Highly dependent on reaction time. | Most home machines |
| **Timed stop** | ±3-8g | Machine stops after X seconds. Yield varies with grind/puck. | Breville Bambino (programmed duration) |
| **Volumetric** | ±2-3g | Machine measures water volume dispensed. Doesn't account for retention. | Many commercial machines, Decent DE1, Breville machines |
| **Gravimetric** | ±0.5g | Machine has built-in scale; stops at target weight in cup. | Decent DE1 + Decent Scale, La Marzocco Leva, some high-end commercial |

### 6.2 How to Model for BayBE

**Current model works well.** `target_yield` as NumericalContinuous.

Regardless of stop mechanism, the user **records actual yield in grams** (weighed on a scale). The stop mechanism determines precision, not the parameter itself.

**Recommendation:** No change. The user may *target* 36g yield but actually get 35g or 37g. We record what they actually got, and BayBE optimizes the *target* for next time.

---

## 7. Ratio

Derived from `target_yield / dose_in`. Not a machine parameter. Not a BayBE parameter. Displayed in UI for user reference.

| Ratio | Name | Style | Notes |
|-------|------|-------|-------|
| 1:1 – 1:1.5 | Ristretto | Very concentrated, syrupy | Rare in modern specialty |
| 1:1.5 – 1:2 | Normale | Classic Italian | Traditional espresso |
| 1:2 – 1:2.5 | Lungo-style moderne | Modern specialty standard | Most common for light-medium roasts |
| 1:2.5 – 1:3 | Lungo | Extended, more dilute | For specific flavor profiles |
| 1:3 – 1:5 | Allongé / turbo | Very extended | Turbo shots, Scandinavian style |

---

## 8. Basket / Portafilter

### 8.1 Types

| Type | Impact on Extraction | Target User | BayBE Relevance |
|------|---------------------|-------------|-----------------|
| **Pressurized** | Creates artificial crema; very forgiving of grind inconsistency. Limits extraction ceiling. | Beginners, pre-ground coffee | Context (recorded), not optimized |
| **Non-pressurized (standard)** | Flow depends entirely on grind, dose, tamp. Standard for dialing in. | Most home baristas | Context (recorded), not optimized |
| **Precision (VST/IMS)** | Tighter hole tolerances, more uniform flow. Higher extraction ceilings. | Enthusiasts | Context (recorded), not optimized |

### 8.2 How to Model for BayBE

**Recommendation: NOT a BayBE search parameter.** Basket type is equipment context, not a recipe variable. Users don't swap baskets between shots when dialing in. Record it in BrewSetup as metadata but don't include in search space.

Could add `basket_type` as Categorical on Brewer or BrewSetup if we want to track it: `["pressurized", "standard", "precision"]`. But it does not go into BayBE.

---

## 9. Other Parameters

### 9.1 Puck Preparation (Not BayBE Parameters)

These are technique variables, not machine capabilities. They affect consistency but are hard to control precisely:

| Factor | Values | Impact | BayBE? |
|--------|--------|--------|--------|
| **WDT (distribution)** | yes/no | Reduces channeling significantly | No — always recommended, not optimizable |
| **Tamping pressure** | ~15-20 kg (with calibrated tamper, effectively standardized) | Minimal if consistent | No — standardize and forget |
| **Puck screen** | yes/no | Reduces channeling, can slow flow slightly | Could be categorical context but not worth optimizing |
| **Leveling tool** | yes/no | Complements WDT | No |

### 9.2 What About Channeling?

Channeling is an **outcome** (failure mode), not a controllable parameter. It's caused by poor puck prep, uneven grind, incorrect dose, or too-fine grind. The user can note it (`channeling_observed: boolean` in observations) but BayBE doesn't optimize against it directly — it shows up as low taste scores which BayBE learns to avoid.

---

## 10. Machine Capability Matrix

### 10.1 Comprehensive Machine Survey

| Machine | Price | Temp Control | Temp Range | Pre-infusion | Pressure Control | Pressure Range | Flow Control | Stop Mode | Group Type |
|---------|-------|-------------|------------|-------------|-----------------|---------------|-------------|-----------|------------|
| **DeLonghi Dedica** | $250 | Thermostat | ~92°C fixed | None | Fixed OPV (15 bar pump, ~9 bar at group) | Fixed | None | Manual | Thermoblock |
| **Breville Bambino Plus** | $400 | 3 presets | ~88/92/96°C | Auto 10s (fixed) | Fixed OPV ~9 bar | Fixed | None | Timed | Thermojet |
| **Gaggia Classic Pro** | $450 | Thermostat (PID moddable) | ~92°C ±8°C (PID: 85-96°C) | None (dimmer mod available) | Fixed OPV (adjustable via mod) | 9 bar (mod: 6-12) | None | Manual | Single boiler |
| **Rancilio Silvia** | $750 | Thermostat (PID moddable) | ~95°C ±8°C (PID: 85-96°C) | None | Fixed OPV (adjustable) | 9 bar (adjustable 6-12) | None | Manual | Single boiler |
| **Rancilio Silvia Pro X** | $1,300 | PID | 85-96°C (1°C) | None | Fixed OPV | 9 bar | None | Manual | Dual boiler |
| **Breville Barista Express** | $600 | PID | ~88/92/96°C (presets) | Timed (0-15s, preset) | Fixed OPV | 9 bar | None | Manual/Volumetric | Thermocoil |
| **Breville Barista Pro** | $800 | PID | 86-96°C (1°C) | Timed (0-15s) | Fixed OPV | 9 bar | None | Manual/Volumetric | Thermojet |
| **Lelit MaraX** | $1,200 | PID (brew priority mode) | 88-96°C (X-temp: 1-3 priority modes) | None | Fixed OPV | 9 bar | None | Manual | HX + Thermosiphon |
| **Breville/Sage Dual Boiler** | $1,500 | PID | 86-96°C (0.5°C) | Timed (0-15s) | Adjustable (internal dial, 6-12 bar) | 6-12 bar | None | Manual/Volumetric | Dual boiler (saturated-ish) |
| **Profitec Pro 600** | $1,800 | PID | 85-96°C (1°C) | None (E61 preinfusion from thermal siphon) | OPV adjustable | 9 bar (adjustable) | None (FC kit available) | Manual | Dual boiler, E61 |
| **Lelit Bianca** | $2,200 | PID (LCC) | 85-96°C (1°C) | Via paddle (manual) | Manual via paddle | 0-9 bar (manual, approximate) | Manual paddle | Manual | Dual boiler, E61 |
| **Profitec Pro 700 + FC** | $2,500 | PID | 85-96°C (1°C) | Via flow control device | Manual via FC device | 0-9 bar (manual, approximate) | Manual needle valve | Manual | Dual boiler, E61 |
| **La Marzocco Linea Mini** | $3,500 | PID | 85-96°C (0.5°C) | Line pressure (plumbed) | Fixed OPV | 9 bar | None | Manual | Saturated group |
| **La Marzocco GS3 MP** | $6,500 | PID | 85-96°C (0.5°C) | Via paddle | Manual via paddle | 0-9 bar (manual) | Manual paddle | Manual | Saturated group |
| **Decent DE1** | $3,000 | PID + profiling | 20-105°C (0.1°C) | Fully programmable (time, pressure, flow, auto-detect first drip) | Fully programmable (electronic) | 0-13 bar | Programmable (ml/s target) | Volumetric / Gravimetric (with scale) | Proprietary saturated |
| **Meticulous Espresso** | $3,500 | PID + profiling | Programmable (0.1°C) | Fully programmable (robotic piston) | Fully programmable (robotic piston) | 0-10+ bar | Programmable (ml/s target, flow profiling) | Gravimetric (built-in Acaia scale) | Robotic lever (motorized piston) |
| **Flair 58** | $500 | External (kettle) | N/A (depends on kettle) | Manual (lever) | Manual lever pressure | 0-10 bar (lever force) | Manual (lever) | Manual | Direct lever |
| **Cafelat Robot** | $400 | External (kettle) | N/A | Manual (lever) | Manual lever pressure | 0-9 bar | Manual (lever) | Manual | Direct lever |

### 10.2 Capability Flags Derived from Matrix

Based on the survey, these are the meaningful boolean/enum capabilities:

```
has_pid_temp:                  bool    # Can set exact temperature?
temp_control_type:             enum    # none / preset / pid / profiling
temp_min:                      float   # Min settable temp (°C)
temp_max:                      float   # Max settable temp (°C)
temp_resolution:               float   # Step size (°C): 0.1, 0.5, 1.0

has_preinfusion:               bool    # Any form of pre-infusion?
preinfusion_type:              enum    # none / fixed / timed / adjustable_pressure / programmable / manual_lever
preinfusion_max_time:          float   # Max PI duration (seconds)

has_adjustable_pressure:       bool    # Can change extraction pressure from default?
pressure_control_type:         enum    # fixed / opv_adjustable / electronic / manual_profiling / programmable
pressure_min:                  float   # Min achievable pressure (bar)
pressure_max:                  float   # Max achievable pressure (bar)

has_flow_control:              bool    # Any form of flow control?
flow_control_type:             enum    # none / manual_paddle / manual_valve / programmable
flow_min:                      float   # Min targetable flow (ml/s) — only for programmable
flow_max:                      float   # Max targetable flow (ml/s) — only for programmable

has_bloom:                     bool    # Supports bloom/soak (pause during PI)?

stop_mode:                     enum    # manual / timed / volumetric / gravimetric
```

---

## 11. Machine Tiers (UX Progressive Disclosure)

While capabilities are composable (not strictly tiered), UX benefits from progressive disclosure. Here are pragmatic tiers based on which BayBE parameters the user sees:

### Tier 1 — Basic
**BayBE parameters: 3** (`grind_setting`, `dose_in`, `target_yield`)

Machines: DeLonghi Dedica, basic Gaggia Classic, Breville Bambino (without temp presets), budget machines, Flair Neo.

User experience: "Set your grind, dose, and stop the shot at the target weight." Temperature is fixed. No pre-infusion control. Pressure is fixed.

### Tier 2 — Temperature Control
**BayBE parameters: 4** (add `temperature`)

Machines: Breville Barista Express/Pro, Rancilio Silvia + PID, Lelit MaraX, Gaggia Classic + PID mod.

User experience: Adds temperature slider within machine's range. PID allows reproducible temp adjustments.

### Tier 3 — Pre-infusion
**BayBE parameters: 5** (add `preinfusion_time`)

Machines: Breville/Sage Dual Boiler, Lelit Elizabeth, Profitec Pro 600 (E61 pre-infusion), some mid-range PID machines with timed PI.

User experience: Adds pre-infusion duration control. Machine handles low-pressure phase before extraction.

### Tier 4 — Pressure & Flow Control  
**BayBE parameters: 5-6** (add `brew_pressure` and/or `pressure_profile`)

Machines: Lelit Bianca, Profitec Pro 700 + FC, La Marzocco GS3 MP, E61 + flow control kit, Flair 58.

User experience: Adds pressure adjustment and/or profile type selection. Manual profiling machines choose a profile category.

### Tier 5 — Full Programmable Control
**BayBE parameters: 6-8** (add `flow_rate`, `preinfusion_pressure`, `bloom_pause`, `temp_profile`)

Machines: Decent DE1, Synesso MVP Hydra, La Marzocco Strada EP.

User experience: Every phase of the shot is parameterizable. Machine executes profiles automatically.

### Tier Assignment Rule

Tier is NOT stored — it's **derived** from the brewer's capability flags:

```python
def derive_tier(brewer):
    if brewer.flow_control_type == "programmable":
        return 5
    if brewer.has_flow_control or brewer.pressure_control_type in ("manual_profiling", "programmable"):
        return 4
    if brewer.has_preinfusion and brewer.preinfusion_type in ("timed", "adjustable_pressure"):
        return 3
    if brewer.has_pid_temp:
        return 2
    return 1
```

---

## 12. Equipment Capability vs Recipe Variable

### 12.1 The Distinction

| Type | Definition | Set When | Changes How Often | Examples |
|------|-----------|----------|-------------------|---------|
| **Equipment capability** | "What CAN my machine do?" | Once per brewer setup | Rarely (only when modding or changing equipment) | `has_pid_temp`, `pressure_max`, `preinfusion_type` |
| **Recipe variable** | "What SHOULD I set for this bean?" | Per bean × setup combination | Every shot (BayBE optimizes) | `temperature`, `preinfusion_time`, `brew_pressure` |
| **Equipment constraint** | Bounds on recipe variables derived from capabilities | Derived from capabilities | Updates when capabilities change | `temperature: [85, 96]`, `brew_pressure: [6, 12]` |

### 12.2 How They Connect

1. User registers Brewer with capability flags → stored once
2. Capability flags determine which recipe variables appear in BayBE search space
3. Capability ranges (`temp_min`, `temp_max`, `pressure_min`, `pressure_max`) set BayBE parameter bounds
4. Bean-level `parameter_overrides` can narrow (but not widen) these bounds for specific beans
5. BayBE optimizes recipe variables within the intersection of (capability bounds ∩ user overrides)

### 12.3 Example Flow

**User: Lelit Bianca**
```
Brewer capabilities:
  has_pid_temp: true
  temp_min: 85, temp_max: 96
  has_preinfusion: true, preinfusion_type: manual_paddle
  has_adjustable_pressure: true, pressure_control_type: manual_profiling
  pressure_min: 0, pressure_max: 9
  has_flow_control: true, flow_control_type: manual_paddle

→ BayBE search space includes:
  grind_setting: [user's grinder bounds]
  dose_in: [14, 22] (or bean override)
  target_yield: [25, 60] (or bean override)
  temperature: [85, 96]
  pressure_profile: ["flat", "declining", "ramp_up", "blooming"]  ← categorical
  # preinfusion_time NOT included (manual paddle = not precisely settable)
  # flow_rate NOT included (manual paddle = not precisely settable)
```

**User: Decent DE1**
```
Brewer capabilities:
  has_pid_temp: true, temp_control_type: profiling
  temp_min: 20, temp_max: 105
  has_preinfusion: true, preinfusion_type: programmable
  preinfusion_max_time: 60
  has_adjustable_pressure: true, pressure_control_type: programmable
  pressure_min: 0, pressure_max: 13
  has_flow_control: true, flow_control_type: programmable
  flow_min: 0.5, flow_max: 8.0
  has_bloom: true

→ BayBE search space includes:
  grind_setting: [user's grinder bounds]
  dose_in: [14, 22]
  target_yield: [25, 60]
  temperature: [86, 96] (narrowed by bean override from machine's full 20-105 range)
  preinfusion_time: [0, 30]
  preinfusion_pressure: [1, 5]
  brew_pressure: [6, 13]
  pressure_profile: ["flat", "declining", "ramp_up", "blooming", "slayer_prebrew"]
  # flow_rate: [1.0, 4.0] — could include but may over-parameterize
```

**User: Gaggia Classic (stock)**
```
Brewer capabilities:
  has_pid_temp: false
  has_preinfusion: false
  has_adjustable_pressure: false
  has_flow_control: false

→ BayBE search space includes:
  grind_setting: [user's grinder bounds]
  dose_in: [14, 22]
  target_yield: [25, 60]
  # That's it — 3 parameters. Simple, but effective.
```

---

## 13. Recommended Data Model Changes

### 13.1 Brewer Model Extension

```python
class Brewer(Base):
    __tablename__ = "brewers"

    # Existing fields
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    is_retired = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # NEW: Temperature capabilities
    temp_control_type = Column(String, default="pid")
    # Values: "none", "preset", "pid", "profiling"
    temp_min = Column(Float, nullable=True)   # °C (null = no temp control)
    temp_max = Column(Float, nullable=True)
    temp_step = Column(Float, nullable=True, default=1.0)  # Resolution in °C

    # NEW: Pre-infusion capabilities
    preinfusion_type = Column(String, default="none")
    # Values: "none", "fixed", "timed", "adjustable_pressure", "programmable", "manual"
    preinfusion_max_time = Column(Float, nullable=True)  # seconds

    # NEW: Pressure capabilities
    pressure_control_type = Column(String, default="fixed")
    # Values: "fixed", "opv_adjustable", "electronic", "manual_profiling", "programmable"
    pressure_min = Column(Float, nullable=True)  # bar
    pressure_max = Column(Float, nullable=True, default=9.0)  # bar

    # NEW: Flow capabilities
    flow_control_type = Column(String, default="none")
    # Values: "none", "manual_paddle", "manual_valve", "programmable"

    # NEW: Bloom capability
    has_bloom = Column(Boolean, default=False)

    # NEW: Stop mode
    stop_mode = Column(String, default="manual")
    # Values: "manual", "timed", "volumetric", "gravimetric"

    # Existing relationship
    methods = relationship("BrewMethod", secondary="brewer_methods", backref="brewers")
```

### 13.2 Dynamic Parameter Building

Replace the current hardcoded `_build_parameters()` with a capability-driven builder:

```python
def _build_espresso_parameters(
    brewer: Brewer | None,
    bounds: dict[str, tuple[float, float]],
) -> list:
    """Build BayBE espresso parameters based on brewer capabilities."""
    params = [
        # Always included (core 3)
        NumericalContinuousParameter(name="grind_setting", bounds=bounds["grind_setting"]),
        NumericalContinuousParameter(name="dose_in", bounds=bounds["dose_in"]),
        NumericalContinuousParameter(name="target_yield", bounds=bounds["target_yield"]),
    ]

    # Temperature — only if machine has PID or better
    if brewer is None or brewer.temp_control_type in ("pid", "profiling"):
        temp_bounds = bounds.get("temperature", (86.0, 96.0))
        if brewer and brewer.temp_min is not None:
            temp_bounds = (
                max(temp_bounds[0], brewer.temp_min),
                min(temp_bounds[1], brewer.temp_max or 96.0),
            )
        params.append(NumericalContinuousParameter(
            name="temperature", bounds=temp_bounds
        ))
    elif brewer and brewer.temp_control_type == "preset":
        # Offer preset temps as categorical
        presets = _get_temp_presets(brewer)  # e.g., ["88", "92", "96"]
        params.append(CategoricalParameter(
            name="temperature", values=presets, encoding="OHE"
        ))

    # Pre-infusion time — if machine supports timed/adjustable/programmable PI
    if brewer and brewer.preinfusion_type in ("timed", "adjustable_pressure", "programmable"):
        max_pi = brewer.preinfusion_max_time or 15.0
        pi_bounds = bounds.get("preinfusion_time", (0.0, max_pi))
        params.append(NumericalContinuousParameter(
            name="preinfusion_time", bounds=pi_bounds
        ))

    # Pre-infusion pressure — only if adjustable
    if brewer and brewer.preinfusion_type in ("adjustable_pressure", "programmable"):
        params.append(NumericalContinuousParameter(
            name="preinfusion_pressure", bounds=bounds.get("preinfusion_pressure", (1.0, 5.0))
        ))

    # Brew pressure — if adjustable (OPV, electronic, or profiling)
    if brewer and brewer.pressure_control_type in ("opv_adjustable", "electronic", "programmable"):
        p_min = brewer.pressure_min or 6.0
        p_max = brewer.pressure_max or 12.0
        params.append(NumericalContinuousParameter(
            name="brew_pressure", bounds=bounds.get("brew_pressure", (p_min, p_max))
        ))

    # Pressure profile — if machine supports any form of profiling
    if brewer and brewer.pressure_control_type in ("manual_profiling", "programmable"):
        profiles = ["flat", "declining", "ramp_up", "blooming"]
        if brewer.pressure_control_type == "programmable":
            profiles.append("slayer_prebrew")
        params.append(CategoricalParameter(
            name="pressure_profile", values=profiles, encoding="OHE"
        ))

    # Bloom pause — if machine supports bloom
    if brewer and brewer.has_bloom:
        params.append(NumericalContinuousParameter(
            name="bloom_pause", bounds=bounds.get("bloom_pause", (0.0, 30.0))
        ))

    # Flow rate — only for programmable flow control
    if brewer and brewer.flow_control_type == "programmable":
        params.append(NumericalContinuousParameter(
            name="flow_rate", bounds=bounds.get("flow_rate", (1.0, 5.0))
        ))

    return params
```

### 13.3 Default Bounds Extension

```python
ESPRESSO_DEFAULT_BOUNDS = {
    # Core (always)
    "grind_setting":          (15.0, 25.0),
    "dose_in":                (14.0, 22.0),
    "target_yield":           (25.0, 60.0),
    # Tier 2+
    "temperature":            (86.0, 96.0),
    # Tier 3+
    "preinfusion_time":       (0.0, 15.0),
    # Tier 4+
    "brew_pressure":          (6.0, 12.0),
    "preinfusion_pressure":   (1.0, 5.0),
    # Tier 5
    "bloom_pause":            (0.0, 30.0),
    "flow_rate":              (1.0, 5.0),
}

ESPRESSO_ROUNDING = {
    "grind_setting":          0.5,
    "dose_in":                0.5,
    "target_yield":           1.0,
    "temperature":            0.5,
    "preinfusion_time":       1.0,
    "brew_pressure":          0.5,
    "preinfusion_pressure":   0.5,
    "bloom_pause":            5.0,
    "flow_rate":              0.5,
}
```

### 13.4 Measurement Table Extension

Add nullable columns for new parameters (wide-table approach, consistent with existing pattern):

```python
class Measurement(Base):
    # ... existing columns ...

    # NEW: Additional espresso parameters (all nullable for backward compatibility)
    preinfusion_time = Column(Float, nullable=True)      # seconds
    preinfusion_pressure = Column(Float, nullable=True)   # bar
    brew_pressure = Column(Float, nullable=True)          # bar
    pressure_profile = Column(String, nullable=True)      # categorical value
    bloom_pause = Column(Float, nullable=True)            # seconds
    flow_rate = Column(Float, nullable=True)              # ml/s
    temp_profile = Column(String, nullable=True)          # categorical value
```

### 13.5 Migration from `preinfusion_pct`

The existing `preinfusion_pct` (55-100) needs to coexist during migration:

1. Keep `preinfusion_pct` column (don't drop — historical data)
2. Add new columns alongside
3. For new brews with capable machines, use new parameters
4. For machines without PI capability, omit both old and new PI params
5. Migration mapping for existing data:
   - `preinfusion_pct = 55` → `preinfusion_time = 0` (effectively no PI)
   - `preinfusion_pct = 100` → `preinfusion_time = 15` (max on Sage DB)
   - Linear interpolation between

---

## 14. Key Questions Answered

### Q1: How to model pressure profiling for BayBE?

**Answer: Categorical `pressure_profile` + optional continuous `brew_pressure`.**

Named profiles (`flat`, `declining`, `ramp_up`, `blooming`, `slayer_prebrew`, `lever`) as a CategoricalParameter. The optimizer learns which profile type works best for each bean. `brew_pressure` (continuous) represents the peak/extraction pressure.

For Tier 5 machines wanting more granularity, add `preinfusion_pressure` and optionally `decline_target` as continuous params. But keep the total parameter count ≤8 for BayBE efficiency.

### Q2: How to model flow control?

**Answer: `flow_rate` (NumericalContinuous) only for programmable machines.**

Manual paddle/valve flow control is better captured by the `pressure_profile` categorical (which implicitly encodes flow behavior). Only machines like the Decent DE1 that can target a specific ml/s should have `flow_rate` in the search space.

### Q3: What's the minimal parameter set per tier?

| Tier | Parameters | Count |
|------|-----------|-------|
| 1 (Basic) | `grind_setting`, `dose_in`, `target_yield` | 3 |
| 2 (Temp) | + `temperature` | 4 |
| 3 (PI) | + `preinfusion_time` | 5 |
| 4 (Pressure) | + `brew_pressure` OR `pressure_profile` | 5-6 |
| 5 (Full) | + `flow_rate`, `preinfusion_pressure`, `bloom_pause` | 6-8 |

BayBE works well with 4-6 continuous parameters. Even Tier 5 stays under 8 total (with some being categorical), which is within BayBE's effective range for <50 observations.

### Q4: Which parameters are equipment capability vs recipe variable?

**Equipment capability (stored on Brewer, set once):**
- `temp_control_type`, `temp_min`, `temp_max`, `temp_step`
- `preinfusion_type`, `preinfusion_max_time`
- `pressure_control_type`, `pressure_min`, `pressure_max`
- `flow_control_type`
- `has_bloom`, `stop_mode`

**Recipe variable (optimized per bean by BayBE):**
- `grind_setting`, `dose_in`, `target_yield`
- `temperature` (within capability range)
- `preinfusion_time` (within capability limits)
- `preinfusion_pressure`, `brew_pressure` (within capability range)
- `pressure_profile` (from capability-determined options)
- `flow_rate`, `bloom_pause` (if capability exists)

### Q5: Real-world ranges for each parameter?

| Parameter | Practical Min | Practical Max | Common Range | Rounding |
|-----------|--------------|---------------|-------------|----------|
| `grind_setting` | grinder-specific | grinder-specific | espresso range of grinder | 0.5 |
| `dose_in` | 7.0g (single) | 22.0g (triple) | 17.0-20.0g (double basket) | 0.5g |
| `target_yield` | 15.0g (ristretto) | 60.0g+ (allongé) | 30.0-45.0g | 1.0g |
| `temperature` | 85°C | 96°C (105°C DE1) | 88-94°C | 0.5°C |
| `preinfusion_time` | 0s | 60s (DE1) | 3-12s | 1s |
| `preinfusion_pressure` | 1.0 bar | 5.0 bar | 2.0-4.0 bar | 0.5 bar |
| `brew_pressure` | 4.0 bar (turbo) | 13.0 bar (DE1 max) | 6.0-9.5 bar | 0.5 bar |
| `flow_rate` | 0.5 ml/s | 8.0 ml/s | 1.5-3.5 ml/s | 0.5 ml/s |
| `bloom_pause` | 0s | 30s | 5-15s | 5s |

---

## 15. Implementation Priority

### Phase A: Brewer Capabilities (Low effort, high impact)
1. Add capability columns to `Brewer` model
2. Default existing brewers: `temp_control_type="pid"`, everything else default/none
3. Brewer create/edit form gains capability fields
4. No optimizer changes yet — capability data is just stored

### Phase B: Dynamic Parameter Building (Medium effort, high impact)
1. Refactor `_build_parameters()` to read brewer capabilities from BrewSetup
2. Build search space dynamically based on capability flags
3. Backward compatible: existing espresso campaigns produce same parameters (brewer defaults to PID=true, which gives grind + dose + yield + temp = 4 params + saturation)
4. New `preinfusion_time` replaces `preinfusion_pct` for new campaigns

### Phase C: Advanced Parameters (Medium effort, medium impact)
1. Add `brew_pressure`, `pressure_profile`, `preinfusion_pressure`, `bloom_pause`, `flow_rate` to Measurement table
2. Wire up in recommendation display and recording
3. Update UI to show tier-appropriate parameters based on brewer capabilities

### Phase D: Pre-infusion Migration (Low effort, cleanup)
1. Migrate historical `preinfusion_pct` data to `preinfusion_time`
2. Remove `preinfusion_pct` from BayBE parameter columns (keep DB column)
3. Update `saturation` handling (likely remove — it was a pour-over crossover concept)

---

## 16. Saturation Parameter Assessment

The current `saturation` parameter (`yes`/`no` categorical) represents "pre-wet the puck" and was inherited from pour-over crossover thinking. In practice:

- On machines with pre-infusion: saturation is effectively the same as "has pre-infusion" — redundant
- On machines without pre-infusion: you can't pre-wet the puck anyway
- It adds a categorical dimension to every espresso campaign

**Recommendation: Deprecate `saturation` when implementing capability-driven parameters.** Pre-infusion time of 0 = no saturation; any PI time > 0 = saturation. The information is captured by `preinfusion_time`.

For backward compatibility, keep the column in Measurement but stop including it in new BayBE campaigns once the brewer-capability model is active.

---

## Sources

### Meticulous Espresso — Key Insights for BayBE Modeling

The Meticulous Espresso represents a new category: **robotic lever machines**. It's the world's first motorized-piston espresso machine, replacing both traditional pumps and manual levers with a robotic piston that provides:

1. **Flow-priority brewing** — Unlike traditional machines where pressure is set and flow is a consequence, the Meticulous can target a specific flow rate (ml/s) and let pressure become the consequence. This is fundamentally different and should be modeled as a categorical choice: `brew_mode: "pressure_priority" | "flow_priority"`. In flow-priority mode, `flow_rate` is the optimizable param and pressure is recorded output. In pressure-priority mode, `brew_pressure` is the optimizable param and flow is recorded output.

2. **Profile-based brewing** — Users select from named profiles (Italian, Low Contact/Turbo, Bloom, Slayer-style, lever-style declining). This validates our categorical `pressure_profile` approach — even on the most advanced machine, users primarily choose from named profile templates rather than tweaking arbitrary curves.

3. **Built-in gravimetric dosing** — Acaia scale integrated into drip tray. Machine auto-stops at target weight. This means `target_yield` is extremely precise (±1g), which is ideal for BayBE optimization.

4. **Immediate puck saturation** — The motorized piston provides immediate, even water distribution (no pump pressure ramp-up time). This makes pre-infusion behavior different from pump machines — the Meticulous's "pre-infusion" is more like a controlled slow push than a low-pressure wait. The `preinfusion_type: "programmable"` flag covers this.

5. **Contact time as primary variable** — On flow-priority profiles, grind size affects extraction but NOT shot time (machine compensates flow to maintain target time). This is a paradigm shift: users dial grind for extraction level, then adjust flow rate for contact time. Both are BayBE-optimizable continuous params.

6. **Bean aging compensation** — Constant flow rate means shot time doesn't drift as beans age (machine adjusts pressure automatically). This is relevant for BayBE: recommendations should remain valid longer, requiring fewer re-optimization cycles.

**Impact on our model:** The Meticulous fits cleanly into our existing capability-driven model with `pressure_control_type: "programmable"`, `flow_control_type: "programmable"`, and `temp_control_type: "profiling"`. It's a Tier 5 machine. The one addition needed is `brew_mode` (pressure_priority vs flow_priority) as a categorical parameter for machines that support both modes.

---

## Sources (Original)

- **Decent DE1 specs:** decentespresso.com/overview — Pressure 0-13 bar, temp 20-105°C, flow/pressure/temp profiling, PI end detection, volumetric dosing. Confidence: HIGH (manufacturer source, verified Feb 2026).
- **Lelit Bianca:** lelit.com — Paddle flow control (manual, analog), dual boiler, PID via LCC controller (1°C steps), E61 group. Confidence: HIGH.
- **Breville/Sage Dual Boiler:** sageappliances.com — PID 86-96°C (0.5°C), timed PI (0-15s), adjustable OPV (internal, 6-12 bar), no pressure profiling. Confidence: HIGH.
- **La Marzocco Linea Mini:** lamarzocco.com — PID (0.5°C), saturated group, line-pressure PI (plumbed only), 9 bar OPV (not adjustable). Confidence: HIGH.
- **La Marzocco GS3 MP:** lamarzocco.com — Manual paddle for flow/pressure control, PID, saturated group. Confidence: HIGH.
- **Gaggia Classic Pro:** Stock thermostat (~92°C ±8°C), 15-bar vibe pump, 9-bar OPV (adjustable via screw). Common mods: PID kit, dimmer switch (pre-infusion). Confidence: HIGH (community consensus).
- **Rancilio Silvia:** Stock thermostat, OPV adjustable. PID mod widely documented. Confidence: HIGH.
- **Profitec Pro 600/700:** PID, E61 group, dual boiler. Pro 700 widely paired with aftermarket flow control device. Confidence: HIGH.
- **Pressure profiling community data:** Home-Barista, Reddit r/espresso, Decent User Forums. Profile categories (flat, declining, blooming, Slayer-style) well-established in community. Confidence: HIGH for categories, MEDIUM for specific pressure values.
- **Flow rate data:** Decent DE1 community data shows typical espresso flow rates 1.5-3.5 ml/s, turbo shots 3-5 ml/s. Confidence: MEDIUM (varies significantly with grind and puck prep).
- **BayBE parameter count limits:** BayBE documentation and practical experience — Gaussian process surrogate models work well with 4-8 parameters and 20-50 observations. Beyond 8 continuous parameters, the curse of dimensionality requires exponentially more observations. Confidence: HIGH.

---
*Espresso Machine Capabilities Research for: BeanBay — Coffee optimization via Bayesian optimization*
*Researched: 2026-02-24*

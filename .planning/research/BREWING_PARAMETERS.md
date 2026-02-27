# Brewing Parameters Research

**Domain:** BeanBay multi-method brewing optimization
**Researched:** 2026-02-24
**Purpose:** Define controllable parameters per brewing method for BayBE search space modeling

---

## Current State

BeanBay currently supports two methods with hardcoded parameter sets:

- **Espresso:** `grind_setting`, `temperature`, `preinfusion_pct`, `dose_in`, `target_yield`, `saturation` (categorical)
- **Pour-over:** `grind_setting`, `temperature`, `bloom_weight`, `dose_in`, `brew_volume`

This research defines the complete parameter landscape to generalize the system.

---

## 1. Espresso

### Core Parameters (always present)

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Maps to grinder's min/max |
| `dose_in` | NumericalContinuous | 14.0 - 22.0 | grams | 0.5 | Basket size dependent (single: 7-12g, double: 14-20g, triple: 20-22g) |
| `target_yield` | NumericalContinuous | 25.0 - 60.0 | grams | 1.0 | Output weight; determines ratio |
| `temperature` | NumericalContinuous | 85.0 - 96.0 | celsius | 0.5 | PID machines: 0.5-1C steps; basic machines: not adjustable |

### Equipment-Dependent Parameters

| Parameter | BayBE Type | Range | Availability | Notes |
|-----------|-----------|-------|-------------|-------|
| `preinfusion_time` | NumericalContinuous | 0 - 15 | Machines with timed PI | Seconds of low-pressure soak |
| `preinfusion_pressure` | NumericalContinuous | 1.0 - 5.0 | Machines with adjustable PI pressure | bar; ramp to full extraction pressure |
| `brew_pressure` | NumericalContinuous | 5.0 - 13.0 | Pressure-profiling machines | bar; default 9 bar; some go to 13 |
| `flow_rate` | NumericalContinuous | 1.0 - 6.0 | Flow-profiling machines | ml/s target flow |
| `saturation` | Categorical | yes/no | Pour-over crossover | Pre-wet puck (rare for espresso) |

### Pressure Profile Types (categorical, equipment-dependent)

If the brewer supports pressure profiling, the profile shape matters but is hard to parameterize continuously. Options:

| Profile | Description | Machines |
|---------|-------------|----------|
| `flat_9bar` | Standard 9 bar throughout | Most machines (default) |
| `declining` | Start 9, naturally decline | Lever machines, spring-lever profiles |
| `blooming` | Low (2-3 bar) → pause → 6-9 bar | Decent DE1 blooming profile |
| `ramp_up` | Gradual 3 → 9 bar | Slayer-style slow ramp |
| `custom` | User-defined curve | Decent DE1, Lelit Bianca paddle |

**Recommendation:** For BayBE, pressure profiling is best modeled as a categorical `pressure_profile` parameter (if machine supports it) rather than trying to parameterize arbitrary curves. The profile name becomes a categorical variable; the optimizer learns which profiles work best for a given bean.

### Machine Capability Matrix

| Machine | Temp Control | Pre-infusion | Pressure Profiling | Flow Control | Temp Range |
|---------|-------------|-------------|-------------------|-------------|------------|
| **Sage/Breville Dual Boiler** | PID, 0.5C steps | Time-based (adjustable seconds) | No (flat 9 bar via OPV) | No | 86-96C |
| **Decent DE1** | PID, 0.1C steps | Full control (time, pressure, flow) | Full (draw any curve, 0-13 bar) | Full (target ml/s) | 20-105C |
| **La Marzocco Linea Mini** | PID, 1C steps | Plumbing-dependent (line pressure PI) | No (fixed pump, OPV at 9 bar) | No | 85-96C |
| **Lelit Bianca** | PID (LCC), 1C steps | Via paddle (manual flow restriction) | Manual via paddle | Manual paddle (analog, not digital) | 85-96C |
| **Gaggia Classic Pro** | No PID (thermostat, ~+/-5C) | None (or dimmer mod) | No | No | ~92C fixed (mod: 85-96) |
| **Rancilio Silvia** | No PID (thermostat) | None | No | No | ~95C (varies with surfing) |
| **Breville Bambino Plus** | PID (preset temps only) | Auto 10s PI | No | No | Low/Med/High (~88/92/96) |

### Minimal Espresso Parameter Set (90% impact)

1. **grind_setting** — #1 impact on extraction
2. **dose_in** — determines ratio denominator
3. **target_yield** — determines ratio numerator
4. **temperature** — significant flavor impact (if adjustable)

These four capture the vast majority of espresso dial-in. `preinfusion` and `pressure_profile` are meaningful but secondary.

### Recorded Outputs (not BayBE inputs, but tracked)

| Output | Type | Notes |
|--------|------|-------|
| `extraction_time` | Float (seconds) | Time from pump start to target yield |
| `ratio` | Computed | `target_yield / dose_in` (e.g., 1:2.0) |
| `channeling_observed` | Boolean | Visual assessment from bottomless PF |

---

## 2. Pour-Over (V60, Kalita Wave, Chemex, etc.)

### Core Parameters

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Medium grind range |
| `dose_in` | NumericalContinuous | 12.0 - 30.0 | grams | 0.5 | Common: 15-20g |
| `brew_volume` | NumericalContinuous | 200.0 - 500.0 | ml | 5.0 | Total water; determines ratio |
| `temperature` | NumericalContinuous | 85.0 - 100.0 | celsius | 1.0 | Kettle temp; 92-96 typical |
| `bloom_weight` | NumericalContinuous | 20.0 - 80.0 | grams | 1.0 | 2-3x dose typical (30-60g) |
| `bloom_time` | NumericalContinuous | 20.0 - 60.0 | seconds | 5.0 | 30-45s typical |

### Advanced Parameters

| Parameter | BayBE Type | Range | Notes |
|-----------|-----------|-------|-------|
| `num_pours` | NumericalDiscrete | 1 - 6 | Single continuous pour vs multiple staged pours |
| `pour_interval` | NumericalContinuous | 15.0 - 60.0 | Seconds between pours (if multi-pour) |
| `agitation` | Categorical | none / swirl / stir / Rao_spin | Technique after bloom or pours |
| `filter_rinse` | Categorical | yes / no | Pre-wetting the paper filter |

### Brewer Differences

| Brewer | Geometry | Drain | Impact on Parameters |
|--------|----------|-------|---------------------|
| **Hario V60** | Cone, 60-degree angle, spiral ribs | Fast, open bottom | Most sensitive to pour technique; grind must compensate for fast drain |
| **Kalita Wave** | Flat bottom, 3 small holes | Slower, more forgiving | More consistent; less sensitive to pour technique |
| **Chemex** | Cone, thick paper | Slow drain, thick filter | Thicker filter absorbs oils; generally coarser grind needed; cleaner cup |
| **Origami** | Cone or flat (accepts both filters) | Depends on filter choice | Versatile; parameter ranges depend on filter |
| **April** | Cone, single large hole | Very fast | Ultra-fine for pour-over; unique technique |

**Key insight:** The brewer choice is already captured by the `Brewer` entity in the current data model. Different brewers within "pour-over" don't need separate parameter sets — they need different default *ranges*. The brewer is part of the `BrewSetup` context, and the optimizer will learn optimal ranges within that context via the campaign key `bean__pour-over__setup_id`.

### Minimal Pour-Over Parameter Set (90% impact)

1. **grind_setting** — #1 impact
2. **dose_in** — base amount
3. **brew_volume** — water:coffee ratio
4. **temperature** — extraction driver
5. **bloom_weight** — affects early extraction and degassing

These five (which match the current implementation) capture the dominant variables. `bloom_time`, `num_pours`, and `agitation` are meaningful but secondary.

### Recorded Outputs

| Output | Type | Notes |
|--------|------|-------|
| `total_brew_time` | Float (seconds) | From first pour to last drip |
| `ratio` | Computed | `brew_volume / dose_in` (e.g., 1:15) |

---

## 3. French Press / Immersion

### Core Parameters

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Coarse range |
| `dose_in` | NumericalContinuous | 15.0 - 40.0 | grams | 0.5 | Depends on press size |
| `water_amount` | NumericalContinuous | 200.0 - 800.0 | ml | 10.0 | Press capacity |
| `temperature` | NumericalContinuous | 88.0 - 100.0 | celsius | 1.0 | Off-boil typical (~96C) |
| `steep_time` | NumericalContinuous | 120.0 - 600.0 | seconds | 15.0 | 4 min standard; Hoffmann method: 9-10 min |
| `agitation` | Categorical | none / stir_once / stir_multiple | Whether and how to break the crust |

### Minimal Set (90% impact)

1. **grind_setting**
2. **dose_in** + **water_amount** (ratio)
3. **steep_time**
4. **temperature** (less critical — most use near-boil)

---

## 4. AeroPress

### Core Parameters

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Fine to medium |
| `dose_in` | NumericalContinuous | 11.0 - 20.0 | grams | 0.5 | Typically 11-15g |
| `water_amount` | NumericalContinuous | 100.0 - 250.0 | ml | 5.0 | |
| `temperature` | NumericalContinuous | 75.0 - 100.0 | celsius | 1.0 | Wide range intentional — AP recipes vary hugely |
| `steep_time` | NumericalContinuous | 30.0 - 300.0 | seconds | 5.0 | From quick press to long steep |
| `method` | Categorical | standard / inverted | Orientation during brewing |

### Advanced Parameters

| Parameter | BayBE Type | Range | Notes |
|-----------|-----------|-------|-------|
| `agitation` | Categorical | none / stir / swirl | Stirring during steep |
| `press_speed` | Categorical | fast / slow / gentle | Qualitative — hard to measure precisely |
| `filter_type` | Categorical | paper / metal | Changes body and clarity |

### Minimal Set (90% impact)

1. **grind_setting**
2. **dose_in** + **water_amount** (ratio)
3. **temperature**
4. **steep_time**
5. **method** (standard vs inverted)

---

## 5. Turkish / Ibrik (Cezve)

### Core Parameters

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Finest possible; finer than espresso |
| `dose_in` | NumericalContinuous | 5.0 - 12.0 | grams | 0.5 | Per cup |
| `water_amount` | NumericalContinuous | 50.0 - 150.0 | ml | 5.0 | Per cup |
| `heat_level` | Categorical | low / medium / medium_high | Stove heat setting |
| `num_boils` | NumericalDiscrete | 1 - 3 | Traditional: bring to foaming 2-3x |
| `sugar` | Categorical | none / little / medium / sweet | Traditional; affects optimization if included |

### Minimal Set (90% impact)

1. **grind_setting** (must be ultra-fine)
2. **dose_in** + **water_amount** (ratio)
3. **heat_level**
4. **num_boils**

---

## 6. Moka Pot

### Core Parameters

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Fine-medium (finer than pour-over, coarser than espresso) |
| `dose_in` | NumericalContinuous | 10.0 - 25.0 | grams | 0.5 | Fill the basket; pot-size dependent |
| `water_amount` | NumericalContinuous | 100.0 - 300.0 | ml | 10.0 | Fill to valve; pot-size dependent |
| `preheat_water` | Categorical | yes / no | Starting with hot vs cold water |
| `heat_level` | Categorical | low / medium / high | Stove setting |

### Minimal Set (90% impact)

1. **grind_setting**
2. **dose_in** (basket fill level)
3. **heat_level**
4. **preheat_water**

---

## 7. Cold Brew

### Core Parameters

| Parameter | BayBE Type | Typical Range | Unit | Rounding | Notes |
|-----------|-----------|---------------|------|----------|-------|
| `grind_setting` | NumericalContinuous | grinder-specific | clicks/numbers | 0.5 | Coarse to very coarse |
| `dose_in` | NumericalContinuous | 30.0 - 150.0 | grams | 5.0 | High dose (concentrate) |
| `water_amount` | NumericalContinuous | 300.0 - 1500.0 | ml | 10.0 | |
| `steep_time` | NumericalContinuous | 720.0 - 1440.0 | minutes | 60.0 | 12-24 hours (stored in minutes for BayBE range sanity) |
| `brew_temp` | Categorical | fridge / room_temp | ~4C vs ~20C |

### Minimal Set (90% impact)

1. **grind_setting**
2. **dose_in** + **water_amount** (ratio; typically 1:5 to 1:12)
3. **steep_time**
4. **brew_temp**

---

## 8. Grinder Modeling

### Current Model (adequate)

The existing `Grinder` model captures the essentials:

```python
class Grinder(Base):
    name: str
    dial_type: str       # "stepped" or "stepless"
    step_size: float     # only for stepped (e.g., 1.0 for Comandante clicks)
    min_value: float     # e.g., 0
    max_value: float     # e.g., 50
```

### Grinder Reference Data

| Grinder | Dial Type | Range | Step Size | Espresso Range | Pour-Over Range | French Press Range |
|---------|-----------|-------|-----------|----------------|-----------------|-------------------|
| **Comandante C40** | Stepped | 0 - 50 clicks | 1 click (3 subdivisions w/ Red Clix) | 8 - 16 | 22 - 32 | 32 - 40 |
| **1Zpresso JX-Pro** | Stepped | 0 - 200 (numbers on dial) | 1 click (12.5 micron/click) | 60 - 90 | 120 - 160 | 160 - 200 |
| **1Zpresso J-Max** | Stepped | 0 - ~300 | 1 click (8.8 micron/click) | 80 - 130 | 180 - 240 | 240 - 300 |
| **Niche Zero** | Stepless | 0 - 50 (numbered dial) | Continuous (0.25 practical) | 8 - 18 | 25 - 40 | 40 - 50 |
| **DF83v / DF64** | Stepless | 0 - ~80 (numbered) | Continuous | 10 - 30 | 35 - 55 | 55 - 70 |
| **Baratza Encore** | Stepped | 0 - 40 | 1 step | Not recommended | 12 - 21 | 22 - 32 |
| **Baratza Sette 270** | Stepped | 1 - 31 (macro) x A-T (micro) | Macro + micro steps | 5E - 15E (espresso range) | Not ideal | Not ideal |
| **Eureka Mignon** | Stepless | ~0 - 10 (arbitrary scale) | Continuous | 1 - 4 | Not common | Not ideal |
| **Lagom P64 / P100** | Stepless | 0 - ~80 (numbers vary) | Continuous | 10 - 25 | 30 - 50 | 50 - 65 |

### Zeroing / Calibration Concept

Grinders need periodic "zeroing" — finding the point where burrs touch. All settings are relative to this zero point. In BeanBay's model, this is handled by the user setting `min_value` correctly:

- User zeros the grinder (burrs touch = 0)
- Sets `min_value` = 0 (or whatever the dial reads at zero)
- Sets `max_value` = maximum useful setting
- BayBE's search range for `grind_setting` uses these bounds

The absolute number is meaningless across grinders — a "20" on a Niche Zero is completely different from a "20" on a Comandante. This is already handled correctly by the campaign key being per-setup: `bean__method__setup_id`. Grind settings learned on one setup don't transfer to a different grinder.

### How Grind Ranges Map to Methods

The optimizer needs to know what range to explore for a given method on a given grinder. This should be modeled as **method-specific ranges on the Brewer/Setup level**, not on the grinder alone, because:

1. The grinder only defines the physical range (min_value to max_value)
2. The useful range for a method is a subset
3. Starting ranges can be pre-populated but should be adjustable per-bean

**Recommendation:** Add a `grind_range` field to `BrewSetup` (or use the existing `parameter_overrides` on Bean) to narrow the search space per method. Defaults can be derived from known grinder + method combinations.

### Stepped vs Stepless in BayBE

- **Stepless:** Use `NumericalContinuousParameter` with rounding to practical precision (e.g., 0.25 increments)
- **Stepped:** Use `NumericalDiscreteParameter` with explicit values, OR use `NumericalContinuousParameter` with rounding to `step_size`

**Current approach (rounding) works well.** Trying to use `NumericalDiscreteParameter` for stepped grinders with 40+ steps creates an enormous discrete search space that BayBE handles less efficiently than continuous with rounding.

---

## 9. Key Questions Answered

### Q1: Minimal parameter set per method that captures 90% of impact?

| Method | Minimal Parameters | Count |
|--------|-------------------|-------|
| **Espresso** | grind_setting, dose_in, target_yield, temperature | 4 |
| **Pour-over** | grind_setting, dose_in, brew_volume, temperature, bloom_weight | 5 |
| **French Press** | grind_setting, dose_in, water_amount, steep_time | 4 |
| **AeroPress** | grind_setting, dose_in, water_amount, temperature, steep_time | 5 |
| **Turkish** | grind_setting, dose_in, water_amount, heat_level | 4 |
| **Moka Pot** | grind_setting, dose_in, heat_level | 3 |
| **Cold Brew** | grind_setting, dose_in, water_amount, steep_time, brew_temp | 5 |

Common across ALL methods: `grind_setting`, `dose_in`.

### Q2: Equipment capabilities vs recipe choices?

**Equipment capabilities** (defined on Brewer):
- Has PID temperature control (boolean)
- Has pre-infusion (boolean + type: none/timed/pressure/flow)
- Has pressure profiling (boolean)
- Has flow control (boolean)
- Temperature range (min/max, if PID)
- Max pressure (bar)

**Recipe choices** (optimized per bean by BayBE):
- grind_setting, dose_in, target_yield/brew_volume
- temperature (within equipment range)
- preinfusion settings (within equipment capability)
- steep_time, bloom parameters, etc.

The distinction matters: capabilities determine which parameters appear in the search space; recipe values are what BayBE optimizes.

### Q3: How to model advanced vs basic machine features?

**Recommendation: Capability flags on the Brewer model.**

```python
class Brewer(Base):
    name: str
    # ... existing fields ...

    # Capability flags (determine which parameters are optimizable)
    has_pid_temp: bool = True          # Can set exact temperature?
    has_preinfusion: bool = False       # Any form of pre-infusion?
    preinfusion_type: str = "none"     # none / timed / pressure / flow / manual_paddle
    has_pressure_profiling: bool = False
    has_flow_control: bool = False
    temp_min: float = None             # Minimum settable temp (if PID)
    temp_max: float = None             # Maximum settable temp (if PID)
    max_pressure: float = 9.0          # Bar (most machines)
```

When building the BayBE search space for a brew setup:
1. Always include: `grind_setting`, `dose_in`, method-specific core params
2. If `has_pid_temp`: include `temperature` with `[temp_min, temp_max]` bounds
3. If `has_preinfusion` and `preinfusion_type == "timed"`: include `preinfusion_time`
4. If `has_pressure_profiling`: include `brew_pressure` or `pressure_profile`
5. Etc.

If a machine lacks PID temp control, temperature is simply omitted from the BayBE search space — BayBE can't optimize what you can't control.

### Q4: UX pattern for progressive disclosure?

**Tier 1 (always shown):** Core parameters — the minimal set from Q1.
These are the fields the user sees on every brew form.

**Tier 2 (shown if equipment supports):** Advanced parameters detected from brewer capabilities.
Example: temperature slider only appears if `brewer.has_pid_temp == True`.

**Tier 3 (expandable / optional):** Recording-only outputs and edge-case params.
Example: extraction_time, channeling_observed, notes. These don't feed into BayBE but are tracked for the user's reference.

**Implementation pattern:**
```
Brew Form:
  ┌──────────────────────────────┐
  │ ☕ Grind: 18.5               │  ← Always
  │ ⚖️  Dose: 18.0g              │  ← Always
  │ 🎯 Yield: 36.0g             │  ← Always (espresso)
  │ 🌡️ Temperature: 93C         │  ← Only if brewer.has_pid_temp
  │ ⏱️ Pre-infusion: 8s         │  ← Only if brewer.has_preinfusion
  │                              │
  │ ▸ Advanced settings          │  ← Expandable
  │   Pressure profile: flat_9   │
  │   Flow rate: 2.5 ml/s       │
  │                              │
  │ ▸ Record observations        │  ← Expandable
  │   Extraction time: ___s     │
  │   Notes: ___                │
  └──────────────────────────────┘
```

### Q5: How do grinder ranges map across methods practically?

The key insight is that **grind ranges are grinder-specific, not universal**. A "medium grind" on a Comandante C40 is ~24-28 clicks; on a Niche Zero it's ~25-35 on the dial. There's no universal number.

**Practical approach:**
1. User registers their grinder with `min_value`, `max_value`, `dial_type`, `step_size`
2. When creating a brew setup for a method, the system suggests a default `grind_setting` range based on the method:
   - Espresso: lower 25-40% of grinder range
   - Pour-over: middle 40-65% of grinder range
   - French press: upper 60-85% of grinder range
   - Turkish: lowest 15-25% of grinder range
3. User adjusts if they know their grinder better
4. These map to `parameter_overrides.grind_setting.min/max` on the Bean level

**Percentage-based defaults:**
```python
METHOD_GRIND_PERCENTAGES = {
    "espresso":     (0.15, 0.40),
    "pour-over":    (0.40, 0.70),
    "french-press": (0.55, 0.85),
    "aeropress":    (0.25, 0.60),
    "turkish":      (0.05, 0.20),
    "moka-pot":     (0.25, 0.45),
    "cold-brew":    (0.55, 0.85),
}

def suggest_grind_range(grinder, method):
    lo_pct, hi_pct = METHOD_GRIND_PERCENTAGES[method]
    full_range = grinder.max_value - grinder.min_value
    return (
        grinder.min_value + full_range * lo_pct,
        grinder.min_value + full_range * hi_pct,
    )
```

---

## 10. Data Model Recommendations

### Approach: Method-Specific Parameter Registries

Rather than hardcoding parameter lists in the optimizer, define a registry that maps method → parameter definitions. This makes adding new methods trivial.

```python
# Conceptual — not literal code, but the data structure
PARAMETER_REGISTRY = {
    "espresso": {
        "core": [
            {"name": "grind_setting", "type": "continuous", "default_range": (15, 25), "rounding": 0.5, "unit": "setting"},
            {"name": "dose_in",       "type": "continuous", "default_range": (14, 22),  "rounding": 0.5, "unit": "g"},
            {"name": "target_yield",  "type": "continuous", "default_range": (25, 60),  "rounding": 1.0, "unit": "g"},
            {"name": "temperature",   "type": "continuous", "default_range": (86, 96),  "rounding": 0.5, "unit": "C",
             "requires": "brewer.has_pid_temp"},
        ],
        "advanced": [
            {"name": "preinfusion_time", "type": "continuous", "default_range": (0, 15),  "rounding": 1.0, "unit": "s",
             "requires": "brewer.has_preinfusion"},
            {"name": "brew_pressure",    "type": "continuous", "default_range": (6, 9.5), "rounding": 0.5, "unit": "bar",
             "requires": "brewer.has_pressure_profiling"},
            {"name": "pressure_profile", "type": "categorical", "values": ["flat_9bar", "declining", "blooming", "ramp_up"],
             "requires": "brewer.has_pressure_profiling"},
        ],
        "categorical": [
            {"name": "saturation", "values": ["yes", "no"]},
        ],
        "outputs": [
            {"name": "extraction_time", "unit": "s"},
        ],
    },
    "pour-over": {
        "core": [
            {"name": "grind_setting",  "type": "continuous", "default_range": (15, 40), "rounding": 0.5},
            {"name": "dose_in",        "type": "continuous", "default_range": (12, 22), "rounding": 0.5, "unit": "g"},
            {"name": "brew_volume",    "type": "continuous", "default_range": (200, 500), "rounding": 5.0, "unit": "ml"},
            {"name": "temperature",    "type": "continuous", "default_range": (88, 98), "rounding": 1.0, "unit": "C"},
            {"name": "bloom_weight",   "type": "continuous", "default_range": (20, 80), "rounding": 1.0, "unit": "g"},
        ],
        "advanced": [
            {"name": "bloom_time",     "type": "continuous", "default_range": (20, 60), "rounding": 5.0, "unit": "s"},
            {"name": "num_pours",      "type": "discrete",  "values": [1, 2, 3, 4, 5, 6]},
            {"name": "agitation",      "type": "categorical", "values": ["none", "swirl", "stir"]},
        ],
        "outputs": [
            {"name": "total_brew_time", "unit": "s"},
        ],
    },
    "french-press": {
        "core": [
            {"name": "grind_setting",  "type": "continuous", "default_range": (25, 40), "rounding": 0.5},
            {"name": "dose_in",        "type": "continuous", "default_range": (15, 40), "rounding": 0.5, "unit": "g"},
            {"name": "water_amount",   "type": "continuous", "default_range": (200, 800), "rounding": 10.0, "unit": "ml"},
            {"name": "steep_time",     "type": "continuous", "default_range": (180, 600), "rounding": 15.0, "unit": "s"},
        ],
        "advanced": [
            {"name": "temperature",    "type": "continuous", "default_range": (90, 100), "rounding": 1.0, "unit": "C"},
            {"name": "agitation",      "type": "categorical", "values": ["none", "stir_once", "stir_multiple"]},
        ],
    },
    "aeropress": {
        "core": [
            {"name": "grind_setting",  "type": "continuous", "default_range": (10, 30), "rounding": 0.5},
            {"name": "dose_in",        "type": "continuous", "default_range": (11, 20), "rounding": 0.5, "unit": "g"},
            {"name": "water_amount",   "type": "continuous", "default_range": (100, 250), "rounding": 5.0, "unit": "ml"},
            {"name": "temperature",    "type": "continuous", "default_range": (75, 100), "rounding": 1.0, "unit": "C"},
            {"name": "steep_time",     "type": "continuous", "default_range": (30, 300), "rounding": 5.0, "unit": "s"},
        ],
        "advanced": [
            {"name": "brew_method",    "type": "categorical", "values": ["standard", "inverted"]},
            {"name": "agitation",      "type": "categorical", "values": ["none", "stir", "swirl"]},
        ],
    },
    "turkish": {
        "core": [
            {"name": "grind_setting",  "type": "continuous", "default_range": (0, 10), "rounding": 0.5},
            {"name": "dose_in",        "type": "continuous", "default_range": (5, 12), "rounding": 0.5, "unit": "g"},
            {"name": "water_amount",   "type": "continuous", "default_range": (50, 150), "rounding": 5.0, "unit": "ml"},
            {"name": "heat_level",     "type": "categorical", "values": ["low", "medium", "medium_high"]},
        ],
        "advanced": [
            {"name": "num_boils",      "type": "discrete", "values": [1, 2, 3]},
            {"name": "sugar",          "type": "categorical", "values": ["none", "little", "medium", "sweet"]},
        ],
    },
    "moka-pot": {
        "core": [
            {"name": "grind_setting",  "type": "continuous", "default_range": (10, 25), "rounding": 0.5},
            {"name": "dose_in",        "type": "continuous", "default_range": (10, 25), "rounding": 0.5, "unit": "g"},
            {"name": "preheat_water",  "type": "categorical", "values": ["yes", "no"]},
            {"name": "heat_level",     "type": "categorical", "values": ["low", "medium", "high"]},
        ],
        "advanced": [
            {"name": "water_amount",   "type": "continuous", "default_range": (100, 300), "rounding": 10.0, "unit": "ml"},
        ],
    },
    "cold-brew": {
        "core": [
            {"name": "grind_setting",  "type": "continuous", "default_range": (30, 45), "rounding": 0.5},
            {"name": "dose_in",        "type": "continuous", "default_range": (30, 150), "rounding": 5.0, "unit": "g"},
            {"name": "water_amount",   "type": "continuous", "default_range": (300, 1500), "rounding": 10.0, "unit": "ml"},
            {"name": "steep_time",     "type": "continuous", "default_range": (720, 1440), "rounding": 60.0, "unit": "min"},
        ],
        "advanced": [
            {"name": "brew_temp",      "type": "categorical", "values": ["fridge", "room_temp"]},
        ],
    },
}
```

### Brewer Capability Model Extension

```python
class Brewer(Base):
    # ... existing fields ...

    # Espresso-specific capabilities
    has_pid_temp: bool = True
    has_preinfusion: bool = False
    preinfusion_type: str = "none"    # none / timed / pressure / flow / manual_paddle
    has_pressure_profiling: bool = False
    has_flow_control: bool = False
    temp_min: float = None
    temp_max: float = None
    max_pressure: float = 9.0
```

### Dynamic Parameter Building

```python
def build_parameters_for_setup(method: str, brewer: Brewer | None, overrides: dict | None) -> list:
    """Build BayBE parameter list dynamically based on method + equipment capabilities."""
    method_config = PARAMETER_REGISTRY[method]
    params = []

    for p in method_config["core"]:
        if "requires" in p and brewer:
            if not getattr(brewer, p["requires"].split(".")[1], True):
                continue
        bounds = _apply_overrides(p, overrides)
        params.append(_make_baybe_param(p, bounds))

    # Advanced params only if equipment supports them
    for p in method_config.get("advanced", []):
        if "requires" in p and brewer:
            if not getattr(brewer, p["requires"].split(".")[1], False):
                continue
        bounds = _apply_overrides(p, overrides)
        params.append(_make_baybe_param(p, bounds))

    for p in method_config.get("categorical", []):
        params.append(CategoricalParameter(name=p["name"], values=p["values"]))

    return params
```

---

## 11. Migration Strategy from Current Model

The current system has hardcoded espresso + pour-over parameter sets. To generalize:

### Phase 1: Add Brewer capabilities
- Add capability columns to `Brewer` model
- Existing brewers default to `has_pid_temp=True`, all others `False`
- No impact on existing campaigns

### Phase 2: Parameter registry
- Create `PARAMETER_REGISTRY` dict (as above)
- Refactor `_build_parameters()` to use registry
- Keep backward compatibility: espresso and pour-over produce identical parameters as today

### Phase 3: New methods
- Add methods one at a time (french-press, aeropress, etc.)
- Each gets its own parameter set from the registry
- New `Measurement` columns added as nullable (no breaking changes)

### Phase 4: Equipment-aware parameter filtering
- Use brewer capabilities to filter parameters from registry
- Machines without PID get no temperature parameter
- Machines with pressure profiling get `pressure_profile` categorical

### Storage Consideration

The current `Measurement` table has fixed columns (`grind_setting`, `temperature`, `preinfusion_pct`, etc.). For multi-method support with varying parameter sets, two approaches:

**Option A: Wide table with nullable columns** (current approach, extend it)
- Add `steep_time`, `water_amount`, `bloom_time`, `agitation`, etc. as nullable columns
- Simple queries, familiar pattern
- Gets wide with many methods but SQLite handles this fine

**Option B: JSON column for method-specific params**
- `params = Column(JSON)` storing `{"grind_setting": 18.5, "steep_time": 240, ...}`
- Flexible, no schema changes per method
- Harder to query specific params

**Recommendation: Option A** — it's what the codebase already does (pour-over added `bloom_weight` and `brew_volume` as nullable columns). Keep extending. The wide table is fine for a single-user app with <10k rows.

---

## 12. Summary: BayBE Variable Types by Method

| Method | Continuous Params | Categorical Params | Discrete Params | Total Core |
|--------|------------------|-------------------|-----------------|------------|
| Espresso | 4 (grind, dose, yield, temp) | 1 (saturation) | 0 | 5 |
| Pour-over | 5 (grind, dose, volume, temp, bloom) | 0 | 0 | 5 |
| French Press | 4 (grind, dose, water, steep) | 0 | 0 | 4 |
| AeroPress | 5 (grind, dose, water, temp, steep) | 0 | 0 | 5 |
| Turkish | 3 (grind, dose, water) | 1 (heat) | 0 | 4 |
| Moka Pot | 2 (grind, dose) | 2 (preheat, heat) | 0 | 4 |
| Cold Brew | 4 (grind, dose, water, steep) | 0 | 0 | 4 |

BayBE handles 4-6 parameters well. Beyond ~8 continuous parameters, the search space gets too large for efficient Bayesian optimization with <50 observations. The core sets above are sized appropriately.

---

## Sources

- **Decent DE1 specs:** https://decentespresso.com/overview — Pressure 0-13 bar, temp 20-105C, flow/pressure/temperature profiling, pre-infusion end detection. Confidence: HIGH.
- **Lelit Bianca specs:** https://lelit.com/product/bianca-pl162t/ — Paddle flow control, dual boiler, LCC with pre-infusion and brew temp settings. Confidence: HIGH.
- **Sage Dual Boiler specs:** https://www.sageappliances.com — PID temp control, timed pre-infusion, 9 bar OPV, no pressure profiling. Confidence: HIGH.
- **Niche Zero specs:** https://www.nichecoffee.co.uk/products/niche-zero — Stepless, 0-50 range, 63mm conical burrs. Confidence: HIGH.
- **Comandante C40:** https://comandantegrinder.com — Stepped, Nitro Blade burrs, consistent precision. Confidence: HIGH.
- **Community grinder ranges:** Home-Barista, Reddit r/espresso, r/coffee consensus on grinder settings per method. Confidence: MEDIUM (varies by individual grinder calibration).
- **Brewing parameter impact:** SCA brewing standards, James Hoffmann methodology, Barista Hustle extraction theory. Confidence: HIGH for relative parameter importance.

---
*Brewing Parameters Research for: BeanBay — Multi-method coffee optimization*
*Researched: 2026-02-24*

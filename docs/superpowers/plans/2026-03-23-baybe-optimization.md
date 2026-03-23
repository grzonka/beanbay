# BayBE Optimization Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate BayBE Bayesian optimization into the BeanBay REST API, enabling async brew parameter suggestions per bean+setup with a 3-layer parameter range system.

**Architecture:** New optimization models (Campaign, Recommendation, OptimizationJob, MethodParameterDefault, BeanParameterOverride) alongside existing Brew/Bean/BrewSetup models. Taskiq InMemoryBroker handles async BayBE computation. A parameter range service computes effective ranges from method defaults → equipment capabilities → bean overrides. All new routes live under `/api/v1/optimize`.

**Tech Stack:** FastAPI, SQLModel, BayBE, taskiq (InMemoryBroker), Alembic, pytest

**Spec:** `docs/superpowers/specs/2026-03-23-baybe-optimization-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|---------------|
| `src/beanbay/models/optimization.py` | Campaign, MethodParameterDefault, BeanParameterOverride, Recommendation, OptimizationJob models |
| `src/beanbay/schemas/optimization.py` | Create/Update/Read schemas for all optimization models |
| `src/beanbay/services/parameter_ranges.py` | 3-layer effective range computation + capability gate evaluation |
| `src/beanbay/services/optimizer.py` | BayBE campaign creation, recommendation generation, measurement handling |
| `src/beanbay/services/taskiq_broker.py` | Taskiq broker setup + worker task definition |
| `src/beanbay/routers/optimize.py` | All `/optimize/...` endpoints (campaigns, recommendations, jobs, overrides, progress, preferences) |
| `src/beanbay/seed_optimization.py` | Seed MethodParameterDefault rows for all 7 brew methods |
| `tests/unit/test_parameter_ranges.py` | Unit tests for range computation + capability gating |
| `tests/unit/test_capability_gates.py` | Unit tests for requires condition parsing |
| `tests/integration/test_optimize_api.py` | Integration tests for optimization endpoints |
| `tests/integration/test_bean_overrides_api.py` | Integration tests for bean parameter override endpoints |

### Modified Files

| File | Change |
|------|--------|
| `src/beanbay/models/brew.py` | Add 7 new nullable columns to Brew |
| `src/beanbay/models/__init__.py` | Re-export new optimization models |
| `src/beanbay/schemas/brew.py` | Add new columns to BrewCreate, BrewUpdate, BrewRead, BrewListRead |
| `src/beanbay/main.py` | Register optimize router, call seed_method_parameter_defaults, start taskiq broker |
| `pyproject.toml` | Add `baybe`, `taskiq` dependencies |

---

## Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add baybe and taskiq to pyproject.toml**

Add to `[project.dependencies]`:
```toml
"baybe>=0.12",
"taskiq>=0.11",
```

- [ ] **Step 2: Install dependencies**

Run: `uv sync`
Expected: Dependencies resolve and install successfully.

- [ ] **Step 3: Verify imports work**

Run: `uv run python -c "import baybe; import taskiq; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add baybe and taskiq dependencies"
```

---

## Task 2: Add New Brew Model Columns + Migration

**Files:**
- Modify: `src/beanbay/models/brew.py:180` (add after `total_time`)
- Modify: `src/beanbay/schemas/brew.py` (update BrewCreate, BrewUpdate, BrewRead, BrewListRead)

- [ ] **Step 1: Write integration test for new Brew columns**

File: `tests/integration/test_brews_api.py` (append to existing file)

```python
def test_create_brew_with_new_columns(client):
    """New optimization columns can be set on brew creation."""
    person_id = _create_person(client)
    bean_id = _create_bean(client)
    bag_id = _create_bag(client, bean_id)
    method_id = _create_brew_method(client)
    setup_id = _create_brew_setup(client, method_id)

    resp = client.post(
        BREWS,
        json={
            "bag_id": bag_id,
            "brew_setup_id": setup_id,
            "person_id": person_id,
            "dose": 18.0,
            "brewed_at": datetime.now(timezone.utc).isoformat(),
            "bloom_weight": 45.0,
            "preinfusion_pressure": 3.0,
            "pressure_profile": "flat",
            "brew_mode": "standard",
            "saturation": 0.5,
            "bloom_pause": 5.0,
            "temp_profile": "declining",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["bloom_weight"] == 45.0
    assert data["preinfusion_pressure"] == 3.0
    assert data["pressure_profile"] == "flat"
    assert data["brew_mode"] == "standard"
    assert data["saturation"] == 0.5
    assert data["bloom_pause"] == 5.0
    assert data["temp_profile"] == "declining"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_brews_api.py::test_create_brew_with_new_columns -v`
Expected: FAIL (fields not recognized)

- [ ] **Step 3: Add columns to Brew model**

In `src/beanbay/models/brew.py`, add after `total_time: float | None = None` (line ~180):

```python
    # Optimization parameters — method/capability-specific, all nullable
    bloom_weight: float | None = None
    preinfusion_pressure: float | None = None
    pressure_profile: str | None = None
    brew_mode: str | None = None
    saturation: float | None = None
    bloom_pause: float | None = None
    temp_profile: str | None = None
```

- [ ] **Step 4: Add columns to BrewCreate, BrewUpdate, BrewRead schemas**

In `src/beanbay/schemas/brew.py`:
- Add to `BrewBase` (shared fields): `bloom_weight`, `preinfusion_pressure`, `pressure_profile`, `brew_mode`, `saturation`, `bloom_pause`, `temp_profile` — all `float | None = None` or `str | None = None`.
- Add to `BrewRead` model_validator field extraction list.
- Add to `BrewListRead` if relevant for list display (skip for now — list is already wide).

- [ ] **Step 5: Generate Alembic migration**

Run: `uv run alembic revision --autogenerate -m "add optimization columns to brews"`
Expected: Migration file created in `migrations/versions/`

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/integration/test_brews_api.py::test_create_brew_with_new_columns -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/beanbay/models/brew.py src/beanbay/schemas/brew.py migrations/versions/ tests/integration/test_brews_api.py
git commit -m "feat: add optimization parameter columns to Brew model"
```

---

## Task 3: Create Optimization Models

**Files:**
- Create: `src/beanbay/models/optimization.py`
- Modify: `src/beanbay/models/__init__.py`

- [ ] **Step 1: Create optimization models file**

File: `src/beanbay/models/optimization.py`

```python
"""Optimization models for BayBE integration.

Campaign tracks per-bean per-setup optimization state.
MethodParameterDefault defines per-method parameter ranges (seeded).
BeanParameterOverride allows per-bean range narrowing.
Recommendation stores BayBE suggestions.
OptimizationJob tracks async recommendation tasks.
"""

import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

from beanbay.models.base import uuid4_default


class Campaign(SQLModel, table=True):
    """An optimization campaign for a bean + brew setup combination.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Foreign key to the bean being optimized.
    brew_setup_id : uuid.UUID
        Foreign key to the brew setup being used.
    campaign_json : str | None
        Serialized BayBE Campaign state (opaque blob).
    phase : str
        Current optimization phase: random, learning, optimizing.
    measurement_count : int
        Number of valid measurements fed to the campaign.
    best_score : float | None
        Highest taste score achieved.
    bounds_fingerprint : str | None
        Hash of numeric parameter ranges for change detection.
    param_fingerprint : str | None
        Hash of parameter names for structural change detection.
    created_at : datetime
        Row creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    """

    __tablename__ = "campaigns"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint("bean_id", "brew_setup_id", name="uq_campaign_bean_setup"),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_id: uuid.UUID = Field(foreign_key="beans.id", index=True)
    brew_setup_id: uuid.UUID = Field(foreign_key="brew_setups.id", index=True)

    campaign_json: str | None = None
    phase: str = Field(default="random")
    measurement_count: int = Field(default=0)
    best_score: float | None = None

    bounds_fingerprint: str | None = None
    param_fingerprint: str | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class MethodParameterDefault(SQLModel, table=True):
    """Default parameter range for a brew method (seeded data).

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    brew_method_id : uuid.UUID
        Foreign key to the brew method.
    parameter_name : str
        Brew model column name (e.g. ``"temperature"``, ``"dose"``).
    min_value : float | None
        Lower bound. None for categorical parameters.
    max_value : float | None
        Upper bound. None for categorical parameters.
    step : float | None
        Rounding precision for the parameter.
    allowed_values : str | None
        Comma-separated values for categorical parameters.
    requires : str | None
        Brewer capability gate condition string.
    created_at : datetime
        Row creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    """

    __tablename__ = "method_parameter_defaults"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "brew_method_id", "parameter_name", name="uq_method_param"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    brew_method_id: uuid.UUID = Field(foreign_key="brew_methods.id", index=True)

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    allowed_values: str | None = None
    requires: str | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class BeanParameterOverride(SQLModel, table=True):
    """Per-bean parameter range override.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    bean_id : uuid.UUID
        Foreign key to the bean.
    parameter_name : str
        Brew model column name to override.
    min_value : float | None
        Overridden lower bound (None = use default).
    max_value : float | None
        Overridden upper bound (None = use default).
    created_at : datetime
        Row creation timestamp.
    updated_at : datetime
        Last-modified timestamp.
    """

    __tablename__ = "bean_parameter_overrides"  # type: ignore[assignment]
    __table_args__ = (
        UniqueConstraint(
            "bean_id", "parameter_name", name="uq_bean_param_override"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    bean_id: uuid.UUID = Field(foreign_key="beans.id", index=True)

    parameter_name: str
    min_value: float | None = None
    max_value: float | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class Recommendation(SQLModel, table=True):
    """A BayBE-generated parameter suggestion.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    campaign_id : uuid.UUID
        Foreign key to the parent campaign.
    brew_id : uuid.UUID | None
        Foreign key to the brew (set when user brews this recommendation).
    phase : str
        Optimization phase at generation time.
    predicted_score : float | None
        BayBE predicted taste score.
    predicted_std : float | None
        BayBE prediction uncertainty.
    parameter_values : str
        JSON dict of parameter_name to suggested value.
    status : str
        Lifecycle status: pending, brewed, skipped.
    created_at : datetime
        Row creation timestamp.
    """

    __tablename__ = "recommendations"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaigns.id", index=True)
    brew_id: uuid.UUID | None = Field(
        default=None, foreign_key="brews.id", index=True
    )

    phase: str
    predicted_score: float | None = None
    predicted_std: float | None = None
    parameter_values: str  # JSON

    status: str = Field(default="pending")
    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )


class OptimizationJob(SQLModel, table=True):
    """Async job tracker for BayBE recommendation tasks.

    Attributes
    ----------
    id : uuid.UUID
        Primary key.
    campaign_id : uuid.UUID
        Foreign key to the campaign.
    job_type : str
        Type of job: recommend, rebuild.
    status : str
        Job status: pending, running, completed, failed.
    result_id : uuid.UUID | None
        Recommendation ID when job completes.
    error_message : str | None
        Error details on failure.
    created_at : datetime
        Row creation timestamp.
    completed_at : datetime | None
        Job completion timestamp.
    """

    __tablename__ = "optimization_jobs"  # type: ignore[assignment]

    id: uuid.UUID = Field(default_factory=uuid4_default, primary_key=True)
    campaign_id: uuid.UUID = Field(foreign_key="campaigns.id", index=True)

    job_type: str
    status: str = Field(default="pending", index=True)
    result_id: uuid.UUID | None = None
    error_message: str | None = None

    created_at: datetime = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now()},
    )
    completed_at: datetime | None = None
```

- [ ] **Step 2: Register models in `__init__.py`**

Add to `src/beanbay/models/__init__.py`:

```python
from beanbay.models.optimization import (  # noqa: F401
    BeanParameterOverride,
    Campaign,
    MethodParameterDefault,
    OptimizationJob,
    Recommendation,
)
```

- [ ] **Step 3: Generate Alembic migration**

Run: `uv run alembic revision --autogenerate -m "add optimization models"`

- [ ] **Step 4: Verify migration applies**

Run: `uv run pytest tests/integration/test_brews_api.py::test_create_brew -v`
Expected: PASS (existing tests still work with new tables)

- [ ] **Step 5: Commit**

```bash
git add src/beanbay/models/optimization.py src/beanbay/models/__init__.py migrations/versions/
git commit -m "feat: add optimization database models (Campaign, Recommendation, etc.)"
```

---

## Task 4: Seed Method Parameter Defaults

**Files:**
- Create: `src/beanbay/seed_optimization.py`
- Modify: `src/beanbay/main.py` (call seed function in lifespan)

- [ ] **Step 1: Write integration test for seeded data**

File: `tests/integration/test_optimize_api.py`

```python
"""Integration tests for optimization endpoints."""

import uuid

OPTIMIZE = "/api/v1/optimize"


def _create_brew_method(client, name: str = "espresso") -> str:
    resp = client.post("/api/v1/brew-methods", json={"name": f"{name}_{uuid.uuid4().hex[:8]}"})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_method_defaults_are_seeded(client, session):
    """Method parameter defaults are seeded for espresso on app startup."""
    from beanbay.models.optimization import MethodParameterDefault
    from beanbay.models.tag import BrewMethod
    from sqlmodel import select

    espresso = session.exec(
        select(BrewMethod).where(BrewMethod.name == "espresso")
    ).first()
    if espresso is None:
        pytest.skip("espresso brew method not seeded")

    defaults = session.exec(
        select(MethodParameterDefault).where(
            MethodParameterDefault.brew_method_id == espresso.id
        )
    ).all()
    param_names = {d.parameter_name for d in defaults}
    assert "temperature" in param_names
    assert "dose" in param_names
    assert "yield_amount" in param_names
    # grind_setting should NOT be seeded
    assert "grind_setting" not in param_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_optimize_api.py::test_method_defaults_are_seeded -v`
Expected: FAIL (no seeded data)

- [ ] **Step 3: Create seed_optimization.py**

File: `src/beanbay/seed_optimization.py`

Implement `seed_method_parameter_defaults(session: Session)` — idempotent function that inserts `MethodParameterDefault` rows for all 7 brew methods. Use the exact values from the spec tables. Look up `BrewMethod` by name to get the FK. Skip if the method doesn't exist in the DB yet. Skip if rows already exist for that method.

Reference: spec section "Layer 1: Method Defaults" for all parameter names, ranges, steps, and requires conditions.

- [ ] **Step 4: Call seed function in main.py lifespan**

In `src/beanbay/main.py`, add to the lifespan handler after existing seed calls:

```python
from beanbay.seed_optimization import seed_method_parameter_defaults
# ... inside the with Session block:
seed_method_parameter_defaults(session)
```

- [ ] **Step 5: Run test**

Run: `uv run pytest tests/integration/test_optimize_api.py::test_method_defaults_are_seeded -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/beanbay/seed_optimization.py src/beanbay/main.py tests/integration/test_optimize_api.py
git commit -m "feat: seed method parameter defaults for all brew methods"
```

---

## Task 5: Optimization Schemas

**Files:**
- Create: `src/beanbay/schemas/optimization.py`

- [ ] **Step 1: Create optimization schemas**

File: `src/beanbay/schemas/optimization.py`

Define Pydantic schemas following existing patterns (`src/beanbay/schemas/brew.py`):

```python
# Campaign
CampaignCreate:    bean_id (uuid), brew_setup_id (uuid)
CampaignRead:      id, bean_id, brew_setup_id, phase, measurement_count, best_score,
                   created_at, updated_at, bean_name (computed), brew_setup_name (computed)
CampaignListRead:  id, bean_name, brew_setup_name, phase, measurement_count, best_score, created_at
CampaignDetailRead: extends CampaignRead + effective_ranges (list of EffectiveRange)

EffectiveRange:    parameter_name, min_value, max_value, step, source (str)

# Recommendation
RecommendationRead: id, campaign_id, brew_id, phase, predicted_score, predicted_std,
                    parameter_values (dict), status, created_at

# Job
OptimizationJobRead: id, campaign_id, job_type, status, result_id, error_message,
                     created_at, completed_at

# Bean Overrides
BeanOverrideItem:   parameter_name, min_value (float|None), max_value (float|None)
BeanOverrideRead:   id, bean_id, parameter_name, min_value, max_value, created_at, updated_at
BeanOverridesPut:   overrides (list of BeanOverrideItem)

# Method Defaults
MethodParameterDefaultRead: parameter_name, min_value, max_value, step, requires, allowed_values

# Progress
ConvergenceInfo:    status (str), improvement_rate (float|None)
ScoreHistoryEntry:  shot_number (int), score (float|None), is_failed (bool), phase (str|None)
CampaignProgress:   phase, measurement_count, best_score, convergence, score_history (list)

# Person Preferences
TopBean:            bean_id, name, avg_score, brew_count
FlavorFrequency:    tag, frequency
OriginPreference:   origin, avg_score, brew_count
MethodBreakdown:    method, brew_count, avg_score
PersonPreferences:  person (dict), brew_stats (dict), top_beans, flavor_profile,
                    roast_preference (dict), origin_preferences, method_breakdown
```

- [ ] **Step 2: Verify schemas load without import errors**

Run: `uv run python -c "from beanbay.schemas.optimization import CampaignCreate, CampaignRead; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/beanbay/schemas/optimization.py
git commit -m "feat: add optimization Pydantic schemas"
```

---

## Task 6: Capability Gate Evaluator

**Files:**
- Create: `src/beanbay/services/parameter_ranges.py` (start with gate evaluation only)
- Create: `tests/unit/test_capability_gates.py`

- [ ] **Step 1: Write unit tests for capability gate parsing**

File: `tests/unit/test_capability_gates.py`

```python
"""Unit tests for brewer capability gate evaluation."""

from beanbay.services.parameter_ranges import evaluate_requires


class FakeBrewer:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_none_requires_always_passes():
    assert evaluate_requires(None, FakeBrewer()) is True


def test_not_equal_none():
    brewer = FakeBrewer(preinfusion_type="timed")
    assert evaluate_requires("preinfusion_type != none", brewer) is True


def test_not_equal_none_fails():
    brewer = FakeBrewer(preinfusion_type="none")
    assert evaluate_requires("preinfusion_type != none", brewer) is False


def test_in_list():
    brewer = FakeBrewer(pressure_control_type="electronic")
    assert evaluate_requires(
        "pressure_control_type in (opv_adjustable, electronic, programmable)",
        brewer,
    ) is True


def test_in_list_fails():
    brewer = FakeBrewer(pressure_control_type="fixed")
    assert evaluate_requires(
        "pressure_control_type in (opv_adjustable, electronic, programmable)",
        brewer,
    ) is False


def test_equals_true():
    brewer = FakeBrewer(has_bloom=True)
    assert evaluate_requires("has_bloom == true", brewer) is True


def test_equals_true_fails():
    brewer = FakeBrewer(has_bloom=False)
    assert evaluate_requires("has_bloom == true", brewer) is False


def test_equals_value():
    brewer = FakeBrewer(flow_control_type="programmable")
    assert evaluate_requires("flow_control_type == programmable", brewer) is True


def test_equals_value_fails():
    brewer = FakeBrewer(flow_control_type="none")
    assert evaluate_requires("flow_control_type == programmable", brewer) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_capability_gates.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement evaluate_requires**

File: `src/beanbay/services/parameter_ranges.py`

```python
"""Parameter range computation service.

Provides the 3-layer effective range system and capability gate evaluation.
"""

from __future__ import annotations

import re
from typing import Any


def evaluate_requires(condition: str | None, brewer: Any) -> bool:
    """Evaluate a capability gate condition against a brewer.

    Supported formats:
    - ``"attr != value"``
    - ``"attr == value"`` (including ``"true"``/``"false"`` for booleans)
    - ``"attr in (val1, val2, ...)"``

    Parameters
    ----------
    condition : str | None
        Condition string, or None (always passes).
    brewer : Any
        Object with brewer capability attributes.

    Returns
    -------
    bool
        Whether the condition is satisfied.
    """
    if condition is None:
        return True

    condition = condition.strip()

    # "attr in (val1, val2, ...)"
    m = re.match(r"(\w+)\s+in\s+\(([^)]+)\)", condition)
    if m:
        attr, values_str = m.group(1), m.group(2)
        values = [v.strip() for v in values_str.split(",")]
        return str(getattr(brewer, attr, None)) in values

    # "attr != value"
    m = re.match(r"(\w+)\s*!=\s*(\w+)", condition)
    if m:
        attr, value = m.group(1), m.group(2)
        return str(getattr(brewer, attr, None)) != value

    # "attr == value"
    m = re.match(r"(\w+)\s*==\s*(\w+)", condition)
    if m:
        attr, value = m.group(1), m.group(2)
        actual = getattr(brewer, attr, None)
        if value.lower() == "true":
            return bool(actual) is True
        if value.lower() == "false":
            return bool(actual) is False
        return str(actual) == value

    return False
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_capability_gates.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/beanbay/services/parameter_ranges.py tests/unit/test_capability_gates.py
git commit -m "feat: add capability gate condition evaluator"
```

---

## Task 7: Parameter Range Service — Effective Range Computation

**Files:**
- Modify: `src/beanbay/services/parameter_ranges.py` (add range computation)
- Create: `tests/unit/test_parameter_ranges.py`

- [ ] **Step 1: Write unit tests for effective range computation**

File: `tests/unit/test_parameter_ranges.py`

Test scenarios:
1. Method default only (no brewer, no overrides) → returns method default range
2. Method default + brewer narrows temperature → clipped to brewer min/max
3. Method default + bean override narrows dose → override applied
4. All 3 layers → most restrictive wins
5. Capability-gated parameter excluded when brewer lacks capability
6. Capability-gated parameter included when brewer has capability
7. Grind setting from grinder ring_sizes_json
8. No grinder → grind_setting excluded
9. Invalid range (min >= max after layering) → raises ValueError
10. Categorical parameter → allowed_values passed through, no range computation

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_parameter_ranges.py -v`
Expected: FAIL

- [ ] **Step 3: Implement compute_effective_ranges**

Add to `src/beanbay/services/parameter_ranges.py`:

```python
def compute_effective_ranges(
    method_defaults: list[MethodParameterDefault],
    brewer: Brewer | None,
    grinder: Grinder | None,
    bean_overrides: list[BeanParameterOverride],
) -> list[EffectiveRange]:
```

Logic:
1. For each method default, check `evaluate_requires(default.requires, brewer)` — skip if False.
2. Start with `(default.min_value, default.max_value)`.
3. Apply brewer narrowing: clip temperature to `brewer.temp_min/max`, pressure to `brewer.pressure_min/max`, pre_infusion_time to `0..brewer.preinfusion_max_time`.
4. Apply bean overrides: `max(effective_min, override.min)`, `min(effective_max, override.max)`.
5. If `effective_min >= effective_max`, raise `ValueError`.
6. Add grind_setting from grinder `ring_sizes_json` if grinder present (parse JSON, compute linear bounds).
7. For categoricals: pass through `allowed_values`, skip range computation.
8. Return list of `EffectiveRange` dataclasses.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/unit/test_parameter_ranges.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/beanbay/services/parameter_ranges.py tests/unit/test_parameter_ranges.py
git commit -m "feat: add 3-layer effective parameter range computation"
```

---

## Task 8: Bean Parameter Override Endpoints

**Files:**
- Create: `src/beanbay/routers/optimize.py` (start with override endpoints only)
- Create: `tests/integration/test_bean_overrides_api.py`

- [ ] **Step 1: Write integration tests for bean override CRUD**

File: `tests/integration/test_bean_overrides_api.py`

Test scenarios:
1. `GET /optimize/beans/{bean_id}/overrides` returns empty list initially
2. `PUT /optimize/beans/{bean_id}/overrides` with valid overrides → 200, returns list
3. `GET` after `PUT` → returns the overrides
4. `PUT` again replaces all overrides (old ones removed)
5. `PUT` with empty list clears all overrides
6. `PUT` with invalid bean_id → 404

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_bean_overrides_api.py -v`
Expected: FAIL

- [ ] **Step 3: Implement override endpoints in optimize router**

File: `src/beanbay/routers/optimize.py`

```python
router = APIRouter(tags=["Optimization"])

@router.get("/optimize/beans/{bean_id}/overrides")
@router.put("/optimize/beans/{bean_id}/overrides")
```

Follow existing router patterns. PUT deletes existing overrides for the bean, then inserts new ones.

- [ ] **Step 4: Register router in main.py**

Add to `src/beanbay/main.py`:
```python
from beanbay.routers.optimize import router as optimize_router
# Add to _routers list
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/integration/test_bean_overrides_api.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/beanbay/routers/optimize.py src/beanbay/main.py tests/integration/test_bean_overrides_api.py
git commit -m "feat: add bean parameter override endpoints"
```

---

## Task 9: Campaign CRUD Endpoints

**Files:**
- Modify: `src/beanbay/routers/optimize.py` (add campaign endpoints)
- Modify: `tests/integration/test_optimize_api.py`

- [ ] **Step 1: Write integration tests for campaign CRUD**

Append to `tests/integration/test_optimize_api.py`:

Test scenarios:
1. `POST /optimize/campaigns` creates a campaign → 201
2. `POST` again with same bean+setup returns existing campaign (idempotent) → 200
3. `GET /optimize/campaigns` lists campaigns with filters
4. `GET /optimize/campaigns/{id}` returns detail with effective_ranges
5. `DELETE /optimize/campaigns/{id}` resets campaign state
6. `POST` with invalid bean_id → 404
7. `POST` with invalid brew_setup_id → 404

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_optimize_api.py -v -k "campaign"`
Expected: FAIL

- [ ] **Step 3: Implement campaign endpoints**

Add to `src/beanbay/routers/optimize.py`:

```python
@router.post("/optimize/campaigns", response_model=CampaignDetailRead, status_code=201)
@router.get("/optimize/campaigns", response_model=list[CampaignListRead])
@router.get("/optimize/campaigns/{campaign_id}", response_model=CampaignDetailRead)
@router.delete("/optimize/campaigns/{campaign_id}")
```

The POST endpoint:
1. Validate bean_id and brew_setup_id exist
2. Check for existing campaign with same bean+setup → return it if found
3. Create new Campaign row
4. Compute effective_ranges using `compute_effective_ranges()` from the parameter range service
5. Return campaign detail with ranges

The DELETE endpoint:
1. Set `campaign_json = None`, `phase = "random"`, `measurement_count = 0`, `best_score = None`
2. Delete related recommendations
3. Clear fingerprints

- [ ] **Step 4: Add method defaults endpoint**

```python
@router.get("/optimize/defaults/{brew_method_id}", response_model=list[MethodParameterDefaultRead])
```

Query `MethodParameterDefault` rows for the given method.

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/integration/test_optimize_api.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/beanbay/routers/optimize.py tests/integration/test_optimize_api.py
git commit -m "feat: add campaign CRUD and method defaults endpoints"
```

---

## Task 10: Taskiq Broker Setup

**Files:**
- Create: `src/beanbay/services/taskiq_broker.py`
- Modify: `src/beanbay/main.py` (start broker in lifespan)

- [ ] **Step 1: Create taskiq broker module**

File: `src/beanbay/services/taskiq_broker.py`

Use Context7 to check taskiq documentation for InMemoryBroker setup. The module should:
1. Create an `InMemoryBroker` instance
2. Define a `generate_recommendation` task (placeholder that just marks job as completed)
3. Export the broker and task

```python
from taskiq import InMemoryBroker

broker = InMemoryBroker()

@broker.task
async def generate_recommendation(job_id: str) -> None:
    """Generate a BayBE recommendation for the given job.

    Placeholder — full implementation in Task 11.
    """
    pass
```

- [ ] **Step 2: Start broker in app lifespan**

In `src/beanbay/main.py`, add broker startup/shutdown to lifespan:

```python
from beanbay.services.taskiq_broker import broker

# In lifespan, after seed:
await broker.startup()
# In yield cleanup:
await broker.shutdown()
```

Note: The lifespan becomes async. FastAPI supports async lifespan handlers.

- [ ] **Step 3: Verify app starts without errors**

Run: `uv run python -c "from beanbay.services.taskiq_broker import broker; print(type(broker))"`
Expected: prints broker type

- [ ] **Step 4: Commit**

```bash
git add src/beanbay/services/taskiq_broker.py src/beanbay/main.py
git commit -m "feat: add taskiq InMemoryBroker setup"
```

---

## Task 11: Optimizer Service (BayBE Integration)

**Files:**
- Create: `src/beanbay/services/optimizer.py`

- [ ] **Step 1: Create optimizer service**

File: `src/beanbay/services/optimizer.py`

Use Context7 to check BayBE documentation for:
- `Campaign` creation with `TwoPhaseMetaRecommender`
- `NumericalContinuousParameter`, `CategoricalParameter`
- `NumericalTarget`, `SingleTargetObjective`
- `Campaign.recommend()`, `Campaign.add_measurements()`
- `Campaign.to_json()`, `Campaign.from_json()`

Implement:

```python
class OptimizerService:
    """Manages BayBE campaigns and recommendations."""

    @staticmethod
    def build_campaign(effective_ranges: list[EffectiveRange]) -> BaybeCampaign:
        """Build a BayBE Campaign from effective parameter ranges."""

    @staticmethod
    def recommend(campaign: BaybeCampaign, measurements_df: pd.DataFrame) -> dict:
        """Generate a recommendation. Returns dict of param_name → value."""

    @staticmethod
    def determine_phase(campaign: BaybeCampaign, measurement_count: int) -> str:
        """Determine current phase: random, learning, optimizing."""

    @staticmethod
    def compute_fingerprints(effective_ranges: list[EffectiveRange]) -> tuple[str, str]:
        """Compute bounds + param fingerprints for change detection."""
```

- [ ] **Step 2: Implement the generate_recommendation task**

Update `src/beanbay/services/taskiq_broker.py` to replace the placeholder with the full worker logic from the spec (steps 1-11 in Worker Task section).

The task function:
1. Opens a DB session
2. Loads the Campaign row
3. Loads the BrewSetup → Brewer, Grinder
4. Queries MethodParameterDefaults for the setup's brew method
5. Queries BeanParameterOverrides for the campaign's bean
6. Computes effective ranges
7. Checks fingerprints — rebuilds BayBE campaign if changed
8. Queries valid measurements (brews with scores, not failed)
9. Adds measurements to BayBE campaign
10. Calls campaign.recommend(batch_size=1)
11. Rounds values, snaps grind steps
12. Creates Recommendation row
13. Updates Campaign (campaign_json, phase, measurement_count, best_score)
14. Updates OptimizationJob → completed

- [ ] **Step 3: Commit**

```bash
git add src/beanbay/services/optimizer.py src/beanbay/services/taskiq_broker.py
git commit -m "feat: add BayBE optimizer service and recommendation worker"
```

---

## Task 12: Recommendation & Job Endpoints

**Files:**
- Modify: `src/beanbay/routers/optimize.py` (add recommendation + job endpoints)
- Modify: `tests/integration/test_optimize_api.py`

- [ ] **Step 1: Write integration tests for recommendation flow**

Append to `tests/integration/test_optimize_api.py`:

Test scenarios:
1. `POST /optimize/campaigns/{id}/recommend` → 202, returns `{job_id, status: "pending"}`
2. `GET /optimize/jobs/{job_id}` → returns job status
3. `GET /optimize/campaigns/{id}/recommendations` → lists recommendations
4. `GET /optimize/recommendations/{id}` → recommendation detail
5. `POST /optimize/recommendations/{id}/skip` → status becomes "skipped"
6. `POST /optimize/recommendations/{id}/link` with valid brew_id → status becomes "brewed"
7. `POST /optimize/recommendations/{id}/link` with invalid brew_id → 404

Note: For integration tests, the async task runs synchronously in InMemoryBroker, so results should be available immediately after the POST.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_optimize_api.py -v -k "recommend"`
Expected: FAIL

- [ ] **Step 3: Implement endpoints**

Add to `src/beanbay/routers/optimize.py`:

```python
@router.post("/optimize/campaigns/{campaign_id}/recommend", status_code=202)
# Creates OptimizationJob, enqueues taskiq task, returns job_id

@router.get("/optimize/jobs/{job_id}", response_model=OptimizationJobRead)
# Polls job status

@router.get("/optimize/campaigns/{campaign_id}/recommendations")
# Lists recommendations for campaign

@router.get("/optimize/recommendations/{recommendation_id}")
# Recommendation detail

@router.post("/optimize/recommendations/{recommendation_id}/skip")
# Set status = "skipped"

@router.post("/optimize/recommendations/{recommendation_id}/link")
# Validate brew_id, set brew_id + status = "brewed"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/integration/test_optimize_api.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add src/beanbay/routers/optimize.py tests/integration/test_optimize_api.py
git commit -m "feat: add recommendation and job polling endpoints"
```

---

## Task 13: Campaign Progress Endpoint

**Files:**
- Modify: `src/beanbay/routers/optimize.py`
- Modify: `tests/integration/test_optimize_api.py`

- [ ] **Step 1: Write integration test for progress endpoint**

Test scenarios:
1. Campaign with no brews → `getting_started`, empty score_history
2. Campaign with a few brews → returns score_history with shot numbers
3. Convergence status reflects measurement count and phase

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_optimize_api.py -v -k "progress"`
Expected: FAIL

- [ ] **Step 3: Implement progress endpoint**

Add to `src/beanbay/routers/optimize.py`:

```python
@router.get("/optimize/campaigns/{campaign_id}/progress", response_model=CampaignProgress)
```

Logic:
1. Load campaign
2. Query brews for this bean+setup, ordered by `brewed_at`
3. Build `score_history` list with shot_number, score, is_failed
4. Compute convergence status:
   - `getting_started`: < 3 valid measurements
   - `exploring`: campaign phase is "random"
   - `learning`: phase is "learning", improvement rate > threshold
   - `converged`: phase is "optimizing", improvement rate < threshold
5. Improvement rate: compare best score of last 3 shots to best score of previous 3

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/integration/test_optimize_api.py -v -k "progress"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/beanbay/routers/optimize.py tests/integration/test_optimize_api.py
git commit -m "feat: add campaign progress and convergence endpoint"
```

---

## Task 14: Per-Person Preferences Endpoint

**Files:**
- Modify: `src/beanbay/routers/optimize.py`
- Modify: `tests/integration/test_optimize_api.py`

- [ ] **Step 1: Write integration test for preferences**

Test scenarios:
1. Person with brews → returns top_beans, flavor_profile, method_breakdown
2. Person with no brews → returns empty lists, zero counts
3. Invalid person_id → 404

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_optimize_api.py -v -k "preference"`
Expected: FAIL

- [ ] **Step 3: Implement preferences endpoint**

Add to `src/beanbay/routers/optimize.py`:

```python
@router.get("/optimize/people/{person_id}/preferences", response_model=PersonPreferences)
```

Logic — all computed from SQL queries:
1. `brew_stats`: COUNT + AVG(score) from brews joined with brew_tastes, filtered by person_id
2. `top_beans`: GROUP BY bean, ORDER BY AVG(score) DESC, LIMIT 10
3. `flavor_profile`: COUNT flavor_tag occurrences across person's brew_tastes
4. `roast_preference`: AVG(roast_degree) + distribution buckets from beans
5. `origin_preferences`: GROUP BY origin, ORDER BY AVG(score) DESC
6. `method_breakdown`: GROUP BY brew_method, COUNT + AVG(score)

Query chain: `Brew → BrewTaste (for scores) → Bag → Bean → origins/flavor_tags`

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/integration/test_optimize_api.py -v -k "preference"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/beanbay/routers/optimize.py tests/integration/test_optimize_api.py
git commit -m "feat: add per-person bean preference analytics endpoint"
```

---

## Task 15: Final Integration — Run Full Test Suite

**Files:**
- No new files

- [ ] **Step 1: Run complete test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run linter**

Run: `uvx prek --all-files`
Expected: No errors

- [ ] **Step 3: Verify app starts cleanly**

Run: `uv run fastapi dev src/beanbay/main.py &` then `curl http://localhost:8000/health`
Expected: `{"status": "ok"}`

Then: `curl http://localhost:8000/api/v1/optimize/campaigns`
Expected: `[]` (empty list)

Kill the server after verification.

- [ ] **Step 4: Regenerate frontend types**

Run: (with API running) `cd frontend && bun run generate-types`
Expected: `src/api/types.ts` updated with new optimization endpoints and schemas

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/types.ts
git commit -m "chore: regenerate frontend types with optimization endpoints"
```

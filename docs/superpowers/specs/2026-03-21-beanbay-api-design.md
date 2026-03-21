# BeanBay REST API — Design Spec

## Overview

BeanBay is a FastAPI + SQLModel application for tracking coffee brews, equipment,
beans, and taste assessments. It provides a RESTful API for a local home-network
deployment, with no authentication required. The API will later support a frontend
and BayBE-based Bayesian optimization (both out of scope for this phase).

**Stack:** FastAPI, SQLModel, Pydantic Settings, Alembic, Pint, SQLite (default,
configurable via `BEANBAY_DATABASE_URL`).

---

## 1. Project Structure

```
src/beanbay/
├── __init__.py
├── _version.py                  # existing (setuptools_scm)
├── main.py                      # FastAPI app, lifespan (migrations + seed)
├── config.py                    # pydantic-settings
├── database.py                  # engine, sessionmaker, get_session DI dependency
├── models/
│   ├── __init__.py              # re-export all models (for Alembic metadata)
│   ├── base.py                  # TimestampMixin, uuid PK base, soft-delete (retired_at)
│   ├── bean.py                  # Bean, Bag, bean_origins/processes/varieties junctions
│   ├── equipment.py             # Grinder, Brewer, Paper, Water, WaterMineral,
│   │                            #   brewer_methods, brewer_stop_modes junctions
│   ├── brew.py                  # BrewMethod, BrewSetup, Brew, BrewTaste,
│   │                            #   brew_taste_flavor_tags junction
│   ├── person.py                # Person
│   ├── rating.py                # BeanRating, BeanTaste, bean_taste_flavor_tags junction
│   └── tag.py                   # FlavorTag, Origin, Roaster, ProcessMethod,
│                                #   BeanVariety, StopMode
├── routers/
│   ├── __init__.py
│   ├── beans.py                 # /beans + /beans/{id}/bags
│   ├── equipment.py             # /grinders, /brewers, /papers, /waters
│   ├── brew_setups.py           # /brew-setups
│   ├── brews.py                 # /brews
│   ├── ratings.py               # /bean-ratings
│   ├── people.py                # /people
│   └── lookup.py                # /flavor-tags, /origins, /roasters,
│                                #   /process-methods, /bean-varieties,
│                                #   /brew-methods, /stop-modes
├── schemas/
│   ├── __init__.py
│   ├── common.py                # PaginatedResponse[T], unit conversion query params
│   ├── bean.py                  # BeanBase/Create/Update/Read, BagBase/Create/Update/Read
│   ├── equipment.py             # Grinder/Brewer/Paper/Water schemas
│   ├── brew.py                  # BrewSetup/Brew/BrewTaste schemas
│   ├── rating.py                # BeanRating/BeanTaste schemas
│   ├── person.py                # Person schemas
│   └── tag.py                   # FlavorTag/Origin/Roaster/ProcessMethod/BeanVariety/StopMode
├── utils/
│   ├── grinder_display.py       # to_display / from_display (cherry-picked from main)
│   ├── units.py                 # pint-based unit conversion helpers
│   └── brewer_capabilities.py   # derive_tier() (cherry-picked from main)
├── seed.py                      # default brew methods, stop modes, default person
migrations/                      # Alembic (project root, alongside alembic.ini)
```

---

## 2. Data Model

### 2.1 Shared Patterns

All table models use:

- **UUID4 primary keys** via `Field(default_factory=uuid4, primary_key=True)`.
- **Soft delete** via `retired_at: datetime | None = None`. No `is_retired` column;
  derived as a computed property in read schemas: `is_retired = retired_at is not None`.
  List queries filter `retired_at IS NULL` by default; `?include_retired=true` to include.
- **Timestamps**: `created_at: datetime` on all models, using
  `Field(sa_column_kwargs={"server_default": func.now()})` for DB-side generation.
  `updated_at: datetime` on all updatable entities (Bean, Bag, Brew, BrewSetup,
  BrewTaste, BeanTaste, Brewer, Grinder, Paper, Water, Person). Note:
  `datetime.utcnow` is deprecated in Python 3.12+; always use `datetime.now(UTC)`
  for Python-side timestamps or prefer DB-side `server_default`.

**Exceptions to shared patterns:**
- **WaterMineral** has no `created_at`, `updated_at`, or `retired_at`. Minerals are
  managed as a sub-collection of Water — replaced inline on Water update
  (delete-all-and-reinsert). This is intentional: minerals have no independent
  lifecycle.
- **BrewTaste / BeanTaste** have `created_at` and `updated_at` but no `retired_at`.
  Taste records are created/deleted alongside their parent Brew or BeanRating —
  they have no independent soft-delete lifecycle.
- **Lookup tables** (FlavorTag, Origin, etc.) have `created_at` but no `updated_at`
  (only the name can change, which is rare).

**SQLModel inheritance pattern:**

```python
class BeanBase(SQLModel):
    name: str
    roaster_id: uuid.UUID | None = None
    notes: str | None = None

class Bean(BeanBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()})
    retired_at: datetime | None = None

class BeanCreate(BeanBase):
    origin_ids: list[uuid.UUID] = []
    process_ids: list[uuid.UUID] = []
    variety_ids: list[uuid.UUID] = []

class BeanUpdate(SQLModel):
    name: str | None = None
    roaster_id: uuid.UUID | None = None
    # ... all optional

class BeanRead(BeanBase):
    id: uuid.UUID
    created_at: datetime
    retired_at: datetime | None
    is_retired: bool  # computed via @model_validator
    origins: list[OriginRead]
    processes: list[ProcessMethodRead]
    varieties: list[BeanVarietyRead]
```

Update uses `db_obj.sqlmodel_update(update.model_dump(exclude_unset=True))`.

### 2.2 Lookup Tables

Small reference tables for autocomplete and deduplication. All have the same shape.

| Table | Fields | Notes |
|---|---|---|
| `FlavorTag` | id (UUID PK), name (str, unique) | shared by BrewTaste and BeanTaste |
| `Origin` | id (UUID PK), name (str, unique) | e.g. Ethiopia, Colombia |
| `Roaster` | id (UUID PK), name (str, unique) | e.g. Onyx Coffee Lab |
| `ProcessMethod` | id (UUID PK), name (str, unique) | e.g. washed, natural, honey |
| `BeanVariety` | id (UUID PK), name (str, unique) | e.g. bourbon, gesha, caturra |
| `BrewMethod` | id (UUID PK), name (str, unique) | seeded: espresso, pour-over, french-press, aeropress, turkish, moka-pot, cold-brew |
| `StopMode` | id (UUID PK), name (str, unique) | seeded: manual, timed, volumetric, gravimetric |

### 2.3 Person

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str, unique | |
| is_default | bool | default=False, server ensures at most one is True |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | soft delete |

Configurable default person name via `BEANBAY_DEFAULT_PERSON_NAME` (default: "Default").
Seeded on startup.

### 2.4 Bean & Bag

**Bean** (product identity):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str | |
| roaster_id | FK -> Roaster? | |
| notes | str? | |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

Many-to-many relationships via junction tables:
- `bean_origins` -> Origin
- `bean_processes` -> ProcessMethod
- `bean_varieties` -> BeanVariety

**Bag** (purchase instance):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| bean_id | FK -> Bean | |
| roast_date | date? | |
| opened_at | date? | |
| weight | float | canonical: grams |
| price | float? | user's local currency, no currency conversion |
| is_preground | bool | default=False |
| notes | str? | |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

### 2.5 Equipment

**Grinder:**

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str | |
| dial_type | enum: stepless/stepped | |
| display_format | str | default="decimal" |
| ring_sizes_json | str? | JSON list of [min, max, step] tuples per ring |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

Grinder display conversion (canonical float <-> display notation like "2.5.1") is
handled by standalone functions in `utils/grinder_display.py`, cherry-picked and
adapted from the main branch.

**GrinderRead schema** exposes the ring config as structured data (not raw JSON)
so the frontend can build a fully dynamic grind input widget:

```json
{
  "id": "...",
  "name": "1Zpresso JX-Pro",
  "dial_type": "stepped",
  "grind_range": {
    "min": 0,
    "max": 200,
    "step": 1.0
  },
  "rings": [
    {"label": "rotations", "min": 0, "max": 4, "step": 1},
    {"label": "number",    "min": 0, "max": 9, "step": 1},
    {"label": "tick",      "min": 0, "max": 3, "step": 1}
  ]
}
```

- `grind_range` is computed from the ring config: total canonical min/max/step.
- `rings` is the structured form of `ring_sizes_json`. One entry per ring.
- Single-ring grinders (Niche Zero, Comandante) have one entry in `rings`.
- The frontend renders one input per ring (constrained by min/max/step) plus a
  slider from `grind_range.min` to `grind_range.max`. Changing the slider updates
  the per-ring values and vice versa. The decomposition algorithm (canonical ↔
  per-ring) is the same as `to_display`/`from_display` and is simple enough to
  implement client-side given the ring definitions.

**GrinderCreate/GrinderUpdate** accepts the same `rings` structure (list of
`{label, min, max, step}` dicts). The API serializes to `ring_sizes_json` for
DB storage and computes `display_format` from the ring count.

**Brewer** (full capability model):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str | |
| temp_control_type | str enum | none / preset / pid / profiling |
| temp_min | float? | celsius |
| temp_max | float? | celsius |
| temp_step | float? | celsius resolution |
| preinfusion_type | str enum | none / fixed / timed / adjustable_pressure / programmable / manual |
| preinfusion_max_time | float? | seconds |
| pressure_control_type | str enum | fixed / opv_adjustable / electronic / manual_profiling / programmable |
| pressure_min | float? | bar |
| pressure_max | float? | bar |
| flow_control_type | str enum | none / manual_paddle / manual_valve / programmable |
| saturation_flow_rate | float? | ml/s |
| has_bloom | bool | default=False |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

Many-to-many relationships:
- `brewer_methods` -> BrewMethod
- `brewer_stop_modes` -> StopMode

Capability fields are flat on the Brewer table (not normalized into separate config
tables). Nullable range fields (e.g. `temp_min`/`temp_max`) are only meaningful when
the corresponding control type supports them (e.g. `temp_control_type` is "pid" or
"profiling"). This is a deliberate trade-off: the flat design gives BayBE direct
single-query access to all capability bounds for search space construction, and the
1:1 nature of these configs makes separate tables unnecessary overhead.

Computed `tier` (1-5) via `utils/brewer_capabilities.derive_tier()`, cherry-picked
from main branch. Returned in `BrewerRead` as a computed field. Tier levels:
- **Tier 1 — Basic:** grind + dose + yield only (Gaggia Classic stock, Bambino preset)
- **Tier 2 — Temperature:** + PID/profiling temp control (Rancilio Silvia Pro X)
- **Tier 3 — Pre-infusion:** + timed/adjustable pre-infusion (Sage Dual Boiler)
- **Tier 4 — Pressure & Flow:** + manual profiling or paddle/valve (lever machines)
- **Tier 5 — Full Programmable:** + programmable flow control (Decent DE1, Meticulous)

Used by the frontend to scale UI complexity, and later by BayBE to select which
parameters to include in the optimization search space.

**Paper:**

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str | |
| notes | str? | |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

**Water:**

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str | |
| notes | str? | |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

**WaterMineral** (normalized):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| water_id | FK -> Water | |
| mineral_name | str | e.g. Ca, Mg, Na, Cl, SO4 |
| ppm | float | |

Unique constraint on `(water_id, mineral_name)`. No timestamps or soft-delete — minerals
are a sub-collection of Water, managed via delete-all-and-reinsert on Water update.

### 2.6 Brew Domain

**BrewSetup** (reusable equipment combination):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| name | str? | |
| brew_method_id | FK -> BrewMethod | |
| grinder_id | FK -> Grinder? | nullable (preground beans) |
| brewer_id | FK -> Brewer? | nullable |
| paper_id | FK -> Paper? | nullable (espresso, french press) |
| water_id | FK -> Water? | nullable |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | retire, not delete |

**Brew** (a single brew record):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| bag_id | FK -> Bag | which bag was used |
| brew_setup_id | FK -> BrewSetup | equipment combination |
| person_id | FK -> Person | who brewed |
| grind_setting | float? | canonical numeric (null if preground) |
| temperature | float? | celsius (null for cold-brew) |
| pressure | float? | bar (null for brewers without adjustable pressure) |
| flow_rate | float? | ml/s (null for brewers without flow control) |
| dose | float | grams |
| yield_amount | float? | grams |
| pre_infusion_time | float? | seconds |
| total_time | float? | seconds |
| stop_mode_id | FK -> StopMode? | which stop mode was used for this brew |
| is_failed | bool | default=False |
| notes | str? | |
| brewed_at | datetime | when the brew happened |
| created_at | datetime | |
| updated_at | datetime | |
| retired_at | datetime? | |

**Grind setting in API schemas:**

The DB stores `grind_setting` as a canonical `float`. The API exposes **both**
representations so the frontend has full flexibility:

```json
// BrewRead response — both values provided
{
  "grind_setting": 101.0,
  "grind_setting_display": "2.5.1"
}

// BrewCreate/BrewUpdate request — accept EITHER
{"grind_setting": 101.0}              // canonical float (from slider)
{"grind_setting_display": "2.5.1"}    // display notation (from ring inputs)
// If both provided, grind_setting_display takes precedence.
// If neither, null (preground bag).
```

Conversion uses the brew-setup's grinder ring config via `to_display`/`from_display`.
The frontend can use the grinder's `rings` and `grind_range` (from `GrinderRead`)
to build a synced slider + per-ring input widget entirely from API data.

**BrewTaste** (subjective assessment, 1:1 with Brew):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| brew_id | FK -> Brew, unique | |
| score | float? | 0-10, overall assessment — **the BayBE optimization objective** |
| acidity | float? | 0-10 |
| sweetness | float? | 0-10 |
| body | float? | 0-10 |
| bitterness | float? | 0-10 |
| aroma | float? | 0-10 |
| intensity | float? | 0-10 |
| notes | str? | |
| created_at | datetime | |
| updated_at | datetime | |

`score` is the overall taste assessment and serves as the primary scalar objective
for BayBE optimization. Sub-dimensions (acidity, sweetness, etc.) are informational
and help the user understand *why* a brew scored the way it did.

No `retired_at` — taste records have no independent lifecycle; they are created/
deleted alongside their parent Brew.

Many-to-many: `brew_taste_flavor_tags` -> FlavorTag.

### 2.7 Rating Domain

**BeanRating** (per person, per bean — multiple over time allowed):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| bean_id | FK -> Bean | |
| person_id | FK -> Person | |
| rated_at | datetime | when the rating was given |
| created_at | datetime | |
| retired_at | datetime? | |

No unique constraint on `(bean_id, person_id)` — multiple ratings over time are
allowed. The latest by `rated_at` is the "current" rating. New ratings create new
rows (append-only pattern).

**BeanTaste** (1:1 with BeanRating):

| Field | Type | Notes |
|---|---|---|
| id | UUID4 PK | |
| bean_rating_id | FK -> BeanRating, unique | |
| score | float? | 0-10 |
| acidity | float? | 0-10 |
| sweetness | float? | 0-10 |
| body | float? | 0-10 |
| bitterness | float? | 0-10 |
| aroma | float? | 0-10 |
| intensity | float? | 0-10 |
| notes | str? | |
| created_at | datetime | |
| updated_at | datetime | |

No `retired_at` — taste records have no independent lifecycle; they are created/
deleted alongside their parent BeanRating.

Many-to-many: `bean_taste_flavor_tags` -> FlavorTag.

### 2.8 Junction Tables Summary

| Junction | Left | Right |
|---|---|---|
| `bean_origins` | Bean | Origin |
| `bean_processes` | Bean | ProcessMethod |
| `bean_varieties` | Bean | BeanVariety |
| `brewer_methods` | Brewer | BrewMethod |
| `brewer_stop_modes` | Brewer | StopMode |
| `brew_taste_flavor_tags` | BrewTaste | FlavorTag |
| `bean_taste_flavor_tags` | BeanTaste | FlavorTag |

### 2.9 ERD

```
Person --1:N--> Brew
Person --1:N--> BeanRating

Roaster --1:N--> Bean
Bean --N:M--> Origin          (via bean_origins)
Bean --N:M--> ProcessMethod   (via bean_processes)
Bean --N:M--> BeanVariety     (via bean_varieties)
Bean --1:N--> Bag --1:N--> Brew
Bean --1:N--> BeanRating --1:1--> BeanTaste --N:M--> FlavorTag

Brew --1:1--> BrewTaste --N:M--> FlavorTag
Brew --N:1--> BrewSetup

BrewSetup --N:1--> BrewMethod
BrewSetup --N:1--> Grinder?
BrewSetup --N:1--> Brewer?
BrewSetup --N:1--> Paper?
BrewSetup --N:1--> Water --1:N--> WaterMineral

Brewer --N:M--> BrewMethod    (via brewer_methods)
Brewer --N:M--> StopMode      (via brewer_stop_modes)
```

### 2.10 Future BayBE Integration Notes

BayBE (Bayesian optimization) integration is out of scope for this phase, but the
data model is designed to support it without schema changes:

- **Campaign key:** `(brew_setup_id, bean_id)` — the natural compound key for an
  optimization campaign. A future `Campaign` table will FK to both.
- **Search space:** Grinder `grind_range` + brewer capability bounds (`temp_min/max`,
  `pressure_min/max`, etc.) provide all parameter ranges BayBE needs.
- **Observations:** Brew records (grind_setting, temperature, pressure, flow_rate,
  dose, yield_amount, pre_infusion_time, total_time) + `BrewTaste.score` as the
  objective. All stored as canonical floats — no conversion needed for BayBE.
- **Tier gating:** `derive_tier()` determines which parameters to include in the
  search space per brewer.

No additional models or columns will be needed for BayBE — only a Campaign/
PendingRecommendation table and a service layer on top of existing data.

---

## 3. API Design

All endpoints prefixed with `/api/v1`. REST conventions: plural nouns, proper HTTP
methods, appropriate status codes (201 on create, 204 on delete, 404 on not found,
422 on validation error).

### 3.1 Lookup/Reference Resources

All lookup tables share the same CRUD pattern:

| Method | Path | Notes |
|---|---|---|
| GET | `/{resource}` | list with `?q=` prefix search for autocomplete |
| POST | `/{resource}` | create |
| GET | `/{resource}/{id}` | detail |
| PATCH | `/{resource}/{id}` | update |
| DELETE | `/{resource}/{id}` | soft-delete |

Resources: `/flavor-tags`, `/origins`, `/roasters`, `/process-methods`,
`/bean-varieties`, `/brew-methods`, `/stop-modes`.

All list endpoints support `?q=<search>` for case-insensitive prefix/contains
matching to power frontend autocomplete.

### 3.2 People

| Method | Path | Notes |
|---|---|---|
| GET | `/people` | list |
| POST | `/people` | create |
| GET | `/people/{id}` | detail |
| PATCH | `/people/{id}` | update (including `is_default: true` — server unsets previous) |
| DELETE | `/people/{id}` | soft-delete |

### 3.3 Beans & Bags

| Method | Path | Notes |
|---|---|---|
| GET | `/beans` | list, filterable by roaster/origin/process/variety |
| POST | `/beans` | create, body includes origin_ids, process_ids, variety_ids |
| GET | `/beans/{id}` | detail with nested bags, latest rating per person |
| PATCH | `/beans/{id}` | update |
| DELETE | `/beans/{id}` | soft-delete |
| GET | `/beans/{bean_id}/bags` | list bags for a bean |
| POST | `/beans/{bean_id}/bags` | create bag |
| GET | `/bags` | top-level list, filterable by bean_id/is_preground/opened_after |
| GET | `/bags/{id}` | detail (top-level for direct access) |
| PATCH | `/bags/{id}` | update |
| DELETE | `/bags/{id}` | soft-delete |

`GET /bags` enables a "pantry" view showing all active bags across all beans,
sortable by roast_date or opened_at. Also useful for the brew form's bag picker.

### 3.4 Equipment

**Grinders:**

| Method | Path | Notes |
|---|---|---|
| GET | `/grinders` | list |
| POST | `/grinders` | create (includes ring_sizes config) |
| GET | `/grinders/{id}` | detail |
| PATCH | `/grinders/{id}` | update |
| DELETE | `/grinders/{id}` | soft-delete |

Grind setting display conversion happens transparently at the serialization
boundary (same layer as unit conversion). No separate convert endpoint.

**Brewers:**

| Method | Path | Notes |
|---|---|---|
| GET | `/brewers` | list |
| POST | `/brewers` | create, body includes method_ids, stop_mode_ids |
| GET | `/brewers/{id}` | detail, includes computed `tier`, nested `methods` and `stop_modes` |
| PATCH | `/brewers/{id}` | update |
| DELETE | `/brewers/{id}` | soft-delete |

**Papers:** Standard CRUD at `/papers`.

**Waters:**

| Method | Path | Notes |
|---|---|---|
| GET | `/waters` | list |
| POST | `/waters` | create with inline minerals array |
| GET | `/waters/{id}` | detail with nested minerals |
| PATCH | `/waters/{id}` | update |
| DELETE | `/waters/{id}` | soft-delete |

Water mineral update strategy: if `minerals` is present in the PATCH body, the
existing minerals are deleted and replaced with the provided list (delete-all-and-
reinsert). If `minerals` is omitted from the PATCH body (`exclude_unset=True`),
minerals are not touched. Partial mineral updates are not supported — always send
the full mineral list when changing minerals.

Water create/update example:
```json
{
  "name": "Barista Hustle #4",
  "notes": "Light and bright",
  "minerals": [
    {"mineral_name": "Ca", "ppm": 40.0},
    {"mineral_name": "Mg", "ppm": 16.0}
  ]
}
```

### 3.5 Brew Setups

| Method | Path | Notes |
|---|---|---|
| GET | `/brew-setups` | list, filterable by method/grinder/brewer/has_grinder |
| POST | `/brew-setups` | create |
| GET | `/brew-setups/{id}` | detail with nested equipment names |
| PATCH | `/brew-setups/{id}` | update |
| DELETE | `/brew-setups/{id}` | retire (soft-delete) |

### 3.6 Brews

| Method | Path | Notes |
|---|---|---|
| GET | `/brews` | list, filterable by person_id/bean_id/bag_id/brew_setup_id/date range |
| POST | `/brews` | create, body includes optional nested `taste` object |
| GET | `/brews/{id}` | detail with full nested data |
| PATCH | `/brews/{id}` | update brew fields |
| DELETE | `/brews/{id}` | soft-delete |
| PUT | `/brews/{id}/taste` | create or replace taste assessment |
| PATCH | `/brews/{id}/taste` | partial update taste |
| DELETE | `/brews/{id}/taste` | remove taste assessment (204) |

Brew responses include both `grind_setting` (canonical float) and
`grind_setting_display` (human-readable notation). Brew create/update accepts
either — see Section 2.6 for details. Conversion uses the brew-setup's grinder
ring config.

**List vs detail nesting:**

- `GET /brews` (list) uses `BrewListRead`: includes `bag.bean.name`,
  `brew_setup.brew_method.name`, `person.name`, `taste.score`,
  `grind_setting_display`. Enough for a list view without extra calls.
- `GET /brews/{id}` (detail) uses `BrewRead`: full nested setup with equipment,
  full bag with bean, full taste with flavor tags, all parameters.

**Filtering for BayBE campaigns:** `GET /brews` supports AND-composed filters.
`?brew_setup_id=X&bean_id=Y` returns all brews for that setup + bean combination
across all bags. The `bean_id` filter resolves through `Bag.bean_id`, so the
caller does not need to enumerate individual bag IDs.

### 3.7 Bean Ratings

| Method | Path | Notes |
|---|---|---|
| GET | `/beans/{bean_id}/ratings` | filterable by `?person_id=`, ordered by rated_at desc |
| POST | `/beans/{bean_id}/ratings` | new rating (append-only, creates new entry) |
| GET | `/bean-ratings/{id}` | detail with nested taste |
| DELETE | `/bean-ratings/{id}` | soft-delete |
| PUT | `/bean-ratings/{id}/taste` | create or replace taste |
| PATCH | `/bean-ratings/{id}/taste` | partial update taste |
| DELETE | `/bean-ratings/{id}/taste` | remove taste assessment (204) |

BeanRatings are append-only by design (new rating = new row). No PATCH on BeanRating
itself — to "update" a rating, create a new one. DELETE (soft-delete) is available
for removing erroneous entries. Latest rating per person is retrieved via standard
query params (`?limit=1&sort_by=rated_at&sort_dir=desc`).

### 3.8 Query Parameters

Common across all list endpoints:

| Param | Type | Default | Notes |
|---|---|---|---|
| `include_retired` | bool | false | include soft-deleted items |
| `limit` | int | 50 | max 200 |
| `offset` | int | 0 | |
| `sort_by` | str | varies | validated against per-resource allowlist |
| `sort_dir` | asc/desc | desc for dates, asc for names | |
| `q` | str | — | prefix/contains search (lookup tables) |

`sort_by` is validated against an allowlist of sortable fields per resource. Invalid
field names return 422. This prevents SQL injection via column name.

### 3.9 Unit Conversion

| Param | Values | Default |
|---|---|---|
| `?units=metric` | grams, celsius, ml | metric |
| `?units=imperial` | oz, fahrenheit, fl oz | |

Internal storage is always canonical (grams, celsius, seconds, ml). The `pint`
library handles conversion at the serialization boundary. Grinder display
conversion (float <-> notation) runs at the same layer.

**Fields subject to unit conversion:**
- Brew: `dose` (g/oz), `yield_amount` (g/oz), `temperature` (C/F),
  `pressure` (bar/psi), `flow_rate` (ml/s, fl oz/s)
- Bag: `weight` (g/oz)
- Brewer: `temp_min`, `temp_max`, `temp_step` (C/F), `pressure_min`, `pressure_max`
  (bar/psi), `saturation_flow_rate` (ml/s, fl oz/s)
- WaterMineral: `ppm` — not converted (unit-agnostic).

Field names in responses are unit-agnostic (e.g. `weight`, `dose`, `temperature`).
The `?units` param controls the value, not the field name.

### 3.10 Response Format

```python
from pydantic import BaseModel

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

Uses `pydantic.BaseModel` (not `SQLModel`) since this is a pure response schema,
never persisted. SQLModel's metaclass has known issues with Generic types.
Fully typed — used as `PaginatedResponse[BeanRead]`, `PaginatedResponse[BrewRead]`,
etc. Shows up correctly in OpenAPI schema.

Single resources return the read schema directly. Dates in ISO 8601, all times UTC.

### 3.11 Soft-Delete Referential Integrity

When soft-deleting a lookup entity (Origin, FlavorTag, etc.) that is still
referenced by an active entity (e.g. a Bean still linked to that Origin):

- **The API prevents it.** DELETE returns 409 Conflict with a message listing the
  active references. The user must unlink the entity first, then retire it.
- Read schemas still include retired lookup entities if they remain linked (should
  not happen under this constraint, but defensive display).

When soft-deleting a **Person** who has non-retired Brews or BeanRatings:

- **Allowed.** The person is retired, but their brews/ratings remain visible.
  `GET /brews` with `include_retired=false` still returns brews from a retired
  person (the brew itself is not retired). The `PersonRead` nested in brew
  responses includes `is_retired: true` so the frontend can display appropriately.

---

## 4. Configuration

**`config.py`** — pydantic-settings:

```python
class Settings(BaseSettings):
    database_url: str = "sqlite:///beanbay.db"
    default_person_name: str = "Default"

    model_config = SettingsConfigDict(env_prefix="BEANBAY_")
```

Environment variables: `BEANBAY_DATABASE_URL`, `BEANBAY_DEFAULT_PERSON_NAME`.

**`database.py`** — engine + FastAPI DI:

- `create_engine(settings.database_url)` with SQLite-specific settings:
  `check_same_thread=False` and `PRAGMA journal_mode=WAL` (via event listener)
  for safe concurrent reads. SQLite is intended for single-user/home-network use;
  for multi-user production, configure `BEANBAY_DATABASE_URL` to point to PostgreSQL.
- `get_session()` generator yielded via `Depends()` in every router.

**Lifespan** — `main.py`:

- `@asynccontextmanager` lifespan on the FastAPI app.
- Alembic migrations run synchronously before the async event loop via
  `alembic.command.upgrade()` (not inside an async context, to avoid blocking
  the event loop). Alternatively, run via `asyncio.to_thread()`.
- Seeds brew methods + stop modes, ensures default person exists.
- Seeding is idempotent (upsert by name).

---

## 5. Cherry-Pick Strategy

Three pieces of battle-tested logic adapted from the main branch rather than
rewritten. Original author credited in commit messages.

| Source (main branch) | Target | Adaptation |
|---|---|---|
| `app/models/equipment.py` Grinder: `to_display`, `from_display`, `ring_sizes`, `linear_bounds` | `utils/grinder_display.py` | Extract as standalone functions taking ring config as input. Convert from SQLAlchemy Column types to plain Python args. |
| `app/utils/brewer_capabilities.py` `derive_tier()` | `utils/brewer_capabilities.py` | Nearly verbatim — takes a brewer object with capability attributes. |
| `app/models/equipment.py` capability enums | `models/equipment.py` | Convert to `StrEnum` classes for SQLModel/Pydantic validation. |
| `app/models/equipment.py` `stop_mode` (single str) | `brewer_stop_modes` junction | **Breaking change from main:** main has `stop_mode` as a single `Column(String)` on Brewer. The new design uses a M2M junction table. `derive_tier()` does not reference `stop_mode`, so it is unaffected. Any future optimizer code referencing `brewer.stop_mode` (singular) must be updated to query the M2M relationship. |

Git strategy: `git show main:<file>` into new structure, adapt, credit:
```
feat: add grinder display conversion utilities

Adapted from main branch grinder model (original author: grzonka).
Refactored from ORM methods to standalone functions for SQLModel compatibility.
```

---

## 6. Alembic Setup

- `alembic.ini` exists at project root (already present).
- `migrations/` directory at project root — recreate `env.py` targeting
  `SQLModel.metadata` (import all models from `beanbay.models`).
- Initial migration auto-generated from the full schema.
- Lifespan runs `alembic upgrade head` on startup.

---

## 7. Testing Strategy

**No mocks. Ever.** Real models, real DB, real sessions, real HTTP requests.

```
tests/
├── conftest.py                  # shared fixtures: engine (in-memory SQLite),
│                                #   session (transaction-scoped), client (TestClient
│                                #   with DI override for get_session)
├── unit/
│   ├── conftest.py              # unit-specific fixtures if needed
│   ├── test_grinder_display.py  # pure function tests (to_display, from_display)
│   ├── test_unit_conversion.py  # pint conversion helpers
│   ├── test_brewer_tier.py      # derive_tier() with real model instances
│   └── test_models.py           # model validation, soft-delete, constraints
├── integration/
│   ├── conftest.py              # integration-specific fixtures (test client + DI)
│   ├── test_beans_api.py        # full HTTP request/response against in-memory DB
│   ├── test_equipment_api.py
│   ├── test_brews_api.py
│   ├── test_ratings_api.py
│   ├── test_people_api.py
│   └── test_pagination.py       # pagination, filtering, autocomplete ?q=
```

**Rules:**
- Unit tests: test pure functions and model logic with real SQLModel instances +
  in-memory SQLite session.
- Integration tests: full `httpx.TestClient(app)` hitting real endpoints. DI override
  swaps `get_session` for in-memory SQLite session.
- Fixtures via pytest DI only — never `from conftest import`. Shared fixtures in
  root `conftest.py`, extracted when used across multiple test files.
- Separate `unit/` and `integration/` directories.
- Existing dev dependencies: `pytest`, `pytest-asyncio`, `httpx`.

---

## 8. Dependencies

Current `pyproject.toml` dependencies (add `pint`):

```toml
dependencies = [
    "alembic>=1.18.4",
    "fastapi[standard]>=0.115",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.0",
    "sqlmodel>=0.0.37",
    "pint>=0.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]
```

Build system: hatchling + setuptools_scm (already configured).
Package manager: uv (per project conventions).

---

## 9. Design Decisions Log

| Decision | Rationale |
|---|---|
| UUID4 primary keys | Consistency with old codebase; no downsides at home-network scale |
| Soft delete via `retired_at` only | No redundant `is_retired` column; derived in read schemas |
| Separate BrewTaste/BeanTaste tables | Separates objective brew data from subjective assessment |
| Taste fields duplicated (not shared table) | Independent evolution; no coupling; fully typed |
| Shared FlavorTag table | Autocomplete/dedup across brew and bean taste tags |
| Lookup tables for Origin/Roaster/Process/Variety | Prevent typo-drift, enable autocomplete |
| Bean variety as M2M | Blends combine varieties (e.g. arabica + robusta) |
| Bean process as M2M | Blends can combine processes (e.g. washed + natural lots) |
| Bean origin as M2M | Blends can have multiple origins |
| Roaster as single FK | A bean comes from one roaster |
| Bag separate from Bean | "What coffee" vs "when/how much I bought" |
| Brew links to Bag (not Bean) | Track which specific purchase was used |
| Bag.is_preground | Same bean can be bought whole or preground |
| Person table with default | Consistent identity without auth; single-user convenience |
| BeanRating append-only | Track taste perception over time; latest by rated_at is current |
| Grinder canonical float | Internal numeric value; display conversion at API boundary |
| Grinder rings exposed as structured data | Frontend builds dynamic input widget (per-ring inputs + slider) entirely from API data |
| Brew exposes both grind_setting + grind_setting_display | Float for slider/BayBE, display string for human-readable notation |
| Brewer capabilities flat (not normalized) | Single-query access for BayBE; 1:1 configs don't warrant separate tables |
| Brewer tier computed (not stored) | Derived from capability flags; used for UI complexity and BayBE parameter selection |
| Brewer full capability model | Ready for BayBE integration later |
| Brewer stop_modes as M2M | Brewers support multiple stop modes |
| Canonical units in DB | grams/celsius/seconds/ml; pint converts at API boundary |
| No mocks in tests | Real DB, real requests; design for testability instead |
| Cherry-pick from main | Reuse battle-tested grinder/brewer logic; credit original author |
| SQLModel Base/Create/Update/Read pattern | Canonical pattern per SQLModel docs; DRY via inheritance |
| FastAPI DI for sessions | `Depends(get_session)`; easily overridden in tests |
| Lifespan for setup | Migrations + seeding on startup |
| SQLite WAL mode | Safe concurrent reads for home-network use |
| Alembic runs before async event loop | Avoids blocking the event loop with sync DB operations |
| `retired_at` only (no `is_retired` column) | Computed property; single source of truth |
| `datetime.now(UTC)` or DB-side `server_default` | `datetime.utcnow` deprecated in Python 3.12+ |
| Lookup soft-delete blocked if referenced | 409 Conflict prevents orphaned references |
| Person soft-delete allowed with active brews | Brews stay visible; person marked retired |
| BeanRating append-only (no PATCH) | New rating = new row; DELETE for erroneous entries |
| Water minerals delete-and-reinsert | Simple; no partial mineral updates needed |
| `sort_by` validated against allowlist | Prevents SQL injection via column name |
| `PaginatedResponse` uses `pydantic.BaseModel` | SQLModel metaclass has issues with Generic types |
| Bag field named `weight` (not `size_grams`) | Unit-agnostic naming; `?units` controls the value |
| `Bag.price` has no currency | Always user's local currency; no conversion needed |
| Brew has pressure + flow_rate fields | Nullable; needed for BayBE optimization on Tier 4-5 brewers |
| Brew has stop_mode_id | Records which stop mode was used; BayBE covariate |
| BrewTaste.score is the BayBE objective | Overall assessment; sub-dimensions are informational |
| Top-level `GET /bags` endpoint | Enables pantry view and bag picker without N+1 |
| No latest_score on BeanRead list | Per-user context needed; detail view shows per-person ratings |
| Explicit person_id filter (no implicit default) | No person_id = all people; avoids hidden behavior |
| BrewListRead vs BrewRead schemas | List includes summary nesting; detail includes full nesting |
| AND-composed brew filters support BayBE campaigns | `?brew_setup_id=X&bean_id=Y` across all bags |
| Stats/dashboard endpoint deferred | Frontend computes from raw data initially; add when needed |
| No inline lookup creation on BeanCreate | Frontend uses separate POST to create new lookups; simpler API |

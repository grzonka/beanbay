# Phase 13: Data Model Evolution & Bean Metadata - Research

**Researched:** 2026-02-22
**Domain:** SQLAlchemy data modeling, Alembic migrations, FastAPI form handling
**Confidence:** HIGH

## Summary

This phase extends BeanBay's data model to support equipment, brew methods, brew setups, and enhanced bean metadata. The existing codebase has a clean, minimal schema with 2 models (Bean, Measurement) and 4 Alembic migrations. The architecture is well-established with clear patterns for adding models, writing migrations, creating routes, and testing.

The primary challenge is the data migration for existing measurements — they need to be associated with a default "espresso" brew setup without breaking existing data or BayBE campaign state. The Measurement model currently links directly to Bean; this phase adds an intermediate BrewSetup layer. All new fields on Bean (roast_date, process, variety) are optional, so backwards compatibility is straightforward.

**Primary recommendation:** Build schema-first in a single Alembic migration with careful data migration for existing measurements. Keep new FK columns nullable initially, populate with defaults via migration, then add NOT NULL constraints if desired.

## Current Codebase Structure

### Project Layout (relevant files)
```
app/
├── __init__.py
├── config.py              # Settings with data_dir, database_url
├── database.py            # Engine, SessionLocal, Base, get_db
├── main.py                # FastAPI app, lifespan, router registration
├── models/
│   ├── __init__.py        # Exports Bean, Measurement
│   ├── bean.py            # Bean model (23 lines)
│   └── measurement.py     # Measurement model (42 lines)
├── routers/
│   ├── __init__.py
│   ├── beans.py           # Bean CRUD, activate, parameter overrides (290 lines)
│   ├── brew.py            # Recommend/record/best/manual loop (421 lines)
│   ├── history.py         # Shot history list, detail, edit, batch delete (343 lines)
│   ├── insights.py        # Optimization progress & convergence (231 lines)
│   └── analytics.py       # Aggregate stats, cross-bean comparison (149 lines)
├── services/
│   └── optimizer.py       # BayBE OptimizerService (360 lines)
├── templates/
│   ├── base.html
│   ├── beans/
│   │   ├── list.html      # Bean list with create form
│   │   ├── detail.html    # Bean detail: edit, custom ranges, danger zone
│   │   ├── _bean_card.html
│   │   └── _active_indicator.html
│   ├── brew/...
│   └── history/...
└── static/
    ├── css/
    └── js/

migrations/
├── env.py                 # render_as_batch=True for SQLite
└── versions/
    ├── 87c4e18a3be4_initial_schema.py
    ├── a2f1c3d5e7b9_add_parameter_overrides_to_beans.py
    ├── e192b884d9c6_add_flavor_tags_to_measurements.py
    └── c06d948aa2d7_add_is_manual_to_measurements.py   ← HEAD

tests/
├── conftest.py            # db_session, client, optimizer_service fixtures
├── test_models.py         # 8 model-level tests
├── test_beans.py          # 16 bean CRUD tests
├── test_brew.py           # 25+ brew route tests
├── test_history.py        # 19 history route tests
├── test_insights.py       # insights route tests
├── test_analytics.py      # analytics route tests
└── test_optimizer.py      # BayBE integration tests (marked slow)
```

### Current Models (Exact)

**Bean Model** (`app/models/bean.py`):
```python
class Bean(Base):
    __tablename__ = "beans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    roaster = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    parameter_overrides = Column(JSON, nullable=True, default=None)
    
    measurements = relationship("Measurement", back_populates="bean", cascade="all, delete-orphan")
```

**Measurement Model** (`app/models/measurement.py`):
```python
class Measurement(Base):
    __tablename__ = "measurements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    bean_id = Column(String, ForeignKey("beans.id"), nullable=False, index=True)
    recommendation_id = Column(String, nullable=True, unique=True)
    
    # BayBE parameters (6 recipe params)
    grind_setting = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    preinfusion_pct = Column(Float, nullable=False)
    dose_in = Column(Float, nullable=False)
    target_yield = Column(Float, nullable=False)
    saturation = Column(String, nullable=False)
    
    # Target
    taste = Column(Float, nullable=False)
    
    # Metadata
    extraction_time = Column(Float, nullable=True)
    is_failed = Column(Boolean, default=False)
    is_manual = Column(Boolean, nullable=True, default=False)
    notes = Column(String, nullable=True)
    
    # Flavor profile
    acidity = Column(Float, nullable=True)
    sweetness = Column(Float, nullable=True)
    body = Column(Float, nullable=True)
    bitterness = Column(Float, nullable=True)
    aroma = Column(Float, nullable=True)
    intensity = Column(Float, nullable=True)
    flavor_tags = Column(String, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    bean = relationship("Bean", back_populates="measurements")
```

### Current Alembic Setup

- **4 migrations** in linear chain: `87c4e18a3be4` → `a2f1c3d5e7b9` → `e192b884d9c6` → `c06d948aa2d7` (HEAD)
- **SQLite-specific:** `render_as_batch=True` in `migrations/env.py` (required for SQLite ALTER TABLE)
- **Pattern:** Each migration uses `batch_alter_table` for column additions on existing tables
- **Convention:** Uses autogenerated revision IDs, descriptive message slugs
- **env.py imports `app.models`** to detect model changes for autogenerate
- **`Base.metadata.create_all()`** also runs in `app/main.py` lifespan as a safety net

### Current Bean Detail Page (`app/templates/beans/detail.html`)

Three sections:
1. **Bean info form** — name, roaster, origin fields with "Save Changes" button
2. **Parameter overrides** — collapsible section with custom range inputs
3. **Danger zone** — collapsible section with delete button

Template uses `{{ bean.xxx }}` dict-style access from `_bean_with_shot_count()` which returns a dict (not the ORM object).

### Current Bean Create/Edit Flow

**Create** (`POST /beans`): Accepts `name`, `roaster`, `origin` via `Form()` parameters.  
**Update** (`POST /beans/{bean_id}`): Same fields, same pattern.  
Both are in `app/routers/beans.py`.

The create form is in `beans/list.html`, the edit form is in `beans/detail.html`.

### How `_bean_with_shot_count()` Works

```python
def _bean_with_shot_count(db: Session, bean: Bean) -> dict:
    count = db.query(func.count(Measurement.id)).filter(Measurement.bean_id == bean.id).scalar()
    return {
        "id": bean.id,
        "name": bean.name,
        "roaster": bean.roaster,
        "origin": bean.origin,
        "created_at": bean.created_at,
        "parameter_overrides": bean.parameter_overrides,
        "shot_count": count or 0,
    }
```

This function MUST be updated to include new Bean fields when they are added.

### Test Patterns

- **conftest.py**: Sets `BEANBAY_DATABASE_URL=sqlite:///:memory:`, creates tables with `Base.metadata.create_all()`, uses function-scoped sessions with rollback
- **Model tests** (`test_models.py`): Direct ORM operations, flush, assert fields
- **Route tests** (`test_beans.py`, `test_brew.py`, etc.): Use `TestClient`, post form data, check response status/content
- **Fixture pattern**: Each test file has its own `sample_bean` fixture
- **NO Alembic in tests**: Tests use `Base.metadata.create_all()`, NOT Alembic migrations. New models just need to be registered with Base (imported in `app/models/__init__.py`)

## Architecture Patterns

### Pattern 1: Adding a New Model

Based on how Bean and Measurement were created:

1. Create model file in `app/models/` (e.g., `app/models/brew_setup.py`)
2. Import and export in `app/models/__init__.py`
3. Ensure `migrations/env.py` picks it up (it already imports `app.models`)
4. Generate migration with `alembic revision --autogenerate -m "message"`
5. Tests will work automatically since `conftest.py` does `Base.metadata.create_all()`

### Pattern 2: Adding Columns to Existing Model

Based on parameter_overrides, flavor_tags, is_manual additions:

1. Add column to model class
2. Create migration with `batch_alter_table` (required for SQLite)
3. Update any dict-building functions (like `_bean_with_shot_count`)
4. Update templates to show new fields
5. Update route handlers to accept new form data

### Pattern 3: UUID Primary Keys

Bean uses `String` PK with `default=lambda: str(uuid.uuid4())`. New entity models should follow this same pattern for consistency.

### Pattern 4: Relationship Conventions

- Use `back_populates` (not `backref`)
- Cascade: `"all, delete-orphan"` on the parent side
- FK column type matches parent PK type (String for UUID)

### Anti-Patterns to Avoid
- **Don't use Integer PKs for domain entities** — Bean uses UUID String, follow this convention for new models (Grinder, Brewer, etc.) for consistency. (Measurement uses Integer autoincrement — it's a transaction record, not an entity.)
- **Don't skip `batch_alter_table`** — SQLite requires it for ALTER TABLE operations
- **Don't add NOT NULL columns without defaults on existing tables** — will fail on tables with existing data

## Recommended Schema Design

### New Models

```
BrewMethod
├── id (String, UUID PK)
├── name (String, NOT NULL, UNIQUE)  # "espresso", "v60", "aeropress", etc.
├── created_at (DateTime)

Grinder
├── id (String, UUID PK)
├── name (String, NOT NULL)  # "Niche Zero", "Comandante C40"
├── created_at (DateTime)

Brewer
├── id (String, UUID PK)
├── name (String, NOT NULL)  # "Decent DE1", "Hario V60"
├── created_at (DateTime)

Paper
├── id (String, UUID PK)
├── name (String, NOT NULL)  # "Decent stock", "Hario tabbed"
├── created_at (DateTime)

WaterRecipe
├── id (String, UUID PK)
├── name (String, NOT NULL)  # "Third Wave Water", "RPavlis"
├── recipe_details (String, nullable)  # freeform text for recipe specifics
├── created_at (DateTime)

BrewSetup
├── id (String, UUID PK)
├── name (String, nullable)  # optional user label
├── brew_method_id (FK → brew_methods.id, NOT NULL)
├── grinder_id (FK → grinders.id, nullable)
├── brewer_id (FK → brewers.id, nullable)
├── paper_id (FK → papers.id, nullable)
├── water_recipe_id (FK → water_recipes.id, nullable)
├── created_at (DateTime)
# Relationships to all equipment + method

Bag
├── id (String, UUID PK)
├── bean_id (FK → beans.id, NOT NULL)
├── purchase_date (Date, nullable)
├── cost (Float, nullable)  # META-03: optional cost per bag
├── weight_grams (Float, nullable)
├── notes (String, nullable)
├── created_at (DateTime)
```

### Extended Bean Model

Add to existing Bean:
```python
roast_date = Column(Date, nullable=True)      # META-01
process = Column(String, nullable=True)         # META-01: "washed", "natural", "honey", "anaerobic", "other"
variety = Column(String, nullable=True)          # META-01: freeform text

bags = relationship("Bag", back_populates="bean", cascade="all, delete-orphan")
```

### Extended Measurement Model

Add to existing Measurement:
```python
brew_setup_id = Column(String, ForeignKey("brew_setups.id"), nullable=True, index=True)

brew_setup = relationship("BrewSetup")
```

**CRITICAL:** `brew_setup_id` must be nullable because:
1. Existing measurements have no brew setup
2. The data migration creates a default setup and associates them
3. Making it NOT NULL would require all this in a single transaction

## Data Migration Strategy

### The Challenge

Existing measurements (possibly 0 or many) need to be associated with a default espresso brew setup. This requires:
1. Creating the `brew_methods` table
2. Inserting a default "Espresso" brew method row
3. Creating the `brew_setups` table  
4. Inserting a default brew setup pointing to the espresso method
5. Updating all existing measurements to point to this default setup

### Recommended Approach: Single Migration with Data Operations

```python
def upgrade():
    # 1. Create all new tables (brew_methods, grinders, brewers, papers, water_recipes, brew_setups, bags)
    # 2. Add new columns to beans (roast_date, process, variety)
    # 3. Add brew_setup_id column to measurements (nullable)
    # 4. Data migration:
    #    - INSERT default espresso method into brew_methods
    #    - INSERT default brew setup into brew_setups
    #    - UPDATE measurements SET brew_setup_id = default_setup_id
```

Use `op.execute()` for the data migration SQL:
```python
import uuid

default_method_id = str(uuid.uuid4())
default_setup_id = str(uuid.uuid4())

# Insert default brew method
op.execute(
    f"INSERT INTO brew_methods (id, name) VALUES ('{default_method_id}', 'Espresso')"
)

# Insert default brew setup
op.execute(
    f"INSERT INTO brew_setups (id, brew_method_id) VALUES ('{default_setup_id}', '{default_method_id}')"
)

# Link all existing measurements to the default setup
op.execute(
    f"UPDATE measurements SET brew_setup_id = '{default_setup_id}'"
)
```

**Important:** Generate deterministic UUIDs (or hardcode them) so the migration is idempotent and the downgrade can reference the same IDs.

## Files That Will Need Modification

### New Files to Create
| File | Purpose |
|------|---------|
| `app/models/brew_method.py` | BrewMethod model |
| `app/models/equipment.py` | Grinder, Brewer, Paper, WaterRecipe models (grouped) |
| `app/models/brew_setup.py` | BrewSetup model |
| `app/models/bag.py` | Bag model |
| `migrations/versions/xxx_add_equipment_and_bean_metadata.py` | Single migration for all schema changes |

### Existing Files to Modify
| File | Changes |
|------|---------|
| `app/models/__init__.py` | Export all new models |
| `app/models/bean.py` | Add roast_date, process, variety columns + bags relationship |
| `app/models/measurement.py` | Add brew_setup_id FK + brew_setup relationship |
| `app/routers/beans.py` | Update create/edit to handle new bean fields; add bag routes; update `_bean_with_shot_count()` |
| `app/templates/beans/detail.html` | Add metadata section (process, variety, roast_date) + bag management section |
| `app/templates/beans/list.html` | Update create form with optional new fields |
| `app/templates/beans/_bean_card.html` | Optionally show process/roast_date |
| `tests/test_models.py` | Add tests for new models and extended Bean/Measurement |
| `tests/test_beans.py` | Add tests for new bean fields and bag management |

### Files That May Need Minor Updates
| File | Why |
|------|-----|
| `app/routers/history.py` | `_build_shot_dicts` and `_load_shot_detail` might show brew setup info |
| `app/routers/analytics.py` | `_compute_comparison` might show setup info |
| `tests/conftest.py` | If new fixtures needed for equipment/setup |

### Files That Should NOT Change (This Phase)
| File | Reason |
|------|--------|
| `app/services/optimizer.py` | BayBE campaigns don't reference BrewSetup; recipe params stay on Measurement |
| `app/routers/brew.py` | Brew loop still works with existing params; BrewSetup selection is a future phase |
| `app/routers/insights.py` | Optimization insights don't depend on setup context |

## Common Pitfalls

### Pitfall 1: SQLite ALTER TABLE Limitations
**What goes wrong:** SQLite doesn't support most ALTER TABLE operations (e.g., adding FK constraints, changing column types)
**Why it happens:** Alembic defaults to standard SQL ALTER
**How to avoid:** Always use `render_as_batch=True` (already configured in env.py) and `batch_alter_table` in migrations
**Warning signs:** Migration errors about "unsupported" ALTER operations

### Pitfall 2: NOT NULL Columns on Existing Tables With Data
**What goes wrong:** `ALTER TABLE ADD COLUMN ... NOT NULL` fails if table has existing rows
**Why it happens:** SQLite requires a default for NOT NULL columns added to populated tables
**How to avoid:** Either make new columns nullable, OR provide a `server_default` value
**Warning signs:** "Cannot add a NOT NULL column with default value NULL" error

### Pitfall 3: Foreign Key Enforcement in SQLite
**What goes wrong:** SQLite doesn't enforce foreign keys by default
**Why it happens:** FK enforcement requires `PRAGMA foreign_keys = ON` at each connection
**How to avoid:** For this project, FK enforcement is not explicitly enabled (no `event.listen` on connect). This means:
- FKs are decorative (they express intent but aren't enforced)
- Dangling references won't cause immediate errors
- This is acceptable for a single-user app
**Warning signs:** Data integrity issues with orphaned records

### Pitfall 4: `_bean_with_shot_count()` Returns Dict Not ORM Object
**What goes wrong:** Template uses `bean.xxx` but `xxx` doesn't exist in the dict
**Why it happens:** `_bean_with_shot_count()` builds a plain dict, so new Bean columns need to be explicitly added
**How to avoid:** Always update this function when adding Bean columns. Consider adding a helper or using the ORM object directly with an annotated `shot_count`.
**Warning signs:** Template KeyError or missing data on bean detail page

### Pitfall 5: Data Migration UUIDs Must Be Deterministic
**What goes wrong:** Random UUIDs in migration make downgrade unreliable
**Why it happens:** `uuid.uuid4()` generates different values each run
**How to avoid:** Use hardcoded UUIDs in the migration (e.g., `"00000000-0000-0000-0000-000000000001"`) for seed data
**Warning signs:** Downgrade can't find the records to delete

### Pitfall 6: BayBE Campaign Impact
**What goes wrong:** Measurement model changes might break campaign rebuild
**Why it happens:** `rebuild_campaign` in history.py reads Measurement ORM objects and extracts BAYBE_PARAM_COLUMNS + taste
**How to avoid:** The brew_setup_id is additive and nullable. BAYBE_PARAM_COLUMNS are unchanged. The optimizer only reads grind_setting, temperature, preinfusion_pct, dose_in, target_yield, saturation, taste — none of which change. **No campaign impact.**
**Warning signs:** None expected — this is safe

### Pitfall 7: Circular Import with Multiple Model Files
**What goes wrong:** Models referencing each other cause import errors
**Why it happens:** File A imports from File B which imports from File A
**How to avoid:** Use string references in relationships: `relationship("ModelName")` not direct class references. SQLAlchemy resolves strings at runtime.
**Warning signs:** ImportError at startup

## Code Examples

### Example 1: New Model File Pattern (Following Existing Convention)

```python
# app/models/brew_method.py
import uuid

from sqlalchemy import Column, DateTime, String, func

from app.database import Base


class BrewMethod(Base):
    __tablename__ = "brew_methods"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, server_default=func.now())
```

### Example 2: BrewSetup with Multiple FKs

```python
# app/models/brew_setup.py
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class BrewSetup(Base):
    __tablename__ = "brew_setups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    brew_method_id = Column(String, ForeignKey("brew_methods.id"), nullable=False)
    grinder_id = Column(String, ForeignKey("grinders.id"), nullable=True)
    brewer_id = Column(String, ForeignKey("brewers.id"), nullable=True)
    paper_id = Column(String, ForeignKey("papers.id"), nullable=True)
    water_recipe_id = Column(String, ForeignKey("water_recipes.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    brew_method = relationship("BrewMethod")
    grinder = relationship("Grinder")
    brewer = relationship("Brewer")
    paper = relationship("Paper")
    water_recipe = relationship("WaterRecipe")
```

### Example 3: Bag Model with Bean FK

```python
# app/models/bag.py
import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Bag(Base):
    __tablename__ = "bags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    bean_id = Column(String, ForeignKey("beans.id"), nullable=False, index=True)
    purchase_date = Column(Date, nullable=True)
    cost = Column(Float, nullable=True)
    weight_grams = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    bean = relationship("Bean", back_populates="bags")
```

### Example 4: Migration with Data Migration

```python
def upgrade():
    # Create new tables
    op.create_table('brew_methods',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # ... other tables ...
    
    # Add columns to existing tables
    with op.batch_alter_table('beans') as batch_op:
        batch_op.add_column(sa.Column('roast_date', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('process', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('variety', sa.String(), nullable=True))
    
    with op.batch_alter_table('measurements') as batch_op:
        batch_op.add_column(sa.Column('brew_setup_id', sa.String(), nullable=True))
    
    # Data migration: seed defaults
    DEFAULT_METHOD_ID = "00000000-0000-0000-0000-000000000001"
    DEFAULT_SETUP_ID = "00000000-0000-0000-0000-000000000002"
    
    op.execute(
        f"INSERT INTO brew_methods (id, name) VALUES ('{DEFAULT_METHOD_ID}', 'Espresso')"
    )
    op.execute(
        f"INSERT INTO brew_setups (id, brew_method_id) VALUES ('{DEFAULT_SETUP_ID}', '{DEFAULT_METHOD_ID}')"
    )
    op.execute(
        f"UPDATE measurements SET brew_setup_id = '{DEFAULT_SETUP_ID}'"
    )
```

### Example 5: Bean Detail Template Extension

```html
<!-- Enhanced metadata section (new, before Parameter Overrides) -->
<div class="card mb-md">
  <h3 class="card-title">Coffee Details</h3>
  <form method="post" action="/beans/{{ bean.id }}">
    <!-- existing name, roaster, origin fields -->
    <div class="form-group">
      <label class="form-label" for="roast_date">Roast Date</label>
      <input type="date" id="roast_date" name="roast_date" class="form-input"
             value="{{ bean.roast_date or '' }}">
    </div>
    <div class="form-group">
      <label class="form-label" for="process">Process</label>
      <select id="process" name="process" class="form-input">
        <option value="">—</option>
        <option value="washed" {% if bean.process == 'washed' %}selected{% endif %}>Washed</option>
        <option value="natural" {% if bean.process == 'natural' %}selected{% endif %}>Natural</option>
        <option value="honey" {% if bean.process == 'honey' %}selected{% endif %}>Honey</option>
        <option value="anaerobic" {% if bean.process == 'anaerobic' %}selected{% endif %}>Anaerobic</option>
        <option value="other" {% if bean.process == 'other' %}selected{% endif %}>Other</option>
      </select>
    </div>
    <div class="form-group">
      <label class="form-label" for="variety">Variety</label>
      <input type="text" id="variety" name="variety" class="form-input"
             value="{{ bean.variety or '' }}" placeholder="e.g. SL-28, Gesha">
    </div>
    <button type="submit" class="btn btn-secondary btn-full">Save Changes</button>
  </form>
</div>
```

### Example 6: Update Route to Handle New Fields

```python
@router.post("/{bean_id}", response_class=HTMLResponse)
async def update_bean(
    request: Request,
    bean_id: str,
    name: str = Form(...),
    roaster: str = Form(""),
    origin: str = Form(""),
    roast_date: str = Form(""),    # new
    process: str = Form(""),        # new
    variety: str = Form(""),        # new
    db: Session = Depends(get_db),
):
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)

    bean.name = name.strip()
    bean.roaster = roaster.strip() or None
    bean.origin = origin.strip() or None
    bean.roast_date = datetime.strptime(roast_date, "%Y-%m-%d").date() if roast_date.strip() else None
    bean.process = process.strip() or None
    bean.variety = variety.strip() or None
    db.commit()
    
    return RedirectResponse(url=f"/beans/{bean_id}", status_code=303)
```

### Example 7: Bag Management Routes

```python
@router.post("/{bean_id}/bags", response_class=HTMLResponse)
async def add_bag(
    request: Request,
    bean_id: str,
    purchase_date: str = Form(""),
    cost: Optional[float] = Form(None),
    weight_grams: Optional[float] = Form(None),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    bean = db.query(Bean).filter(Bean.id == bean_id).first()
    if not bean:
        return RedirectResponse(url="/beans", status_code=303)
    
    bag = Bag(
        bean_id=bean_id,
        purchase_date=datetime.strptime(purchase_date, "%Y-%m-%d").date() if purchase_date.strip() else None,
        cost=cost,
        weight_grams=weight_grams,
        notes=notes.strip() or None,
    )
    db.add(bag)
    db.commit()
    
    return RedirectResponse(url=f"/beans/{bean_id}", status_code=303)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing | Custom date parser | `datetime.strptime` / HTML `<input type="date">` | Browser handles date picker, standard format |
| UUID generation | Custom ID scheme | `uuid.uuid4()` (existing pattern) | Already used throughout codebase |
| Schema migration | Manual SQL scripts | Alembic `batch_alter_table` | Already set up, handles SQLite constraints |
| Form validation | Custom validator | FastAPI `Form()` with type hints | Already the established pattern |

## Risks and Mitigation

### Risk 1: Migration on Production Database With Data (MEDIUM)
**Risk:** Alembic migration could fail or corrupt data on a production DB with existing measurements
**Mitigation:** 
- Test migration against a copy of production DB before deploying
- Make all new FK columns nullable first
- Use `op.execute()` for data migration, not ORM (ORM may not match mid-migration schema)
- Include downgrade that reverses all changes

### Risk 2: Template Breakage from Dict Changes (LOW)
**Risk:** `_bean_with_shot_count()` returns a dict; templates access `bean.xxx`. If new fields are not added to the dict, templates will fail.
**Mitigation:** Update `_bean_with_shot_count()` when adding Bean columns. Consider using the ORM object directly with an annotated shot count attribute.

### Risk 3: Existing Test Fixtures Creating Beans Without New Fields (LOW)  
**Risk:** All new columns are nullable/optional, so existing fixtures won't break. But new tests need to cover the new fields.
**Mitigation:** Existing tests will pass unchanged. Add new tests for new fields.

### Risk 4: Measurement.brew_setup_id Makes Queries More Complex (LOW)
**Risk:** Queries that join Measurement to Bean might need to also join through BrewSetup
**Mitigation:** For this phase, brew_setup_id is informational. No existing queries need to change because they query by bean_id (not via setup). Future phases will add setup-aware queries.

### Risk 5: BayBE Campaign State (NEGLIGIBLE)
**Risk:** Adding brew_setup_id to Measurement could affect campaign operations
**Mitigation:** The optimizer only reads `BAYBE_PARAM_COLUMNS` (6 recipe params) + `taste`. These columns are unchanged. No campaign rebuild needed for schema changes.

## Task Decomposition Recommendation

### Task 1: New Model Files + Extended Bean/Measurement Models
- Create model files for BrewMethod, Grinder, Brewer, Paper, WaterRecipe, BrewSetup, Bag
- Extend Bean with roast_date, process, variety, bags relationship
- Extend Measurement with brew_setup_id, brew_setup relationship
- Update `app/models/__init__.py`
- Write model tests

### Task 2: Alembic Migration
- Single migration creating all tables, adding all columns, seeding default data
- Data migration: link existing measurements to default espresso setup
- Test migration runs cleanly (forward and backward)

### Task 3: Bean Create/Edit with Enhanced Metadata
- Update bean create form (list.html) with optional roast_date, process, variety
- Update bean edit form (detail.html) with same fields
- Update `create_bean()` and `update_bean()` routes
- Update `_bean_with_shot_count()` dict
- Tests for new fields in create/edit

### Task 4: Bag Management on Bean Detail Page
- Add bag section to bean detail template
- Add bag CRUD routes (at minimum: add bag, list bags)
- Tests for bag operations

### Task 5: Bean Detail Page UI Enhancement
- Display enhanced metadata (process, variety, roast_date)
- Display bags with cost info
- Visual refinements (UI-03)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `declarative_base()` | `DeclarativeBase` class | SQLAlchemy 2.0 | Project uses old-style `declarative_base()` — fine, fully supported |
| `Column()` | `mapped_column()` | SQLAlchemy 2.0 | Project uses `Column()` — fine, keep consistency |

**Note:** The project uses SQLAlchemy 1.x-style ORM declarations (`Column`, `declarative_base`). This is fully supported in SQLAlchemy 2.x. For consistency, new models should follow the SAME style, not switch to `mapped_column()`.

## Open Questions

1. **Should brew_setup_id on Measurement eventually become NOT NULL?**
   - What we know: It must start nullable for the migration. After data migration, all measurements will have a value.
   - What's unclear: Whether to add a second migration later to make it NOT NULL
   - Recommendation: Keep nullable for now. A future phase can tighten the constraint when BrewSetup selection is integrated into the brew flow.

2. **How granular should equipment models be?**
   - What we know: Requirements say Grinder, Brewer, Paper, WaterRecipe as separate entities
   - What's unclear: Whether each needs its own file or they can share
   - Recommendation: Group related simple models (Grinder, Brewer, Paper) in a single `equipment.py` file. WaterRecipe gets its own file if it has recipe_details. BrewMethod and BrewSetup get their own files.

3. **Process field: enum or freeform?**
   - What we know: META-01 lists specific values: "washed, natural, honey, anaerobic, other"
   - What's unclear: Whether to use a database enum/check constraint or just a String with UI validation
   - Recommendation: Use `String` column with UI-level validation (HTML `<select>`). Don't use database-level enum — it's hard to change in SQLite. The "other" option covers edge cases.

## Sources

### Primary (HIGH confidence)
- **Codebase analysis** — All models, migrations, routers, templates, and tests read directly
- **SQLAlchemy docs** — `Column`, `relationship`, `ForeignKey` patterns match established codebase conventions
- **Alembic docs** — `batch_alter_table` and `op.execute()` for SQLite migrations

### Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries needed; all patterns exist in codebase
- Architecture: HIGH — follows established model/migration/route/test patterns exactly
- Pitfalls: HIGH — based on direct codebase analysis and SQLite-specific constraints
- Data migration: MEDIUM — data migration with `op.execute()` is standard but needs careful testing with real data

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable codebase, no external dependency changes expected)

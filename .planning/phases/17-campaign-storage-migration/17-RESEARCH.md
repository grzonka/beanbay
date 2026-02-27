# Phase 17: Campaign Storage Migration - Research

**Researched:** 2026-02-24
**Domain:** Internal codebase refactoring — moving file-based persistence to SQLite
**Confidence:** HIGH (all findings based on direct codebase analysis, no external library unknowns)

## Summary

This phase migrates BayBE campaign JSON files and pending recommendations from filesystem storage to SQLite tables. The current codebase stores campaign state in `data/campaigns/{key}.json`, bounds fingerprints in `.bounds` files, transfer metadata in `.transfer` files, and pending recommendations in a single `data/pending_recommendations.json` file. All of these move into the existing `data/beanbay.db` SQLite database.

The migration is straightforward because the project already uses SQLAlchemy with SQLite, has established model patterns (8 existing models), and doesn't use Alembic — it relies on `Base.metadata.create_all()` for table creation. The campaign JSON is an opaque blob (BayBE's internal serialization format) that needs no schema decomposition, making `Text` storage appropriate. The in-memory cache pattern in OptimizerService must be preserved because BayBE deserialization is expensive.

**Primary recommendation:** Refactor OptimizerService to accept a `SessionLocal` factory instead of a `Path`, add two new SQLAlchemy models (`CampaignState`, `PendingRecommendation`), implement a one-time startup migration that reads existing files into the DB, and update the brew router's pending recommendation helpers to use DB operations.

## Current State Analysis

### Campaign Storage (File-Based)

**Files involved:**
- `app/services/optimizer.py` — `OptimizerService` class (555 lines)
- Campaign files: `data/campaigns/{campaign_key}.json` (BayBE serialized JSON)
- Fingerprint files: `data/campaigns/{campaign_key}.bounds` (16-char hex string)
- Transfer metadata files: `data/campaigns/{campaign_key}.transfer` (JSON dict)

**Current production data (verified):**
- 12 campaign JSON files (11 with `.bounds` companion files)
- Sizes range from 5.4KB to 19.9MB (one legacy discrete-grid campaign is 19MB)
- Most hybrid campaigns are 5-9KB
- All bounds fingerprints are identical (`b0372653b5094fe0`) — all using default bounds
- 0 `.transfer` files currently exist (no transfer learning campaigns in production)
- Campaign key with special characters exists: `boo_no_waste_super_blend_(jan26)__espresso__none`

**OptimizerService architecture:**
```
__init__(campaigns_dir: Path)
├── _cache: dict[str, Campaign]      # In-memory BayBE objects (MUST keep)
├── _fingerprints: dict[str, str]    # Bounds fingerprints cache (MUST keep)
├── _lock: threading.Lock()          # Thread safety (MUST keep)
├── _campaign_path(key) → Path       # → REPLACE with DB read
├── _fingerprint_path(key) → Path    # → REPLACE with DB read
├── _save_campaign_unlocked(key)     # → REPLACE with DB write
├── get_or_create_campaign(key,...)  # → Update load/save calls
├── get_transfer_metadata(key)       # → REPLACE with DB read
├── migrate_legacy_campaigns()       # → REMOVE (legacy UUID→key migration already ran)
├── recommend(key, ...)              # → No changes needed (uses internal methods)
├── add_measurement(key, ...)        # → No changes needed
├── rebuild_campaign(key, ...)       # → No changes needed
└── get_recommendation_insights(...) # → No changes needed
```

**Key insight:** Only 5 methods directly touch the filesystem. The rest operate on the in-memory cache. The refactoring surface is small.

### Pending Recommendations Storage (File-Based)

**Files involved:**
- `app/routers/brew.py` — helper functions (lines 41-86)
- Single file: `data/pending_recommendations.json` (single JSON dict, all recs as values)

**Current production data (verified):**
- 56 pending recommendations accumulated (27.9KB file)
- Stale entries never cleaned up (recommendations that were never recorded)
- Structure: `{rec_id: {recommendation_id, grind_setting, temperature, ..., insights, method, setup_id, transfer_metadata}}`
- No campaign_key stored in pending recommendations (must be derived from method + setup_id + active bean)

**Code pattern:**
```python
# Three helper functions in brew.py:
_save_pending(data_dir, rec_id, rec)   # Write to single JSON file
_load_pending(data_dir, rec_id)         # Read from file
_remove_pending(data_dir, rec_id)       # Delete entry from file

# Also: app.state.pending_recommendations dict (in-memory, but only used for reads in show_recommendation)
```

**Race condition:** `_save_pending` and `_remove_pending` read-modify-write the entire file without locking. With SQLite, each row operation is atomic.

### Database Infrastructure (Existing)

**`app/database.py`:**
- `engine` — SQLAlchemy engine with `check_same_thread=False`
- `SessionLocal` — Session factory
- `Base` — declarative base (all models inherit from this)
- `get_db()` — FastAPI dependency yielding session

**No Alembic.** Tables created via `Base.metadata.create_all(bind=engine)` in `app/main.py` lifespan. New models just need to be imported before `create_all` runs. This is the established pattern — no need to introduce Alembic for this phase.

**Model conventions (from 8 existing models):**
- UUID string primary keys: `Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))`
- Integer autoincrement PKs: `Column(Integer, primary_key=True, autoincrement=True)`
- Timestamps: `Column(DateTime, server_default=func.now())`
- JSON data: `Column(JSON, nullable=True)` (used in Bean.parameter_overrides)
- Boolean defaults: `Column(Boolean, default=False)`
- Foreign keys with index: `Column(String, ForeignKey("table.id"), nullable=True, index=True)`

## Target Architecture

### New SQLAlchemy Models

#### CampaignState Model
```python
# app/models/campaign_state.py
import uuid
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from app.database import Base

class CampaignState(Base):
    __tablename__ = "campaign_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_key = Column(String, unique=True, nullable=False, index=True)
    campaign_json = Column(Text, nullable=False)        # BayBE Campaign.to_json()
    bounds_fingerprint = Column(String(16), nullable=True)  # 16-char hex
    transfer_metadata = Column(JSON, nullable=True)     # dict or None
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**Design decisions:**
- `Integer` PK (not UUID) — campaigns are internal, no external references needed, autoincrement is simpler
- `campaign_key` as unique indexed string — this is the logical key for lookups
- `campaign_json` as `Text` — campaign JSON is opaque blob, largest is 19MB but most are 5-9KB. SQLite handles Text up to 1GB. `Text` is preferable to `LargeBinary` because `Campaign.to_json()` returns a string and `Campaign.from_json()` takes a string — no encoding/decoding needed
- `bounds_fingerprint` as `String(16)` — short hex hash, nullable for campaigns created before fingerprinting
- `transfer_metadata` as `JSON` — SQLAlchemy's JSON type works with SQLite (stored as TEXT internally), matches `Bean.parameter_overrides` pattern already used in codebase
- `updated_at` with `onupdate` — tracks last persistence time, useful for debugging

#### PendingRecommendation Model
```python
# app/models/pending_recommendation.py
import uuid
from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.dialects.sqlite import JSON
from app.database import Base

class PendingRecommendation(Base):
    __tablename__ = "pending_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String, unique=True, nullable=False, index=True)
    recommendation_data = Column(JSON, nullable=False)  # Full rec dict
    created_at = Column(DateTime, server_default=func.now())
```

**Design decisions:**
- `recommendation_id` as unique indexed string (the UUID generated by OptimizerService.recommend)
- `recommendation_data` as `JSON` — the full recommendation dict including insights, method, setup_id, transfer_metadata. This is what `_load_pending` currently returns
- No `campaign_key` column — pending recs don't currently store it, and it's not needed for lookup (only `recommendation_id` is used)
- `created_at` for eventual stale cleanup (pending recs older than N days can be purged)

### Refactored OptimizerService

```python
class OptimizerService:
    """Thread-safe BayBE campaign manager with SQLite persistence."""

    def __init__(self, session_factory):
        self._session_factory = session_factory   # SessionLocal callable
        self._cache: dict[str, Campaign] = {}     # UNCHANGED
        self._fingerprints: dict[str, str] = {}   # UNCHANGED
        self._lock = threading.Lock()              # UNCHANGED

    def _load_campaign_from_db(self, campaign_key: str) -> tuple[str | None, str]:
        """Load campaign JSON and fingerprint from DB. Returns (json_str, fingerprint)."""
        with self._session_factory() as session:
            state = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
            if state:
                return state.campaign_json, state.bounds_fingerprint or ""
            return None, ""

    def _save_campaign_to_db(self, campaign_key: str) -> None:
        """Upsert campaign state to DB. Must be called with lock held."""
        campaign = self._cache[campaign_key]
        fp = self._fingerprints.get(campaign_key, "")
        json_str = campaign.to_json()
        with self._session_factory() as session:
            state = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
            if state:
                state.campaign_json = json_str
                state.bounds_fingerprint = fp
            else:
                state = CampaignState(
                    campaign_key=campaign_key,
                    campaign_json=json_str,
                    bounds_fingerprint=fp,
                )
                session.add(state)
            session.commit()
    
    # get_transfer_metadata reads from DB instead of .transfer file
    # _save_campaign_unlocked → renamed to _save_campaign_to_db
    # _campaign_path, _fingerprint_path → REMOVED
```

**Key architectural decision: OptimizerService manages its own sessions.**

The OptimizerService runs BayBE operations in `asyncio.to_thread()` and holds a threading lock across operations. It should NOT share sessions with FastAPI request handlers. Instead, it should create short-lived sessions from `SessionLocal` for its own DB operations. This avoids:
1. Session lifecycle mismatches (OptimizerService outlives any single request)
2. Thread-safety issues with sharing sessions across the lock boundary
3. Circular dependencies between router-level `get_db()` and service-level persistence

The `db` parameter currently passed to `get_or_create_campaign` for transfer learning lookup is a *separate concern* — it's the request's DB session used for querying beans/measurements, not for campaign persistence.

### Updated Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Initialize optimizer with DB session factory
    app.state.optimizer = OptimizerService(SessionLocal)

    # Run file→DB migration (idempotent, no-op after first run)
    migrated = migrate_campaigns_to_db(SessionLocal, settings.campaigns_dir)
    if migrated:
        logging.info("Migrated %d campaign(s) from files to DB", migrated)

    yield
```

## Migration Strategy

### Approach: Startup Migration Function (Idempotent)

```python
def migrate_campaigns_to_db(session_factory, campaigns_dir: Path) -> int:
    """One-time migration: read campaign files, insert into DB.
    
    Idempotent: skips campaigns already in DB (by campaign_key).
    Leaves original files in place as backup.
    """
    if not campaigns_dir.exists():
        return 0
    
    migrated = 0
    with session_factory() as session:
        for json_file in sorted(campaigns_dir.glob("*.json")):
            campaign_key = json_file.stem
            # Skip if already migrated
            exists = session.query(CampaignState).filter_by(
                campaign_key=campaign_key
            ).first()
            if exists:
                continue
            
            campaign_json = json_file.read_text()
            bounds_file = campaigns_dir / f"{campaign_key}.bounds"
            fingerprint = bounds_file.read_text().strip() if bounds_file.exists() else None
            transfer_file = campaigns_dir / f"{campaign_key}.transfer"
            transfer_meta = json.loads(transfer_file.read_text()) if transfer_file.exists() else None
            
            state = CampaignState(
                campaign_key=campaign_key,
                campaign_json=campaign_json,
                bounds_fingerprint=fingerprint,
                transfer_metadata=transfer_meta,
            )
            session.add(state)
            migrated += 1
        
        if migrated:
            session.commit()
    
    return migrated


def migrate_pending_to_db(session_factory, data_dir: Path) -> int:
    """One-time migration: read pending_recommendations.json, insert rows."""
    pending_file = data_dir / "pending_recommendations.json"
    if not pending_file.exists():
        return 0
    
    try:
        data = json.loads(pending_file.read_text())
    except (json.JSONDecodeError, OSError):
        return 0
    
    migrated = 0
    with session_factory() as session:
        for rec_id, rec_data in data.items():
            exists = session.query(PendingRecommendation).filter_by(
                recommendation_id=rec_id
            ).first()
            if exists:
                continue
            session.add(PendingRecommendation(
                recommendation_id=rec_id,
                recommendation_data=rec_data,
            ))
            migrated += 1
        if migrated:
            session.commit()
    
    return migrated
```

**Idempotency:** Check `campaign_key` / `recommendation_id` existence before insert. This handles partial migrations (crash during first run) and repeated startups.

**File retention:** Original files are left in place as backup. A future cleanup can remove them after confirming DB integrity. The `campaigns_dir` property in `Settings` should remain for migration compatibility but is no longer used by OptimizerService post-migration.

**Migration order:** Tables must exist (`create_all`) before migration runs. Migration runs before OptimizerService is used. This is already the startup order.

### Legacy Campaign Migration

The existing `migrate_legacy_campaigns()` method renames bare-UUID files to `{bean_id}__espresso__none` format. This should run BEFORE the file→DB migration during the transition period. After one successful startup, all files will be in new format AND in the DB.

Sequence:
1. `create_all` (creates new tables)
2. `migrate_legacy_campaigns()` (rename old filenames — existing code, keep for one more release)
3. `migrate_campaigns_to_db()` (files → DB rows)
4. `migrate_pending_to_db()` (file → DB rows)
5. OptimizerService initialized (now reads from DB)

### What Happens to campaigns_dir

- **Phase 17:** `settings.campaigns_dir` property remains. Migration reads from it. OptimizerService no longer writes to it.
- **Post-migration:** The `data/campaigns/` directory can be deleted manually by users after verifying DB integrity. No code depends on it anymore.
- **Future cleanup (optional):** Remove `campaigns_dir` property from Settings, remove file migration code after sufficient production time.

## Implementation Patterns

### OptimizerService Session Management

**Pattern: Session-per-operation with context manager**

```python
def _load_from_db(self, campaign_key: str):
    with self._session_factory() as session:
        row = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
        if row:
            return row.campaign_json, row.bounds_fingerprint or ""
        return None, ""

def _save_to_db(self, campaign_key: str):
    campaign = self._cache[campaign_key]
    fp = self._fingerprints.get(campaign_key, "")
    with self._session_factory() as session:
        row = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
        if row:
            row.campaign_json = campaign.to_json()
            row.bounds_fingerprint = fp
        else:
            session.add(CampaignState(
                campaign_key=campaign_key,
                campaign_json=campaign.to_json(),
                bounds_fingerprint=fp,
            ))
        session.commit()
```

**Why not `merge()`:** SQLAlchemy's `merge()` requires the object to be detached, which adds complexity. Simple query-then-update/insert is clearer and matches the existing codebase style.

**Why session-per-operation:** OptimizerService holds the threading lock across multiple operations (load, process, save). But the DB session should be as short-lived as possible. Open session, read, close. Process. Open session, write, close. This avoids holding DB connections while BayBE computes (3-10s for recommend).

### Thread Safety: Lock + Session Interaction

The existing `self._lock` (threading.Lock) protects the in-memory cache. DB operations happen within the lock but use their own sessions:

```python
with self._lock:
    # DB read (own session, opens and closes)
    json_str, fp = self._load_from_db(campaign_key)
    if json_str:
        self._cache[campaign_key] = Campaign.from_json(json_str)
        self._fingerprints[campaign_key] = fp
    else:
        # create fresh campaign
        self._cache[campaign_key] = self._create_fresh_campaign(...)
        self._fingerprints[campaign_key] = current_fp
        # DB write (own session, opens and closes)
        self._save_to_db(campaign_key)
```

This is safe because:
1. SQLite with `check_same_thread=False` handles concurrent connections
2. `SessionLocal` creates independent sessions
3. The threading lock prevents concurrent cache corruption
4. Short-lived sessions avoid holding DB locks during computation

### Transfer Metadata Storage

Currently stored in `.transfer` files. After migration, stored in `CampaignState.transfer_metadata` (JSON column):

```python
def get_transfer_metadata(self, campaign_key: str) -> dict | None:
    with self._session_factory() as session:
        state = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
        return state.transfer_metadata if state else None

# In get_or_create_campaign, when transfer learning creates a campaign:
def _save_transfer_metadata(self, campaign_key: str, metadata: dict):
    with self._session_factory() as session:
        state = session.query(CampaignState).filter_by(campaign_key=campaign_key).first()
        if state:
            state.transfer_metadata = metadata
            session.commit()
```

**Timing consideration:** Transfer metadata is written during campaign creation in `get_or_create_campaign`. The campaign itself is also saved in the same logical operation. These can share a single session or use the existing `_save_to_db` pattern with transfer_metadata added.

### Pending Recommendations: DB-Backed Helpers

Replace the three file-based helper functions in `brew.py`:

```python
# Before: _save_pending(data_dir, rec_id, rec)
# After:
def _save_pending(session: Session, rec_id: str, rec: dict) -> None:
    pending = PendingRecommendation(
        recommendation_id=rec_id,
        recommendation_data=rec,
    )
    session.merge(pending)  # merge handles insert-or-update
    session.commit()

# Before: _load_pending(data_dir, rec_id)
# After:
def _load_pending(session: Session, rec_id: str) -> dict | None:
    row = session.query(PendingRecommendation).filter_by(
        recommendation_id=rec_id
    ).first()
    return row.recommendation_data if row else None

# Before: _remove_pending(data_dir, rec_id)
# After:
def _remove_pending(session: Session, rec_id: str) -> None:
    session.query(PendingRecommendation).filter_by(
        recommendation_id=rec_id
    ).delete()
    session.commit()
```

**These functions use the request's DB session** (from `get_db()`), not the OptimizerService's session factory. This is correct because pending recommendations are managed in the router layer, not the optimizer layer.

**Cleanup of `app.state.pending_recommendations`:** The in-memory dict on `app.state` (used in `show_recommendation`) can be removed entirely. The DB query replaces it. This simplifies the code — no dual in-memory + file storage.

### Model Registration

Add to `app/models/__init__.py`:
```python
from app.models.campaign_state import CampaignState
from app.models.pending_recommendation import PendingRecommendation
```

This ensures `Base.metadata.create_all()` picks up the new tables.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB session management | Custom connection pool | `SessionLocal()` context manager | Already established pattern in codebase |
| JSON column type | Manual json.loads/dumps on Text | `Column(JSON)` | SQLAlchemy handles serialization, matches `Bean.parameter_overrides` pattern |
| Upsert logic | Custom REPLACE/INSERT OR REPLACE | Query-then-update pattern | Clearer intent, no SQLite-specific SQL, matches codebase style |
| Table creation | Alembic migrations | `Base.metadata.create_all()` | Existing pattern, no Alembic in project, `create_all` is idempotent |
| Campaign serialization | Custom JSON schema | `Campaign.to_json()` / `Campaign.from_json()` | BayBE provides round-trip serialization, treat as opaque blob |

## Common Pitfalls

### Pitfall 1: Breaking OptimizerService Constructor Signature
**What goes wrong:** Changing `__init__(campaigns_dir: Path)` to `__init__(session_factory)` breaks all tests and the lifespan code.
**Why it happens:** Tests create `OptimizerService(tmp_campaigns_dir)` in the fixture.
**How to avoid:** Update the `optimizer_service` fixture in `conftest.py` to pass a test session factory. Update `app/main.py` lifespan to pass `SessionLocal`. Do this in one commit with the model changes.
**Warning signs:** `TypeError: __init__() got an unexpected keyword argument` in test output.

### Pitfall 2: Session Lifecycle Mismatch
**What goes wrong:** Holding a DB session open while BayBE runs (3-10s for recommend). Session may timeout or cause write contention.
**Why it happens:** Natural instinct is to open session at start of `recommend()` and close at end.
**How to avoid:** Use session-per-DB-operation: open session → read → close session → compute → open session → write → close session. The threading lock protects the in-memory state; the DB sessions are only for I/O.
**Warning signs:** `OperationalError: database is locked` during concurrent requests.

### Pitfall 3: Forgetting to Update Transfer Metadata Path
**What goes wrong:** `get_transfer_metadata()` still reads from `.transfer` files, which no longer get written.
**Why it happens:** Easy to update `_save_campaign_unlocked` but forget `get_transfer_metadata` and the transfer writing in `get_or_create_campaign`.
**How to avoid:** Search for all `self._campaigns_dir` references. There are exactly 5: `_campaign_path`, `_fingerprint_path`, `get_transfer_metadata` (read), transfer metadata write in `get_or_create_campaign`, and `migrate_legacy_campaigns`. All must be updated.
**Warning signs:** Transfer metadata returns `None` for campaigns that should have it.

### Pitfall 4: Large Campaign JSON and SQLite
**What goes wrong:** One campaign file is 19.9MB (legacy discrete-grid format). Writing this to SQLite Text column works but the `campaign_json = campaign.to_json()` call happens while the lock is held.
**Why it happens:** Serialization of large campaigns is slow.
**How to avoid:** This is the existing behavior (file write was also slow). No new risk. SQLite handles Text up to 1GB. The 19MB campaign is an outlier from a legacy format; new campaigns are 5-9KB.
**Warning signs:** None expected — same perf characteristics as file I/O.

### Pitfall 5: Test Fixture Changes Breaking Existing Tests
**What goes wrong:** Changing the `optimizer_service` fixture signature means all 240+ tests must work with the new pattern.
**Why it happens:** Tests directly reference `tmp_campaigns_dir` and check file existence.
**How to avoid:** 
1. Update `conftest.py`: new fixture creates in-memory DB + SessionLocal, passes to OptimizerService
2. Remove `tmp_campaigns_dir` fixture (or keep for migration tests only)
3. Tests that check `campaign_file.exists()` must change to DB queries
4. Run full test suite after each change
**Warning signs:** Tests that assert file paths exist will fail.

### Pitfall 6: Pending Recommendation Session Scope
**What goes wrong:** `_save_pending` and `_remove_pending` commit immediately, but the caller's session (from `get_db()`) is still open. If the caller later rolls back, the pending rec state is inconsistent.
**Why it happens:** Using the same session for pending recs and measurement recording.
**How to avoid:** The pending rec operations should use the same session as the request handler (`db` from `get_db()`). The commit at the end of the request handler commits both the measurement and the pending rec deletion atomically. Remove the explicit `session.commit()` from `_save_pending`/`_remove_pending` and let the caller commit.
**Warning signs:** Orphaned pending recommendations after failed measurement saves.

## Test Strategy

### Test Fixture Changes

**Current fixture:**
```python
@pytest.fixture()
def tmp_campaigns_dir(tmp_path: Path) -> Path:
    d = tmp_path / "campaigns"
    d.mkdir()
    return d

@pytest.fixture()
def optimizer_service(tmp_campaigns_dir: Path) -> OptimizerService:
    return OptimizerService(tmp_campaigns_dir)
```

**New fixture:**
```python
@pytest.fixture()
def test_session_factory(db_session):
    """Session factory that returns the test session (for OptimizerService)."""
    def factory():
        return db_session
    # Make it work as context manager too
    from contextlib import contextmanager
    @contextmanager
    def session_ctx():
        yield db_session
    return session_ctx

@pytest.fixture()
def optimizer_service(test_session_factory) -> OptimizerService:
    return OptimizerService(test_session_factory)
```

**Note:** The test session factory must yield the same `db_session` that has rollback-on-close behavior. This ensures test isolation.

### Tests to Update

| Test File | Tests Affected | Change Required |
|-----------|---------------|-----------------|
| `tests/conftest.py` | `optimizer_service` fixture | Change from Path to session factory |
| `tests/conftest.py` | `tmp_campaigns_dir` fixture | Keep only for migration tests |
| `tests/test_optimizer.py` | `test_create_campaign` | Remove file existence check, verify DB row |
| `tests/test_optimizer.py` | `test_campaign_persistence_across_restart` | Create new service with same session factory |
| `tests/test_optimizer.py` | `test_campaign_file_size_hybrid` | Check JSON string length instead of file size |
| `tests/test_optimizer.py` | `test_add_measurement_and_recommend_again` | Remove file existence check |
| `tests/test_brew.py` | `test_trigger_recommend_*` | Mock may need adjustment for pending rec DB writes |
| `tests/test_brew_multimethod.py` | Various | May need mock updates |

### New Tests to Add

1. **Campaign DB persistence:** Create campaign, verify `CampaignState` row exists with correct `campaign_key`, `campaign_json`, `bounds_fingerprint`
2. **Campaign DB load on restart:** Create campaign, clear cache, load from DB, verify same measurements
3. **Transfer metadata DB storage:** Create campaign with transfer learning, verify `transfer_metadata` JSON in DB
4. **Pending recommendation CRUD:** Save, load, remove pending recommendation via DB
5. **File→DB migration:** Create campaign files in temp dir, run migration, verify DB rows match
6. **Migration idempotency:** Run migration twice, verify no duplicates
7. **Partial migration recovery:** Insert some campaigns into DB, run migration on full file set, verify only missing ones added
8. **Pending migration:** Create pending_recommendations.json, run migration, verify DB rows
9. **Large campaign migration:** Test with a large JSON blob (simulate 19MB campaign)
10. **Stale pending cleanup:** Verify pending recs older than N days can be queried/deleted

### Test Execution

All tests should run with in-memory SQLite (existing pattern via `BEANBAY_DATABASE_URL=sqlite:///:memory:`). The new tables are created by `Base.metadata.create_all()` in `conftest.py` — just importing the new models is sufficient.

## Risk Assessment

### Low Risk
- **Model creation:** Adding new SQLAlchemy models is well-established in this codebase. 8 models already exist following consistent patterns.
- **Table creation:** `Base.metadata.create_all()` is idempotent — existing tables are not affected.
- **Campaign JSON storage:** BayBE's `to_json()`/`from_json()` round-trips perfectly (validated by existing persistence tests).

### Medium Risk
- **Test updates:** ~10 tests directly reference filesystem paths. All must be updated. The test changes are mechanical but numerous.
- **Session management in OptimizerService:** New pattern (session factory) differs from existing code (all other code uses `get_db()` dependency). Must be carefully implemented to avoid leaks.
- **Pending recommendations transaction scope:** Moving from fire-and-forget file writes to transactional DB writes changes the atomicity semantics. Need to ensure pending rec save + measurement recording are consistent.

### Low Risk (Despite Appearances)
- **19MB campaign JSON in SQLite:** SQLite handles this fine. The `SQLITE_MAX_LENGTH` default is 1 billion bytes. Write performance is comparable to file I/O.
- **Missing `.transfer` files:** No `.transfer` files exist in production. The migration code handles this (NULL transfer_metadata). No risk of data loss.

### Mitigation: Rollback Strategy
- Original files are preserved as backup
- If migration fails, revert code changes and files are still there
- `campaigns_dir` property remains in Settings — can be re-enabled by reverting OptimizerService changes
- No destructive operations until explicit cleanup

## Decision Record

### D1: Use `Text` for campaign_json, not `LargeBinary`
**Decision:** Store campaign JSON as `Text` column.
**Rationale:** `Campaign.to_json()` returns `str`, `Campaign.from_json()` takes `str`. Using `Text` avoids encode/decode overhead. SQLite `TEXT` has no practical size limit. The data is human-readable in the DB (useful for debugging).
**Alternative considered:** `LargeBinary` — would require `.encode('utf-8')` / `.decode('utf-8')` on every read/write. No benefit.

### D2: OptimizerService takes `session_factory`, not `Session` or `engine`
**Decision:** Pass `SessionLocal` (the sessionmaker callable) to `__init__`.
**Rationale:** OptimizerService needs to create short-lived sessions at will (session-per-DB-operation). A single session would be held too long. An engine requires creating sessionmakers internally. A factory callable is the cleanest boundary.
**Alternative considered:** Injecting `engine` — would require OptimizerService to know about sessionmaker. Passing `SessionLocal` directly is simpler and matches the existing codebase pattern where `SessionLocal` is the primary session factory.

### D3: No Alembic — continue using `create_all`
**Decision:** New tables created via `Base.metadata.create_all()`, same as all existing tables.
**Rationale:** The project has no Alembic setup. All 8 existing tables use `create_all`. Introducing Alembic for 2 new tables adds complexity with no benefit (no existing production DBs need schema migration — the tables simply don't exist yet, and `create_all` handles that).
**Alternative considered:** Adding Alembic — significant setup overhead, overkill for this project's needs.

### D4: Migration at startup, not during table creation
**Decision:** File→DB migration runs as a separate function in lifespan, after `create_all`.
**Rationale:** `create_all` only creates tables; it doesn't migrate data. Data migration is application logic, not schema logic. Running at startup with idempotency checks is the simplest approach.

### D5: Keep `campaigns_dir` in Settings, don't delete files
**Decision:** `campaigns_dir` property remains. Original files are not deleted by migration.
**Rationale:** Safety. Users can verify DB integrity before deleting files. If something goes wrong, files are still the backup. Cleanup can be a separate optional step or future phase.

### D6: Remove `app.state.pending_recommendations` in-memory dict
**Decision:** Eliminate the in-memory pending recommendations dict on `app.state`.
**Rationale:** It was a secondary cache alongside the file-based store. With DB-backed storage, the DB query is fast enough (<1ms for SQLite). Having three stores (memory, file, DB) adds confusion. One store (DB) is simplest.

### D7: Pending recommendation helpers take `Session` parameter
**Decision:** `_save_pending(session, rec_id, rec)` takes the request's DB session.
**Rationale:** Pending recommendation operations are part of the request lifecycle (save during recommend, delete during record). Using the request's session means they participate in the same transaction. This provides atomicity: if measurement save fails, pending rec isn't deleted.

### D8: Integer primary keys for new models
**Decision:** Use `Integer` autoincrement PKs, not UUID strings.
**Rationale:** CampaignState and PendingRecommendation are internal entities never exposed via API URLs. Integer PKs are smaller, faster, and simpler. The logical key (`campaign_key` / `recommendation_id`) is a separate unique indexed column.

## Architecture Patterns

### Recommended Change Sequence

```
Step 1: Add models (campaign_state.py, pending_recommendation.py)
        Update __init__.py to import them
        → Tables created on next startup, no behavior change

Step 2: Add migration functions (can be in app/services/migration.py)
        Wire into lifespan AFTER create_all
        → Files copied to DB on startup, no behavior change

Step 3: Refactor OptimizerService
        Change __init__ to take session_factory
        Replace _campaign_path/_fingerprint_path with DB operations
        Replace _save_campaign_unlocked with DB write
        Update get_transfer_metadata to read from DB
        Update transfer metadata write in get_or_create_campaign
        → Campaign operations use DB, files no longer written

Step 4: Refactor pending recommendation helpers in brew.py
        Replace _save_pending/_load_pending/_remove_pending with DB operations
        Remove app.state.pending_recommendations usage
        → Pending recs use DB, file no longer written

Step 5: Update main.py lifespan
        Pass SessionLocal to OptimizerService
        Remove campaigns_dir from OptimizerService init
        Keep legacy migration for one more release

Step 6: Update tests
        Change fixtures
        Update assertions (file checks → DB checks)
        Add new migration tests
        Add new DB persistence tests

Step 7: Cleanup
        Remove migrate_legacy_campaigns() from OptimizerService
        Remove _PENDING_FILE and file helpers
        Remove app.state.pending_recommendations references
```

### Anti-Patterns to Avoid
- **Don't mix session scopes:** OptimizerService sessions and request `get_db()` sessions are independent. Never pass a request session to OptimizerService for campaign persistence.
- **Don't hold sessions across BayBE computation:** Open session → read → close → compute (seconds) → open session → write → close.
- **Don't decompose campaign JSON into relational columns:** The JSON is BayBE's internal format. It changes across versions. Treat as opaque blob.
- **Don't delete campaign files automatically:** Let users verify and delete manually. Safety first.

## Open Questions

1. **Stale pending recommendation cleanup**
   - What we know: 56 pending recs accumulated, most are stale (never recorded)
   - What's unclear: Should migration import all 56 or only recent ones? Should there be automatic cleanup?
   - Recommendation: Import all during migration. Add a simple cleanup query (delete where `created_at < now() - 7 days`) that can be called optionally. Don't auto-purge — let it accumulate for now, it's tiny data.

2. **Session factory vs SessionLocal direct import**
   - What we know: OptimizerService could import `SessionLocal` directly instead of receiving it as constructor parameter
   - What's unclear: Is dependency injection worth the extra test complexity?
   - Recommendation: Use constructor injection (pass `SessionLocal`). It's cleaner for testing — tests can pass a test-scoped session factory. Direct import would couple OptimizerService to the global `SessionLocal` and make test isolation harder.

3. **The 19MB legacy campaign**
   - What we know: One campaign (`boo_no_waste_super_blend`) has a 19MB searchspace (discrete grid format). All other campaigns are 5-9KB.
   - What's unclear: Will this cause issues during migration or normal operation?
   - Recommendation: No action needed. SQLite handles it fine. The campaign will migrate normally. If performance becomes an issue (unlikely — it's loaded once and cached), it can be rebuilt from measurements.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `app/services/optimizer.py`, `app/routers/brew.py`, `app/main.py`, `app/config.py`, `app/database.py`, `app/models/*.py`
- Existing test files: `tests/conftest.py`, `tests/test_optimizer.py`, `tests/test_brew.py`, `tests/test_brew_multimethod.py`
- Production data inspection: `data/campaigns/` (12 files), `data/pending_recommendations.json` (56 entries)

### Secondary (HIGH confidence)
- SQLAlchemy column types: `Text`, `JSON`, `String` — behavior verified by existing codebase usage (`Bean.parameter_overrides` uses `JSON` column, `Measurement.flavor_tags` uses `String` for JSON)
- SQLite limits: TEXT column supports up to 1 billion bytes (default `SQLITE_MAX_LENGTH`)

## Metadata

**Confidence breakdown:**
- Current state analysis: HIGH — direct codebase reading, production data inspection
- Target architecture: HIGH — follows existing codebase patterns exactly, no new libraries
- Migration strategy: HIGH — straightforward file→DB copy with idempotency
- Implementation patterns: HIGH — mirrors existing model/session patterns in codebase
- Test strategy: HIGH — test infrastructure well-understood from conftest.py analysis

**Research date:** 2026-02-24
**Valid until:** No expiration (internal codebase research, no external dependencies to go stale)

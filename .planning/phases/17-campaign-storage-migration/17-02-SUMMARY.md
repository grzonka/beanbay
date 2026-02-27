---
phase: 17
plan: "02"
name: "Core Service Refactor — File I/O to DB"
subsystem: "campaign-storage"
tags: ["optimizer", "migration", "sqlite", "pending-recommendations", "lifespan"]
one-liner: "OptimizerService, brew.py, and main.py fully migrated from filesystem to SQLite-backed campaign and pending-recommendation persistence"

dependency-graph:
  requires:
    - "17-01: CampaignState + PendingRecommendation models and migration functions"
  provides:
    - "OptimizerService backed by CampaignState DB table via session_factory"
    - "PendingRecommendation DB table used for all pending rec I/O in brew.py"
    - "migrate_legacy_campaign_files() standalone function in migration.py"
    - "lifespan wired: create tables → rename legacy files → migrate campaigns → migrate pending → OptimizerService(SessionLocal)"
  affects:
    - "17-03: test fixture updates (OptimizerService now requires session_factory arg)"

tech-stack:
  added: []
  patterns:
    - "session_factory = SessionLocal; session = session_factory(); try/finally session.close() — consistent with get_db()"
    - "_load_from_db/_save_to_db upsert pattern for CampaignState rows"
    - "In-memory dict caches (_cache, _fingerprints, _transfer_metadata) backed by DB for durability"

key-files:
  created: []
  modified:
    - "app/services/optimizer.py"
    - "app/routers/brew.py"
    - "app/main.py"
    - "app/services/migration.py"

decisions:
  - id: "D17-02-1"
    decision: "Use try/finally/session.close() not context manager for SessionLocal"
    rationale: "SessionLocal is a plain sessionmaker, not a context manager. Using 'with SessionLocal() as session:' would raise AttributeError at runtime. Consistent with get_db() dependency in database.py."
  - id: "D17-02-2"
    decision: "Transfer metadata stored in CampaignState.transfer_metadata JSON column with in-memory cache"
    rationale: "Replaces .transfer sidecar file. The _transfer_metadata dict mirrors _cache and _fingerprints for the same campaign key. Falls back to DB query on cache miss."
  - id: "D17-02-3"
    decision: "migrate_legacy_campaign_files() added as standalone function in migration.py, not on OptimizerService"
    rationale: "OptimizerService no longer has campaigns_dir, so the method cannot live there. Moving to migration.py groups all startup migration logic in one place."
  - id: "D17-02-4"
    decision: "campaigns_dir derived in lifespan as settings.data_dir / 'campaigns' rather than settings.campaigns_dir property"
    rationale: "Removes dependency on settings.campaigns_dir side-effect (mkdir on access). The dir creation is now done by migrate_campaigns_to_db() only if files exist to migrate."

metrics:
  duration: "~25 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 17 Plan 02: Core Service Refactor — File I/O to DB Summary

**One-liner:** OptimizerService, brew.py, and main.py fully migrated from filesystem to SQLite-backed campaign and pending-recommendation persistence

## What Was Built

### Task 1 — OptimizerService DB Refactor (`app/services/optimizer.py`)

Replaced the entire file I/O layer:

- **`__init__`** changed from `campaigns_dir: Path` to `session_factory` (callable returning a SQLAlchemy Session)
- **Removed:** `_campaign_path()`, `_fingerprint_path()`, `_save_campaign_unlocked()`, `migrate_legacy_campaigns()`
- **Added:** `_load_from_db(campaign_key)` → queries `CampaignState` table, returns `(campaign_json, fingerprint)` tuple
- **Added:** `_save_to_db(campaign_key)` → upserts `CampaignState` row; must be called with lock held
- **Added:** `self._transfer_metadata: dict[str, dict]` in-memory cache for transfer metadata
- `get_or_create_campaign()` now loads from DB on cache miss; writes transfer metadata to DB column instead of `.transfer` file
- `get_transfer_metadata()` checks in-memory cache first, then queries DB
- `recommend()` and `rebuild_campaign()` call `_save_to_db()` instead of `_save_campaign_unlocked()`
- Removed `from pathlib import Path` and `self._campaigns_dir`

### Task 2 — brew.py, main.py, migration.py

**`app/routers/brew.py`:**
- Replaced `_save_pending(data_dir, ...)`, `_load_pending(data_dir, ...)`, `_remove_pending(data_dir, ...)` with DB-backed versions taking `db: Session`
- Removed `app.state.pending_recommendations` in-memory dict usage from `show_recommendation` and `record_measurement`
- Removed `pathlib.Path`, `settings`, and redundant `json` (re-added only for `json.dumps(tags)`)
- Added `PendingRecommendation` model import

**`app/main.py`:**
- Imports `SessionLocal` from `app.database`
- Imports `migrate_legacy_campaign_files`, `migrate_campaigns_to_db`, `migrate_pending_to_db` from `app.services.migration`
- Lifespan sequence: create tables → `migrate_legacy_campaign_files(campaigns_dir)` → `migrate_campaigns_to_db(SessionLocal, campaigns_dir)` → `migrate_pending_to_db(SessionLocal, data_dir)` → `OptimizerService(SessionLocal)`
- Removed `settings.campaigns_dir` forced property access

**`app/services/migration.py`:**
- Added `migrate_legacy_campaign_files(campaigns_dir: Path) -> int` (moved from `OptimizerService.migrate_legacy_campaigns()`, also renames `.transfer` sidecar files)
- Fixed **critical bug**: replaced `with session_factory() as session:` (invalid for plain `sessionmaker`) with `session = session_factory(); try: ... finally: session.close()` in both `migrate_campaigns_to_db` and `migrate_pending_to_db`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid context-manager usage of SessionLocal in migration.py**

- **Found during:** Task 2 (reading migration.py before editing)
- **Issue:** Both `migrate_campaigns_to_db` and `migrate_pending_to_db` used `with session_factory() as session:`. SQLAlchemy's plain `sessionmaker` is NOT a context manager — this would raise `AttributeError: __enter__` at runtime.
- **Fix:** Replaced with `session = session_factory(); try: ... finally: session.close()` pattern, consistent with `get_db()` in `database.py`
- **Files modified:** `app/services/migration.py`
- **Commit:** `dadb130`

**2. [Rule 2 - Missing Critical] Added .transfer file renaming to migrate_legacy_campaign_files()**

- **Found during:** Task 2 (implementing migrate_legacy_campaign_files)
- **Issue:** The original `OptimizerService.migrate_legacy_campaigns()` only renamed `.json` and `.bounds` files. If a legacy campaign had a `.transfer` sidecar, it would be orphaned after renaming the main file.
- **Fix:** Also rename `{stem}.transfer` → `{new_key}.transfer` when it exists
- **Files modified:** `app/services/migration.py`
- **Commit:** `dadb130`

## Verification

- `ruff check` passes on all modified files (clean)
- No new LSP errors introduced (all reported errors are pre-existing project-wide type-stub issues)
- `main.py` no longer references the removed `migrate_legacy_campaigns` method on `OptimizerService`
- `brew.py` has no remaining references to `settings`, `Path`, or file-based pending storage
- `OptimizerService` has no remaining `Path` import or `_campaigns_dir` attribute

## Next Phase Readiness

**Plan 17-03 (test fixture updates):** Ready to execute. Tests that instantiate `OptimizerService` must be updated to pass a `session_factory` (e.g. in-memory SQLite `SessionLocal`) instead of a `campaigns_dir: Path`. The models and migration functions are all in place.

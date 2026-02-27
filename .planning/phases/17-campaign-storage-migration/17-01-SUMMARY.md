---
phase: 17-campaign-storage-migration
plan: 01
subsystem: database
tags: [sqlalchemy, sqlite, migration, campaign-storage, orm-models]

# Dependency graph
requires:
  - phase: 15-multi-method-campaigns
    provides: campaign file format (.json/.bounds/.transfer) and campaign_key conventions
  - phase: 16-transfer-learning
    provides: transfer_metadata sidecar file format and PendingRecommendation dict structure

provides:
  - CampaignState SQLAlchemy model (campaign_states table)
  - PendingRecommendation SQLAlchemy model (pending_recommendations table)
  - migrate_campaigns_to_db() idempotent file-to-DB migration function
  - migrate_pending_to_db() idempotent file-to-DB migration function

affects:
  - 17-02 (OptimizerService refactor will read/write CampaignState rows)
  - 17-03 (tests will use CampaignState/PendingRecommendation fixtures)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent startup migration: check-before-insert prevents duplicate rows"
    - "session_factory as context manager: `with session_factory() as session:` pattern for one-shot DB operations"
    - "Opaque JSON blob storage: campaign_json stored as raw Text (not decomposed) — BayBE controls serialization format"
    - "Optional sidecar files: bounds_fingerprint and transfer_metadata loaded from .bounds/.transfer files, None if absent"

key-files:
  created:
    - app/models/campaign_state.py
    - app/models/pending_recommendation.py
    - app/services/migration.py
  modified:
    - app/models/__init__.py

key-decisions:
  - "campaign_json stored as Text (opaque blob) — BayBE Campaign.to_json() output is not decomposed into columns"
  - "Migration functions leave original files in place as backup — no destructive cleanup"
  - "Idempotency via check-before-insert (not upsert) — simple and auditable"
  - "session_factory passed as argument (not imported) — enables testability with in-memory DB"

patterns-established:
  - "Idempotent migration pattern: query existing row before insert, skip if found"
  - "Optional sidecar loading: try/except on file reads, default to None on any error"

# Metrics
duration: ~15min
completed: 2026-02-24
---

# Phase 17 Plan 01: Campaign Storage Models & Migration Service Summary

**Two new SQLAlchemy models (CampaignState, PendingRecommendation) and idempotent file-to-DB migration service for campaign and pending recommendation data**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-24T00:00:00Z (approx)
- **Completed:** 2026-02-24T00:31:59Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `CampaignState` model with campaign_key unique index, campaign_json Text blob, bounds_fingerprint, transfer_metadata JSON, and timestamps
- Created `PendingRecommendation` model with recommendation_id unique index, recommendation_data JSON, and created_at timestamp
- Created `migrate_campaigns_to_db()` — reads .json/.bounds/.transfer file triplets, inserts CampaignState rows, skips existing (idempotent), handles corrupt files gracefully
- Created `migrate_pending_to_db()` — reads pending_recommendations.json dict, inserts PendingRecommendation rows, skips existing (idempotent)
- All 240 existing tests continue to pass (no behavior changes — new models registered but not yet consumed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CampaignState and PendingRecommendation models** — `90c602f` (feat)
2. **Task 2: Create migration service for file-to-DB migration** — `b206a18` (feat)

## Files Created/Modified

- `app/models/campaign_state.py` — CampaignState model (campaign_states table): Integer PK, unique indexed campaign_key, Text campaign_json, String(16) bounds_fingerprint, JSON transfer_metadata, created_at/updated_at
- `app/models/pending_recommendation.py` — PendingRecommendation model (pending_recommendations table): Integer PK, unique indexed recommendation_id, JSON recommendation_data, created_at
- `app/models/__init__.py` — Added CampaignState and PendingRecommendation imports and __all__ entries
- `app/services/migration.py` — migrate_campaigns_to_db() and migrate_pending_to_db() with idempotency, error handling, and logging

## Decisions Made

- **campaign_json stored as raw Text blob** — BayBE's Campaign.to_json() output is opaque; decomposing it into columns would couple us to BayBE internals. Store as-is and let BayBE deserialize.
- **Migration functions accept session_factory as argument** — enables testing with in-memory SQLite (no global import of SessionLocal), follows the pattern OptimizerService will use in Plan 02.
- **Idempotency via check-before-insert** — simple query before each insert; clear audit trail. Avoids UPSERT complexity for a migration that runs once.
- **Original files left as backup** — migration does not delete .json/.bounds/.transfer files. Cleanup can be manual after confirming successful migration.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `--timeout=60` flag in the plan's pytest invocation is not a built-in pytest flag (requires pytest-timeout plugin). Ran `pytest tests/ -x -q` instead. 240 tests passed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Ready for 17-02:** CampaignState and PendingRecommendation models exist. Migration functions are importable. OptimizerService refactor (Plan 02) can import and use these directly.
- **No blockers.** SessionLocal context manager protocol (SQLAlchemy 1.4+ sessionmaker supports `__enter__`/`__exit__`) works correctly with the `with session_factory() as session:` pattern used in migration.py.

---
*Phase: 17-campaign-storage-migration*
*Completed: 2026-02-24*

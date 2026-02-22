---
phase: 13-data-model-evolution-bean-metadata
plan: "02"
subsystem: database
tags: [alembic, migration, sqlite, data-migration, brew-methods, brew-setups, equipment]

# Dependency graph
requires:
  - phase: 13-01
    provides: New SQLAlchemy models that this migration brings into the DB schema
provides:
  - Alembic migration bf44156bfd41 adding all 7 new tables to production DB
  - Data migration linking all existing measurements to default Espresso brew setup
  - Deterministic default UUIDs for Espresso brew method + setup
affects:
  - 13-03 (bean metadata UI requires roast_date/process/variety columns to exist)
  - 14 (equipment CRUD requires brew_methods/grinders/brewers/papers/water_recipes tables)
  - 15 (multi-method brewing requires brew_setups + brew_setup_id on measurements)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Idempotent migration: checks table/column existence before creating (handles partial DB state)"
    - "Deterministic UUID seeds: 00000000-0000-0000-0000-000000000001/2 for default method/setup"
    - "Named FK constraints required for SQLite batch operations: 'fk_measurements_brew_setup_id'"
    - "render_as_batch=True in env.py for all SQLite column operations"

key-files:
  created:
    - migrations/versions/bf44156bfd41_add_equipment_brew_setups_bean_metadata.py
  modified: []

key-decisions:
  - "Idempotent migration over simple create: DB had tables pre-created by app startup (create_all), so migration uses inspector checks"
  - "Deterministic UUIDs for default seeded data: enables repeatable migrations and downgrade targeting"
  - "FK constraint must be named (not None) for SQLite batch alter: 'fk_measurements_brew_setup_id'"

patterns-established:
  - "Use inspector.get_table_names() to guard table creation in migrations when app.main creates_all at startup"
  - "Named FK constraints in batch operations for SQLite compatibility"

# Metrics
duration: 20min
completed: 2026-02-22
---

# Phase 13 Plan 02: Alembic Migration with Data Migration Summary

**Single Alembic migration creating 7 new tables, 4 new columns, and data-migrating all existing measurements to a default Espresso brew setup with deterministic UUIDs**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-02-22T22:53:23Z
- **Completed:** 2026-02-22T23:15:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Generated and refined Alembic migration `bf44156bfd41` — creates all 7 new tables (`brew_methods`, `grinders`, `brewers`, `papers`, `water_recipes`, `brew_setups`, `bags`), adds `roast_date/process/variety` to `beans`, adds `brew_setup_id` to `measurements`
- Data migration seeds default Espresso brew method (`00000000-0000-0000-0000-000000000001`) and brew setup (`00000000-0000-0000-0000-000000000002`), links all pre-existing measurements
- Verified migration against real pre-existing data: downgrade to `c06d948aa2d7`, inserted test bean + measurement, upgraded to HEAD, confirmed `brew_setup_id` populated
- 144/144 tests pass after migration; `alembic current` = `bf44156bfd41 (head)`

## Task Commits

1. **Task 1: Generate and refine Alembic migration** - `d927072` (feat)
2. **Task 2: Verify migration with data** - included in `d927072` (no new files; verification is ephemeral)

## Files Created/Modified

- `migrations/versions/bf44156bfd41_add_equipment_brew_setups_bean_metadata.py` — single migration covering all Phase 13 schema changes with idempotency guards and data migration

## Decisions Made

- **Idempotent migration with inspector checks:** `app/main.py` runs `Base.metadata.create_all()` at startup, meaning tables already existed in the DB when autogenerate ran. Added `inspector.get_table_names()` checks so migration handles both fresh DBs and DBs where `create_all` ran first.
- **Named FK constraint:** `batch_op.create_foreign_key(None, ...)` raises `ValueError: Constraint must have a name` in SQLite batch mode. Used `"fk_measurements_brew_setup_id"` as the constraint name.
- **Deterministic UUIDs for seeded data:** All-zero UUIDs (`00000000-0000-0000-0000-000000000001/2`) make migration repeatable and allow downgrade to safely reference the same IDs for deletion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FK constraint naming required for batch alter**

- **Found during:** Task 1 — generating migration
- **Issue:** `batch_op.create_foreign_key(None, ...)` raises `ValueError: Constraint must have a name`
- **Fix:** Changed to `"fk_measurements_brew_setup_id"` as explicit constraint name
- **Files modified:** `migrations/versions/bf44156bfd41_...py`
- **Commit:** `d927072`

**2. [Rule 2 - Missing Critical] Idempotency checks for create_all conflict**

- **Found during:** Task 1 — autogenerate missed new tables because they already existed
- **Issue:** `app/main.py` calls `Base.metadata.create_all()` at startup; tables existed before migration ran
- **Fix:** Added `inspector.get_table_names()` checks in upgrade/downgrade to handle both cases
- **Files modified:** `migrations/versions/bf44156bfd41_...py`
- **Commit:** `d927072`

## Issues Encountered

None beyond the two auto-fixed deviations above.

## User Setup Required

None.

## Next Phase Readiness

- **13-03 (Bean metadata UI):** All columns (`roast_date`, `process`, `variety` on `beans`, `brew_setup_id` on `measurements`) now exist in DB. Routes and templates ready.
- **Blockers:** None.

---
*Phase: 13-data-model-evolution-bean-metadata*
*Completed: 2026-02-22*

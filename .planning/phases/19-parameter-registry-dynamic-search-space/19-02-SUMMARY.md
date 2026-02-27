---
phase: 19-parameter-registry-dynamic-search-space
plan: "02"
subsystem: optimizer
tags: [baybe, parameter-registry, optimizer, refactor, backward-compat]

# Dependency graph
requires:
  - phase: 19-01-parameter-registry
    provides: build_parameters_for_setup, get_param_columns, get_default_bounds, get_rounding_rules public API
  - phase: 15-multi-method-brewing
    provides: BAYBE_PARAM_COLUMNS, DEFAULT_BOUNDS, ROUNDING_RULES, POUR_OVER_* constants in optimizer.py (being removed)
provides:
  - optimizer.py using parameter_registry for all parameter construction (no hardcoded constants)
  - transfer_learning.py using parameter_registry directly (no optimizer private function imports)
  - backward-compat re-exports in optimizer.py (BAYBE_PARAM_COLUMNS, DEFAULT_BOUNDS, etc.) for router compat
  - test_optimizer.py using parameter_registry constants (ESPRESSO_PARAMS, ESPRESSO_BOUNDS)
affects:
  - 19-03: routers can now drop backward-compat re-exports and import from parameter_registry directly
  - 20-advanced-espresso-parameters: optimizer already uses build_parameters_for_setup(), adding new params just requires registry update
  - 21-new-brew-methods: same pattern — registry drives optimizer without any optimizer changes

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backward-compat re-exports at module level: BAYBE_PARAM_COLUMNS = get_param_columns('espresso') until routers migrate"
    - "Internal calls to removed private functions replaced with public parameter_registry API"
    - "Tests import constants from parameter_registry, not optimizer"

key-files:
  created: []
  modified:
    - app/services/optimizer.py
    - app/services/transfer_learning.py
    - tests/test_optimizer.py

key-decisions:
  - "Backward-compat re-exports kept in optimizer.py: routers can continue importing DEFAULT_BOUNDS etc. from optimizer until Plan 03 removes them"
  - "transfer_learning.py: _resolve_bounds no longer needed — build_parameters_for_setup() accepts overrides directly"
  - "test_optimizer.py defines module-level ESPRESSO_PARAMS/ESPRESSO_BOUNDS from registry functions (not hardcoded or imported from optimizer)"
  - "transfer_learning.py was already fixed in 19-03 commit ecbe6da before this plan ran — re-edits were idempotent"

patterns-established:
  - "Refactor pattern: remove private helper → replace with public registry API at all call sites"
  - "Test pattern: import test constants from parameter_registry rather than optimizer module"

# Metrics
duration: 8min
completed: 2026-02-26
---

# Phase 19 Plan 02: Optimizer & Transfer Learning Refactor Summary

**`optimizer.py` and `transfer_learning.py` refactored to use `parameter_registry` — all hardcoded constants and private parameter-building functions removed, backward-compat re-exports added, 337 tests pass**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-02-26T08:00:00Z
- **Completed:** 2026-02-26T08:08:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Removed 6 hardcoded constant assignments and 4 private functions (`_get_param_columns`, `_get_default_bounds`, `_get_rounding_rules`, `_build_parameters`) from `optimizer.py`; replaced with `parameter_registry` imports and backward-compat re-exports
- `transfer_learning.py` now imports `build_parameters_for_setup` and `get_param_columns` directly from `parameter_registry` — no longer depends on optimizer private API
- `tests/test_optimizer.py` imports `get_param_columns`/`get_default_bounds` from `parameter_registry`; module-level `ESPRESSO_PARAMS` and `ESPRESSO_BOUNDS` replace old `BAYBE_PARAM_COLUMNS`/`DEFAULT_BOUNDS` everywhere
- All 337 tests pass (53 parameter_registry + 33 optimizer + remaining suite)

## Task Commits

1. **Task 1: Refactor optimizer.py** — `8142931` (refactor)
2. **Task 2: Update test_optimizer.py** — `dccc902` (refactor)

## Files Created/Modified

- `app/services/optimizer.py` — Removed 120 lines of hardcoded constants/private helpers; wired to parameter_registry; added backward-compat re-exports
- `app/services/transfer_learning.py` — Updated imports to use `build_parameters_for_setup` and `get_param_columns` from `parameter_registry` (was already fixed in prior commit `ecbe6da`)
- `tests/test_optimizer.py` — Imports from `parameter_registry`; `ESPRESSO_PARAMS`/`ESPRESSO_BOUNDS` module-level constants replace `BAYBE_PARAM_COLUMNS`/`DEFAULT_BOUNDS`

## Decisions Made

**Backward-compat re-exports in optimizer.py:** Routers (`brew.py`, `beans.py`, `history.py`) previously imported `DEFAULT_BOUNDS`, `BAYBE_PARAM_COLUMNS`, etc. from `optimizer`. Rather than requiring router changes in this plan, module-level re-exports (`BAYBE_PARAM_COLUMNS = get_param_columns("espresso")`) are added so routers continue working unchanged until Plan 03 migrates them.

**transfer_learning.py: _resolve_bounds removed:** The original plan called for keeping `_resolve_bounds` import from optimizer and replacing only `_build_parameters`/`_get_param_columns`. After examination, `build_parameters_for_setup()` already accepts `overrides` directly — no need to call `_resolve_bounds` first. The import of `_resolve_bounds` was eliminated entirely.

**test_optimizer.py uses registry, not optimizer, for constants:** Tests no longer couple to optimizer's internal constant names. `ESPRESSO_PARAMS = get_param_columns("espresso")` is defined at module level — clear and registry-driven.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] transfer_learning.py was already refactored in prior commit**
- **Found during:** Task 1 (checking transfer_learning.py state)
- **Issue:** `ecbe6da` (fix(19-03)) already updated transfer_learning.py to use parameter_registry before this plan ran
- **Fix:** Re-edits were idempotent; file already correct. No action needed beyond verification.
- **Files modified:** None (already correct)
- **Verification:** `from app.services.transfer_learning import build_transfer_campaign` imports cleanly
- **Committed in:** N/A (already committed in ecbe6da)

---

**Total deviations:** 1 (discovery, not a fix — file was already correct)
**Impact on plan:** No scope change. All planned changes executed; transfer_learning.py already done.

## Issues Encountered

None — all edits applied cleanly and tests passed on first run.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

**Phase 19 Plan 03 (router migration) is complete:** Routers already import from `parameter_registry` directly (completed in `3e27d81`). The backward-compat re-exports in `optimizer.py` are now technically redundant but harmless.

**Phase 19 is functionally complete:** All 3 plans executed. `PARAMETER_REGISTRY` is the single source of truth; optimizer and transfer learning both consume it; routers import from it directly; 337 tests pass.

**Ready for Phase 20 (Advanced Espresso Parameters):** `optimizer.py` calls `build_parameters_for_setup(method, brewer=None, overrides=overrides)` — adding new espresso parameters only requires updating `PARAMETER_REGISTRY` and the `Measurement` model, with no changes to optimizer logic.

---
*Phase: 19-parameter-registry-dynamic-search-space*
*Completed: 2026-02-26*

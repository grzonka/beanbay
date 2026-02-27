---
phase: 20-espresso-parameter-evolution
plan: "02"
subsystem: campaign-optimizer
tags: [brewer-context, campaign-outdated, fingerprinting, rebuild-flow, history, optimizer]
requires:
  - "20-01: schema & registry foundation (brewer capability flags, registry entries)"
  - "19-parameter-registry: get_param_columns, build_parameters_for_setup"
provides:
  - "Brewer context threaded through all campaign creation paths"
  - "_param_set_fingerprint() for structural change detection"
  - "is_campaign_outdated() / was_rebuild_declined() / decline_rebuild() / accept_rebuild() on OptimizerService"
  - "param_set_fingerprint + rebuild_declined columns on campaign_states"
  - "Campaign outdated detection in brew router → /brew/campaign-outdated prompt"
  - "Rebuild and decline-rebuild routes with 'remind once then quiet' behavior"
  - "Method-aware history delete_batch (no more hardcoded espresso)"
  - "campaign_outdated.html template"
affects:
  - "20-03: brew UI capability-driven parameter display (brewer now threaded, outdated flow complete)"
  - "Future: any new brew methods will automatically get method-aware campaign handling"
tech-stack:
  added: []
  patterns:
    - "Structural fingerprint vs bounds fingerprint: two separate hash functions for different change types"
    - "Integer decline counter (0/1/2): graceful reminder then permanent silence"
    - "_load_from_db 4-tuple: (campaign_json, bounds_fp, param_set_fp, rebuild_declined)"
    - "Method-aware campaign grouping in history delete_batch"
key-files:
  created:
    - "migrations/versions/7313802b80a0_merge_phase20_phase21_heads.py"
    - "migrations/versions/9052fc4244a4_add_param_set_fingerprint_rebuild_.py"
    - "app/templates/brew/campaign_outdated.html"
  modified:
    - "app/services/optimizer.py"
    - "app/services/transfer_learning.py"
    - "app/models/campaign_state.py"
    - "app/routers/brew.py"
    - "app/routers/history.py"
    - "tests/test_optimizer.py"
    - "tests/test_brew.py"
    - "tests/test_history.py"
decisions:
  - id: "param-set-fp-vs-bounds-fp"
    choice: "Two separate fingerprints: _param_set_fingerprint (structural) vs _bounds_fingerprint (numeric ranges)"
    rationale: "Structural changes (params added/removed) need separate detection from bounds expansion. Conflating them would either miss structural changes or over-trigger rebuilds on range expansions."
  - id: "rebuild-declined-integer"
    choice: "rebuild_declined is Integer (0/1/2) not Boolean"
    rationale: "'Remind once then quiet' requires three states: not declined / declined once (show one more reminder) / permanently declined. Boolean can't express this."
  - id: "legacy-campaigns-no-nag"
    choice: "is_campaign_outdated returns False when no stored fingerprint (legacy campaigns)"
    rationale: "Legacy campaigns predate fingerprinting. Nagging users to rebuild campaigns that have never been fingerprinted would be disruptive and confusing."
  - id: "history-method-grouping"
    choice: "delete_batch groups measurements by (method, setup_id, brewer) using id(brewer) as dict key"
    rationale: "Measurements from different brew setups need separate campaign rebuilds. Grouping by setup ensures each campaign key is rebuilt with the correct method and brewer context."
metrics:
  tests-before: 389
  tests-after: 405
  tests-added: 16
  duration: "~2h (two sessions)"
  completed: "2026-02-26"
---

# Phase 20 Plan 02: Brewer Context Wiring + Campaign Outdated Flow Summary

**One-liner:** Brewer threaded through all campaign creation paths with structural fingerprinting; outdated detection + rebuild/decline UX with remind-once-then-quiet behavior.

## What Was Built

### Task 1: Brewer Context Wiring + Structural Fingerprinting

**`app/services/optimizer.py`**
- `_param_set_fingerprint(method, brewer)` — stable SHA256 hash of sorted param names from `get_param_columns(method, brewer)`. Distinct from `_bounds_fingerprint` (which tracks numeric range changes).
- `_load_from_db` now returns 4-tuple: `(campaign_json, bounds_fp, param_set_fp, rebuild_declined)`
- `_save_to_db` stores `param_set_fingerprint` on every campaign save
- `brewer=None` added to: `_create_fresh_campaign`, `get_or_create_campaign`, `recommend`, `add_measurement`, `rebuild_campaign`, `get_recommendation_insights`
- New methods: `is_campaign_outdated()`, `was_rebuild_declined()`, `decline_rebuild()`, `accept_rebuild()`

**`app/services/transfer_learning.py`**
- `build_transfer_campaign(brewer=None)` — passes brewer to `build_parameters_for_setup` and `get_param_columns`
- `_collect_training_measurements(brewer=None)` — uses brewer-aware param columns

**`app/models/campaign_state.py`**
- `param_set_fingerprint = Column(String, nullable=True)` — stores structural fingerprint
- `rebuild_declined = Column(Integer, default=0)` — 0=not declined, 1=declined once, 2=permanently silent

**Migrations**
- `7313802b80a0_merge_phase20_phase21_heads.py` — merges phase 20 + phase 21 migration heads
- `9052fc4244a4_add_param_set_fingerprint_rebuild_.py` — adds both new columns to `campaign_states`

### Task 2: Brew Router + Campaign Outdated UX

**`app/routers/brew.py`**
- `trigger_recommend`: extracts `brewer` from `active_setup`, passes to `optimizer.recommend()` + `get_recommendation_insights()`. Checks `is_campaign_outdated` BEFORE recommend — redirects to `/brew/campaign-outdated` if outdated and not declined.
- `record_measurement`: passes `brewer` from active setup to `optimizer.add_measurement()`
- `show_best`: passes `brewer` to get capability-filtered `param_defs` for dynamic template rendering
- `GET /brew/campaign-outdated` — shows which new params the brewer now supports (diff vs Tier 1)
- `POST /brew/rebuild-campaign` — calls `optimizer.accept_rebuild()`, redirects to `/brew/recommend`
- `POST /brew/decline-rebuild` — calls `optimizer.decline_rebuild()`, redirects to `/brew`

**`app/routers/history.py`**
- `delete_batch` no longer hardcodes `get_param_columns("espresso")`. Groups remaining measurements by `(method, setup_id, id(brewer))`, uses `get_param_columns(method, brewer)` and `make_campaign_key(bean_id, method, setup_id)` per group. Falls back to `espresso/None` for legacy measurements without brew_setup.

**`app/templates/brew/campaign_outdated.html`**
- daisyUI card showing "New Parameters Available" with badge list of new params
- "Rebuild Campaign" form (POST `/brew/rebuild-campaign`) + "Skip for Now" form (POST `/brew/decline-rebuild`)

## Tests

**`tests/test_optimizer.py`** — 10 new tests (already in Task 1 commits):
- `_param_set_fingerprint` stability, changes on tier change, tier1 behavior
- Fingerprint stored on campaign creation
- `is_campaign_outdated` — false/true/legacy (no stored fp)
- `decline_rebuild` increments counter, caps at 2
- `accept_rebuild` resets counter and updates fingerprint

**`tests/test_brew.py`** — 6 new tests:
- `test_trigger_recommend_passes_brewer_to_optimizer` — verifies brewer=None passed when no active setup
- `test_trigger_recommend_outdated_campaign_redirects_to_prompt` — outdated + not declined → redirect
- `test_trigger_recommend_outdated_campaign_declined_proceeds_normally` — declined → recommend proceeds
- `test_campaign_outdated_page_renders` — page has expected content
- `test_rebuild_campaign_route_calls_accept_rebuild_and_redirects` — calls accept_rebuild, goes to /brew/recommend
- `test_decline_rebuild_route_calls_decline_and_redirects` — calls decline_rebuild, goes to /brew

**Final test count: 405 passed (up from 399)**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Merge migration needed for phase 20+21 diverged heads**
- **Found during:** Task 1 — alembic detected two heads when generating migration
- **Fix:** Created `7313802b80a0_merge_phase20_phase21_heads.py` merge migration before the new columns migration
- **Files:** `migrations/versions/7313802b80a0_merge_phase20_phase21_heads.py`

**2. [Rule 1 - Bug] Unused `_param_set_fingerprint` import in campaign_outdated route**
- **Found during:** Task 2 pre-commit lint check
- **Fix:** Removed unused import — the route uses `get_param_columns` directly to compute new_params
- **Files:** `app/routers/brew.py`

**3. [Rule 1 - Bug] Unused `call` import in test**
- **Found during:** Task 2 pre-commit lint check
- **Fix:** Removed `call` from `from unittest.mock import MagicMock, call`
- **Files:** `tests/test_brew.py`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `3f6b04e` | feat(20-02): wire brewer into campaign creation + structural fingerprinting |
| Task 1 (lint fix) | `e64dd99` | feat(20-02): wire brewer into campaign creation + structural fingerprinting |
| Task 2 (brew router) | `e64dd99` | Already committed in prior session — brew.py, history.py, campaign_outdated.html, tests |
| Task 2 (lint fix) | `fc12c94` | feat(20-02): brew router brewer wiring + campaign outdated prompt + rebuild flow |

## Next Phase Readiness

Phase 20 Plan 03 (Brew UI — capability-driven parameter display) can now proceed:
- ✅ Brewer is threaded through all optimizer paths
- ✅ Campaign outdated detection and rebuild UX complete
- ✅ `param_defs` passed to `show_best` template for dynamic rendering
- ✅ 405 tests passing, no regressions

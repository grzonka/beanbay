---
phase: "03"
plan: "03-01"
name: "Brew Router & Optimization Loop"
subsystem: "optimization-loop"
tags: [fastapi, htmx, jinja2, baybe, espresso, mobile-ui]

dependency-graph:
  requires:
    - "02-01: bean management, mobile shell, parameter overrides"
    - "01-02: BayBE optimizer service (OptimizerService.recommend, add_measurement)"
  provides:
    - "Complete espresso optimization cycle: recommend → brew → rate → recall best"
    - "Brew router: /brew, /brew/recommend, /brew/record, /brew/best"
    - "Mobile-first recipe display (6 params + brew ratio in large scannable text)"
    - "Failed-shot auto-taste=1 logic"
    - "Recommendation deduplication via recommendation_id"
  affects:
    - "Phase 4: shot history builds on Measurement records created here"
    - "Phase 5: insights chart uses taste scores from records created here"
    - "Phase 6: analytics uses all accumulated measurement data"

tech-stack:
  added: []
  patterns:
    - "Server-side pending_recommendations dict for single-user session state (keyed by UUID)"
    - "MagicMock (sync) vs AsyncMock — matched to actual method signatures in tests"
    - "Deduplication via unique recommendation_id on Measurement table"
    - "Auto-taste=1 for failed shots enforced in router before DB save"

key-files:
  created:
    - "tests/test_brew.py — 17 test cases for full optimization loop"
  modified: []
  pre-existing:
    - "app/routers/brew.py — brew router (5 endpoints, implemented in Phase 2 commit)"
    - "app/templates/brew/index.html — main brew page"
    - "app/templates/brew/recommend.html — recommendation display + rate form"
    - "app/templates/brew/best.html — best recipe recall page"
    - "app/templates/brew/_recipe_card.html — reusable 6-param recipe partial"
    - "app/static/css/main.css — brew-specific CSS (.recipe-param, .score-slider, .failed-toggle, .ratio)"
    - "app/main.py — brew router already wired in; Brew nav link in base.html"

decisions:
  - "Brew router + templates were already present from prior work (commit 7786c8f) — no regeneration needed, only tests were missing"
  - "Used MagicMock (not AsyncMock) for optimizer.add_measurement in tests — add_measurement is sync; avoids RuntimeWarning"
  - "17 tests written vs 10 planned — extra cases cover failed-shot exclusion from best, no-active-bean guards on all routes, and conditional Repeat Best button"

metrics:
  duration: "~15 minutes"
  completed: "2026-02-22"
  tests-before: 43
  tests-after: 60
  tests-added: 17
---

# Phase 3 Plan 01: Brew Router & Optimization Loop Summary

**One-liner:** Full optimization cycle implemented — BayBE recommend→rate→record→best-recall with mobile-first recipe display, failed-shot handling, and deduplication.

## What Was Built

The complete espresso optimization loop is now functional:

1. **GET /brew** — Entry point. Shows "Get Recommendation" always; shows "Repeat Best" only after shots exist.
2. **POST /brew/recommend** — Calls `OptimizerService.recommend()`, stores result in `app.state.pending_recommendations`, redirects to display page.
3. **GET /brew/recommend/{id}** — Shows 6 recipe parameters in large, arm's-length-readable text plus the dose:yield brew ratio. Provides taste slider (1–10, 0.5 steps), optional extraction time field, and a prominent "Failed shot" toggle.
4. **POST /brew/record** — Saves measurement to SQLite and adds to BayBE campaign. Auto-sets taste=1 for failed shots. Deduplicates by `recommendation_id`.
5. **GET /brew/best** — Shows the highest-tasting non-failed shot for the active bean. Empty state when no shots recorded. Includes "Brew Again & Rate" form.

All endpoints guard against missing active bean and redirect to `/beans`.

## Tests Written

17 test cases in `tests/test_brew.py`:

| Test | What it verifies |
|------|-----------------|
| `test_brew_index_no_active_bean_redirects` | Redirect to /beans without cookie |
| `test_brew_index_with_active_bean` | Shows action buttons |
| `test_brew_index_no_repeat_best_without_measurements` | Repeat Best hidden initially |
| `test_brew_index_shows_repeat_best_with_measurements` | Repeat Best appears after shots |
| `test_trigger_recommend_no_active_bean` | Redirect to /beans |
| `test_trigger_recommend_generates_and_redirects` | Calls optimizer, redirects to rec URL |
| `test_show_recommendation_displays_params` | All 6 params + 1:2.1 ratio visible |
| `test_show_recommendation_expired_redirects` | Unknown rec_id → back to /brew |
| `test_record_measurement_saves_and_redirects` | DB save + redirect |
| `test_record_failed_shot_sets_taste_to_1` | is_failed=true → taste=1 |
| `test_record_measurement_deduplication` | Second POST with same rec_id ignored |
| `test_record_measurement_no_active_bean` | Redirect to /beans |
| `test_show_best_no_measurements` | Empty state shown |
| `test_show_best_shows_highest_rated` | Returns 9.0 not 6.0/7.5 |
| `test_show_best_excludes_failed_shots` | Failed-only → empty state |
| `test_show_best_displays_brew_ratio` | 1:2.1 in output |
| `test_show_best_no_active_bean` | Redirect to /beans |

## Deviations from Plan

### Auto-fixed Issues

None — all router logic was pre-existing.

### Scope Note

The brew router, all 4 templates, brew-specific CSS, and main.py wiring were already present from commit `7786c8f` (earlier in Phase 3 planning). This plan execution focused on the missing tests, which were the only gap.

## Verification

- **60/60 tests passing** (43 existing + 17 new)
- All 43 Phase 1+2 tests still pass
- No warnings in brew tests

## Next Phase Readiness

Phase 4 (Shot History & Feedback Depth) can begin. It requires:
- Measurement records with `bean_id`, `taste`, `created_at`, `notes` — all present ✓
- Reverse-chronological history view per bean
- Optional notes field (column exists in model, not yet exposed in UI)
- Expandable flavor profile panel (columns exist in model)

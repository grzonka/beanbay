---
phase: 05-insights-trust
verified: 2026-02-22T12:00:00Z
status: passed
score: 3/3 must-haves verified
gaps: []
human_verification:
  - test: "View insights page with active bean and 5+ shots"
    expected: "Chart renders with cumulative best line and individual shot scatter points in correct colors; failed shots shown in red"
    why_human: "Chart.js rendering requires browser; can't verify visually from code"
  - test: "Get a recommendation and check the insight badge"
    expected: "Phase badge (Random exploration or Bayesian optimization) and plain-language explanation display below the recipe card"
    why_human: "Visual appearance and layout cannot be verified programmatically"
  - test: "Pull 10+ shots with improving scores, then check convergence indicator"
    expected: "Convergence badge transitions through stages: Getting started → Early exploration → Narrowing in → Likely near optimal"
    why_human: "Requires runtime state transitions with real optimizer; convergence logic is tested but visual rendering needs human check"
  - test: "View predicted taste range on a Bayesian recommendation (after 2+ shots)"
    expected: "Expected taste shows predicted mean and range (e.g., ~7.5 (6.5 – 8.5))"
    why_human: "Requires real BayBE surrogate model with posterior_stats; mocked in tests"
---

# Phase 5: Insights & Trust Verification Report

**Phase Goal:** Users can see that the optimizer is learning and understand why it suggests what it suggests — building confidence to keep experimenting.
**Verified:** 2026-02-22T12:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can view a chart showing cumulative best taste score over time for a bean, with individual shot scores visible | ✓ VERIFIED | `insights/_progress_chart.html` renders Chart.js canvas with `cumulative_best` line dataset and `individual_scores` scatter dataset; `_build_chart_data()` in `insights.py` computes running best; chart gated on `shot_count >= 2`; failed shots colored red via `failed_indices` |
| 2 | Each recommendation displays whether BayBE is exploring or exploiting, in plain language | ✓ VERIFIED | `optimizer.py:get_recommendation_insights()` calls `select_recommender()` to detect `RandomRecommender` vs `BotorchRecommender`; returns `phase_label` and contextual `explanation`; `brew.py:trigger_recommend()` calls this at recommend time and stores in `rec["insights"]`; `_recommendation_insights.html` renders badge + explanation; predicted taste range shown when available |
| 3 | User can see a convergence indicator showing how far along the optimization is | ✓ VERIFIED | `insights.py:_compute_convergence()` implements 5-state machine: getting_started (< 3 shots), early_exploration (3-7 shots), narrowing_in (recent improvement), near_optimal (no improvement in last 5), refining (default); `_convergence_badge.html` renders label + description; `insights/index.html` includes badge and optimizer phase indicator |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/optimizer.py` | `get_recommendation_insights()` method | ✓ VERIFIED | 357 lines; method at line 257; uses `select_recommender()` for phase detection; computes `posterior_stats` for predicted taste; thread-safe under `_lock` |
| `app/routers/brew.py` | Insights computed at recommend time | ✓ VERIFIED | 274 lines; lines 98-102 call `get_recommendation_insights()` and store in `rec["insights"]`; passed to template via context |
| `app/templates/brew/_recommendation_insights.html` | Phase badge + explanation partial | ✓ VERIFIED | 25 lines; renders badge with `insight-badge-{{ insights.phase }}` class, explanation text, and optional predicted taste range |
| `app/templates/brew/recommend.html` | Includes insights partial | ✓ VERIFIED | 116 lines; line 17 `{% include "brew/_recommendation_insights.html" %}` |
| `app/routers/insights.py` | Insights page with convergence logic | ✓ VERIFIED | 217 lines; `_compute_convergence()` with 5 states; `_build_chart_data()` for Chart.js; route queries measurements, determines optimizer phase, computes best taste |
| `app/templates/insights/index.html` | Insights page template | ✓ VERIFIED | 51 lines; shows bean name, shot count, best taste, convergence badge, optimizer phase badge, progress chart, navigation actions |
| `app/templates/insights/_progress_chart.html` | Chart.js chart | ✓ VERIFIED | 103 lines; Chart.js 4.4.7 CDN; line chart with cumulative best + scatter for individual shots; failed shots in red; tooltips; empty state for < 2 shots |
| `app/templates/insights/_convergence_badge.html` | Convergence badge | ✓ VERIFIED | 11 lines; renders colored badge with label and description |
| `app/templates/base.html` | Insights nav link | ✓ VERIFIED | 42 lines; line 19 `<a href="/insights" class="nav-link">Insights</a>` |
| `app/main.py` | Insights router included | ✓ VERIFIED | 68 lines; line 12 imports insights; line 56 `app.include_router(insights.router)` |
| `tests/test_insights.py` | Test coverage | ✓ VERIFIED | 184 lines; 6 tests: requires active bean, empty bean, measurements present, chart data, convergence status, nav link |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `brew.py:trigger_recommend` | `optimizer.get_recommendation_insights` | Direct call (line 99) | ✓ WIRED | Called after `recommend()`, stored in `rec["insights"]` |
| `brew.py:show_recommendation` | `_recommendation_insights.html` | Template include (line 17 of recommend.html) | ✓ WIRED | `insights` dict passed in template context |
| `insights.py:insights_page` | `_convergence_badge.html` | Template include (line 29 of index.html) | ✓ WIRED | `convergence` dict from `_compute_convergence()` passed in context |
| `insights.py:insights_page` | `_progress_chart.html` | Template include (line 41 of index.html) | ✓ WIRED | `chart_data` from `_build_chart_data()` passed in context, serialized via `tojson` |
| `main.py` | `insights.router` | `include_router` (line 56) | ✓ WIRED | Router mounted at `/insights` prefix |
| `base.html` nav | `/insights` route | `<a href="/insights">` (line 19) | ✓ WIRED | Nav link present globally |
| `optimizer.py:get_recommendation_insights` | BayBE `select_recommender` | Method call on `TwoPhaseMetaRecommender` (line 280) | ✓ WIRED | Correctly detects `RandomRecommender` vs Bayesian phase |
| `optimizer.py:get_recommendation_insights` | BayBE `posterior_stats` | Method call on campaign (line 330) | ✓ WIRED | Called when `not is_random and shot_count >= 2`; wrapped in try/except for robustness |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| VIZ-01: User can see optimization progress chart (cumulative best taste over time) | ✓ SATISFIED | — |
| VIZ-02: User can see why a recipe was suggested (exploring vs exploiting) | ✓ SATISFIED | — |
| VIZ-05: User can see exploration/exploitation balance indicator (how converged the optimizer is) | ✓ SATISFIED | — |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | No anti-patterns found in any phase 5 files |

### Human Verification Required

### 1. Chart Rendering
**Test:** Open `/insights` with an active bean that has 5+ shots (mix of failed and successful)
**Expected:** Chart.js renders a line chart with a cumulative best line (brown, filled area) and individual shot scatter points. Failed shots should appear in red. Tooltips show taste score on hover.
**Why human:** Chart.js rendering is client-side JavaScript; structural verification confirms data flow but visual rendering requires a browser.

### 2. Recommendation Insights Display
**Test:** Trigger a recommendation via `/brew` for a bean with 0 shots, then again after 3+ shots
**Expected:** First recommendation shows "Random exploration" badge with "Exploring randomly" explanation. After shots, shows "Bayesian optimization" badge with contextual explanation. Predicted taste range appears after 2+ measurements.
**Why human:** Visual layout, badge styling, and predicted taste from real BayBE model require runtime verification.

### 3. Convergence State Transitions
**Test:** Pull 10+ shots with gradually improving scores, then check `/insights`
**Expected:** Convergence badge transitions: "Getting started" (< 3 shots) → "Early exploration" (3-7 shots) → "Narrowing in" (when recent shots beat previous best) → "Likely near optimal" (no improvement in last 5 non-failed shots)
**Why human:** Full state machine exercise requires real workflow with optimizer; unit tests cover individual states but end-to-end UX needs manual check.

### 4. Mobile Layout
**Test:** Open `/insights` on a mobile device or narrow viewport
**Expected:** Chart resizes responsively; convergence badge and content stack vertically; nav link accessible
**Why human:** CSS responsive behavior cannot be verified from code alone.

### Gaps Summary

No gaps found. All 3 observable truths are fully verified:

1. **Progress chart**: `_build_chart_data()` correctly computes cumulative best and individual scores from DB measurements. Chart.js renders with proper datasets, colors, and empty state handling. Gated on ≥ 2 shots.

2. **Explore/exploit insights**: `get_recommendation_insights()` uses BayBE's `select_recommender()` to detect random vs Bayesian phase. Contextual explanations vary based on shot count and improvement trends. Predicted taste range computed via `posterior_stats()` when surrogate model is available. Insights computed at recommend time in `brew.py` and stored with the recommendation — no extra latency.

3. **Convergence indicator**: 5-state convergence machine in `_compute_convergence()` with plain-language labels and descriptions. States: getting_started, early_exploration, narrowing_in, near_optimal, refining. Rendered as a colored badge on the insights page alongside the current optimizer phase.

All 98 tests pass (including 6 insights-specific tests and 3 optimizer insights tests). No stub patterns, no TODOs, no placeholder content. All key links verified as wired.

---

_Verified: 2026-02-22T12:00:00Z_
_Verifier: OpenCode (gsd-verifier)_

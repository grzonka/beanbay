# Bugfix Round 1 — Post-Implementation Fixes

**Date**: 2026-03-24
**Scope**: 6 bugs found during Playwright end-to-end testing of the frontend optimization UX feature set.

---

## Bug 1: PlotlyChart crashes with "Element type is invalid"

**Severity**: Critical — crashes every page with a Plotly chart (brew detail, campaign detail, person preferences).

**Root cause**: `import Plot from 'react-plotly.js'` fails under Vite's ESM/CJS interop. The default export resolves to a module object instead of a React component. The `react-plotly.js` docs specify two import patterns: the default import (requires `plotly.js` as a peer dep resolved at build time) and the factory pattern (explicit, works with any bundle).

**Fix**: Use the factory pattern from `react-plotly.js/factory` as documented at https://github.com/plotly/react-plotly.js#customizing-the-plotlyjs-bundle. Verified via Context7:

```typescript
import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
const Plot = createPlotlyComponent(Plotly);
```

**Files**:
- Modify: `frontend/src/components/PlotlyChart.tsx` — change import to factory pattern
- Modify: `frontend/src/plotly.d.ts` — add type declaration for `react-plotly.js/factory`

**Verification**: Every page that renders a chart must load without crash — brew detail (TasteRadar), campaign detail (8 charts), person preferences (5 charts).

---

## Bug 2: useSuggest hook hits 404 — wrong API URL

**Severity**: Critical — "Get Suggestion" button always fails.

**Root cause**: `hooks.ts` line ~210 POSTs to `/optimize/recommend` but the actual endpoint is `/optimize/campaigns/{campaign_id}/recommend`. Additionally, the `JobStatus` type references `job.result?.recommendation_id` but the API returns `result_id` as a top-level field on the job object.

**Fix**: Correct the URL and response type in the `useSuggest` mutation and `JobStatus` interface:
- POST URL: `/optimize/campaigns/${campaign.id}/recommend` (campaign ID interpolated)
- `JobStatus` type: replace `result?: { recommendation_id: string }` with `result_id: string | null`
- Recommendation fetch: use `job.result_id`

**Files**:
- Modify: `frontend/src/features/optimize/hooks.ts` — fix `useSuggest` mutation function and `JobStatus` interface

**Verification**: Click "Get Suggestion" in BrewWizard step 1 with a bag and setup selected. Should show spinner, then populate parameter fields and display info banner with predicted score.

---

## Bug 3: Bag autocomplete shows "Unknown bean" instead of actual bean name

**Severity**: Moderate — user cannot identify which bag to select.

**Root cause**: `BrewStepSetup.tsx` builds a `beanMap` from a separate `/beans` query to resolve `bean_id` → `bean_name`. When the bag dropdown opens before the beans query resolves, `beanMap` is empty and all bags fall through to `'Unknown bean'`. This is a race condition in the client-side join.

**Fix**: Eliminate the client-side join. Return `bean_name` directly from the bags API endpoint so the frontend doesn't need a separate beans query.

Backend: The `GET /bags` list endpoint (in `src/beanbay/routers/beans.py:675`, function `list_bags`) serializes items using `BagRead` (defined in `src/beanbay/schemas/bean.py:101`). Add a `bean_name: str | None` field to `BagRead`. The `Bag` model has a `bean` relationship (via `bean_id` FK), so `bag.bean.name` is accessible. The `list_bags` endpoint already loads bags with their relationships — add `bean_name=bag.bean.name` to the serialization.

Frontend: Remove the beans query from `BrewStepSetup`. Use `bag.bean_name` directly in the label formatter instead of `beanMap[bag.bean_id]`.

**Files**:
- Modify: `src/beanbay/schemas/bean.py` — add `bean_name: str | None = None` field to `BagRead`
- Modify: `src/beanbay/routers/beans.py` — populate `bean_name` from `bag.bean.name` in `list_bags()` and `list_bean_bags()`
- Modify: `frontend/src/features/bags/hooks.ts` — add `bean_name` to `BagListItem` interface
- Modify: `frontend/src/features/brews/components/BrewStepSetup.tsx` — remove beans query and `beanMap`, use `bag.bean_name` directly

**Verification**: Open BrewWizard, click Bag dropdown. Options should show "Ethiopia Yirgacheffe — 250g" not "Unknown bean — 250g".

---

## Bug 4: Dashboard stats show 0 — auto-resolves to default person

**Severity**: Moderate — dashboard stats are useless when the default person has no brews.

**Root cause**: The `_resolve_person_id` dependency in `dependencies.py` auto-falls-back to the default person (the `Person` with `is_default=True`) when no explicit `person_id` query parameter is provided. The dashboard hooks call `/stats/brews`, `/stats/taste`, `/stats/cuppings` without a `person_id`, so all three auto-filter to the default person's data only.

**Design decision**: The dashboard should show aggregated data across ALL users. The person preferences page (`/optimize/people/{id}/preferences`) already takes an explicit `person_id` in the URL path and is unaffected.

**Fix**: Change `_resolve_person_id` to return `None` when no explicit `person_id` is provided, instead of auto-resolving to the default person. When `person_id` is `None`, `_base_brew_filter` does not add a person filter, so the query returns data for all users.

Three endpoints use `OptionalPersonIdDep`: `/stats/brews`, `/stats/taste`, `/stats/cuppings`. After this change, all three will return aggregated data by default, filterable to a specific person via `?person_id=...` query parameter.

**Files**:
- Modify: `src/beanbay/dependencies.py` — change `_resolve_person_id` fallback from default-person lookup to `return None`

**Test impact**: Existing stats tests do not depend on auto-resolve behavior. The empty-state test calls without `person_id` and expects zeros (still correct — no brews in DB). Tests with brews pass an explicit `person_id`. No test updates needed — verify existing tests still pass.

**Verification**: Navigate to dashboard. "Total Brews" should show 10 (not 0). "This Week" should show 10. "Fail Rate" should show "10.0%". "Best Brew Score" should show 9.0.

---

## Bug 5: Timestamps show "1h ago" for just-created brews

**Severity**: Moderate — relative time display is consistently wrong by ~1h (user's UTC offset).

**Root cause**: The SQLite database stores naive `datetime` objects (no timezone). FastAPI's default JSON serialization outputs them as ISO 8601 strings without a timezone suffix (e.g., `"2026-03-24T11:51:49"`). When JavaScript's `new Date()` parses this string, it interprets it as local time. But the server generated the timestamp in UTC. The difference between UTC and the user's local timezone (e.g., UTC+1) creates the offset.

**Fix**: Ensure all datetime serialization includes the UTC timezone marker. Use a custom `JSONResponse` subclass with a `default` handler that appends `Z` to naive datetimes. This is applied once at the FastAPI app level and affects all responses globally.

Implementation approach: Override FastAPI's default `JSONResponse` with a custom class that uses `json.dumps` with a `default` handler for datetime serialization:

```python
import json
from datetime import datetime
from fastapi.responses import JSONResponse

class UTCDateTimeResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            default=self._default_serializer,
            ensure_ascii=False,
        ).encode("utf-8")

    @staticmethod
    def _default_serializer(obj):
        if isinstance(obj, datetime):
            s = obj.isoformat()
            if obj.tzinfo is None:
                s += "Z"
            return s
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
```

Set as the default response class on the FastAPI app: `app = FastAPI(default_response_class=UTCDateTimeResponse)`.

**Note**: This changes datetime serialization for ALL API responses globally. Confirmed that no existing frontend code compensates for missing timezone (the only relative-time formatter is `formatRelativeTime` in `DashboardPage.tsx` which will now work correctly).

**Files**:
- Modify: `src/beanbay/main.py` — add `UTCDateTimeResponse` class and set as `default_response_class`

**Verification**: Dashboard "Recent Brews" should show "Xm ago" (minutes, not hours) for recently created brews. Check that all API responses now include `Z` suffix on datetime fields (e.g., `curl /api/v1/brews?limit=1`).

---

## Bug 6: Campaigns not auto-created when brews are logged

**Severity**: Moderate — optimization campaigns page is empty even with 10 brews.

**Root cause**: Campaigns are only created via the Suggest button flow (`POST /optimize/campaigns`). The spec designed it this way, but the user expectation is that campaigns should exist for every (bean, brew_setup) combination that has brews.

**Design decision**: Idempotently create a campaign for the brew's `(bean_id, brew_setup_id)` whenever a brew is saved. The campaign POST endpoint is already idempotent (returns 200 with existing campaign if one already exists for that combination).

**Fix**: In `create_brew()` at `brews.py`, after the brew is committed, call a shared helper that ensures a campaign exists for the brew's bean+setup combination. Extract the idempotent campaign-creation logic from the optimize router into a shared service function.

```python
# In create_brew(), after session.commit():
from beanbay.services.campaign import ensure_campaign
ensure_campaign(session, bean_id=bag.bean_id, brew_setup_id=payload.brew_setup_id)
```

The `ensure_campaign` function:
1. Checks if a Campaign row exists for `(bean_id, brew_setup_id)`
2. If not, creates one with default state (`phase="random"`, `measurement_count=0`)
3. Commits and returns the campaign

**Files**:
- Create: `src/beanbay/services/campaign.py` — `ensure_campaign(session, bean_id, brew_setup_id)` function
- Modify: `src/beanbay/routers/brews.py` — call `ensure_campaign` after brew commit in `create_brew()`
- Modify: `src/beanbay/routers/optimize.py` — refactor campaign creation in `POST /campaigns` to use the same `ensure_campaign` service
- Modify: `tests/integration/test_optimize_api.py` — add test that creating a brew auto-creates a campaign

**Verification**: Create a brew via the wizard. Navigate to `/optimize`. The campaign for that bean+setup should appear automatically.

---

---

## Bug 7: Bags not marked as opened when used in a brew

**Severity**: Minor — "Bags Unopened" dashboard stat is wrong.

**Root cause**: `create_brew()` in `brews.py` does not set `opened_at` on the bag when a brew is created with it. A bag used in a brew should be considered opened.

**Fix**: In `create_brew()`, after validating the bag exists, set `bag.opened_at` to the current time if it's still `None`:

```python
if bag.opened_at is None:
    bag.opened_at = datetime.now(timezone.utc)
    session.add(bag)
```

**Files**:
- Modify: `src/beanbay/routers/brews.py` — auto-set `bag.opened_at` in `create_brew()` if null

**Verification**: Create a brew with a fresh bag. Check `/beans/{id}` detail — the bag should show an `opened_at` date. Dashboard "Bags Unopened" should decrement.

---

## Dependencies Between Fixes

All 7 fixes are independent and can be implemented in any order. No fix depends on another.

---

## Out of Scope

- **Plotly chunk size warning**: 4.6MB Plotly bundle is inherent. Could be addressed with dynamic import in a future optimization pass.

# Phase 16: Cross-Brew Transfer Learning — Context

## Vision

When a user starts brewing a new coffee bean that shares characteristics with beans they've
already dialed in (same process and/or variety), BeanBay should leverage that prior knowledge to
give smarter first recommendations — instead of starting from random exploration.

The user experience: They add a new "Burundi Natural" coffee. BayBE notices they've already
dialed in two other "Natural" beans. The first recommendation for the new bean is informed by
those results, not a random starting point. The brew page shows a small badge: "Starting with
insights from 2 similar beans."

## What's Essential

1. **Similarity matching is simple and transparent:** process + variety match only. Not fuzzy
   matching. If both fields are present and match, they're similar. Missing metadata = no match.

2. **TaskParameter is the mechanism:** BayBE's TaskParameter adds a "bean_task" dimension to
   the search space. Similar beans are training tasks; the new bean is the active test task.
   This is the only correct way to do transfer learning with BayBE — do NOT try to pre-populate
   measurements directly (that would bias without uncertainty).

3. **Search space must match:** Transfer learning only works if training and test tasks use the
   same parameter columns (same brew method). A pour-over bean can't train an espresso campaign.
   Check method match before activating.

4. **Minimum data threshold:** Only use beans with at least 3 measurements as training sources.
   A bean with 1-2 shots doesn't have enough signal to contribute useful priors.

5. **Graceful fallback:** If no similar beans found (or <3 measurements), create a standard
   fresh campaign. No errors, no special handling — just the existing behavior.

6. **UI is informational only:** Show a badge/indicator when transfer learning was applied.
   "Insights from 2 similar beans" on the brew page. No configuration needed by the user.

## What's Out of Scope

- Fuzzy matching (e.g., "Ethiopian Washed" ~ "Ethiopian Natural") — too complex, too many edge cases
- Cross-method transfer (espresso campaign can't learn from pour-over)
- Manual control over which beans contribute
- Transfer learning for pour-over → espresso or vice versa
- Weighting training tasks by recency or quality

## Key Constraint: Campaign File Format

Transfer learning campaigns contain a `TaskParameter` in their search space. This changes the
campaign JSON format. A campaign created with transfer learning CANNOT have new measurements
added via `add_measurement` in the standard way (the measurement must include the `bean_task`
column). We handle this by:

- Creating the transfer learning campaign fresh (with TaskParameter)
- Saving it as the normal campaign JSON
- When adding subsequent measurements, always include `bean_task = {bean_id}` in the dict

The campaign key doesn't change — it's still `{bean_id}__{method}__{setup_id}`. The campaign
JSON itself is what determines whether it uses transfer learning.

## Architecture

```
SimilarityService (new)
  find_similar_beans(bean, method, db) -> list[SimilarBean]
  has_sufficient_data(bean_id, method, db) -> bool

TransferLearningService (new)
  build_transfer_campaign(bean, similar_beans, method, overrides) -> Campaign | None
    - Returns None if not enough training data
    - Returns Campaign with TaskParameter if transfer learning applies

OptimizerService (updated)
  get_or_create_campaign(campaign_key, overrides, method, bean=None, db=None)
    - If bean provided and no existing campaign: check for similar beans
    - If similar beans found: use TransferLearningService to seed campaign
    - Otherwise: standard fresh campaign
```

## Implementation Notes

- `SimilarityService` queries the DB — it needs a `db` session
- `OptimizerService` currently has no DB access — we add it as an optional param to
  `get_or_create_campaign` and `recommend` (only needed on first campaign creation)
- When transfer learning is used, store a metadata file `{campaign_key}.transfer` with:
  - `contributing_beans: [{"bean_id": ..., "name": ..., "process": ..., "variety": ...}]`
  - `measurement_count: N`
  This is read by the recommend route to show the UI indicator.
- The `.transfer` file is created once (when campaign is seeded) and never updated.

## What the User Sees

On the brew page, after getting a recommendation, if a `.transfer` file exists for the campaign:
- A subtle info badge: "✦ Seeded from N similar beans" (or "bean" if N=1)
- Clicking/tapping shows which beans: small tooltip or expandable row

After several shots, the new bean's own data dominates the model — the transfer learning
contribution fades naturally. The badge remains to show history.

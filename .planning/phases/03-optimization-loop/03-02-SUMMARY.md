---
phase: 03-optimization-loop
plan: 02
subsystem: ui
tags: [fastapi, jinja2, htmx, uuid, cookies, pytest]

# Dependency graph
requires:
  - phase: 03-optimization-loop
    provides: Brew loop routes (brew.py), bean management routes (beans.py), base templates
provides:
  - Fresh UUID per /brew/best visit — deduplication only blocks same-page double-submits
  - POST /beans/deactivate endpoint deleting active_bean_id cookie
  - Deselect button on bean detail page (active bean branch)
  - ✕ clear button in nav active-bean indicator
  - 5 new tests covering both UAT gap fixes
affects:
  - phase-4-shot-history
  - phase-5-insights

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fresh UUID per page view for deduplication scoping (prevents overzealous dedup)"
    - "POST endpoint before path-param route to avoid param capture (deactivate before /{bean_id})"
    - "Cookie deletion via response.delete_cookie() with Max-Age=0 verification in tests"

key-files:
  created: []
  modified:
    - app/routers/brew.py
    - app/templates/brew/best.html
    - app/routers/beans.py
    - app/templates/beans/detail.html
    - app/templates/base.html
    - tests/test_brew.py
    - tests/test_beans.py

key-decisions:
  - "UUID scoped to page visit (not stored in DB or state) — generated on each show_best call"
  - "Deactivate route placed BEFORE /{bean_id} wildcard to avoid FastAPI routing ambiguity"
  - "Test verifies Max-Age=0 header instead of following redirect (TestClient httpx doesn't evict manually-set cookies on server-sent expiry)"

patterns-established:
  - "Fresh UUID per page view: generate uuid4 in route, pass to template context"
  - "Cookie deletion test pattern: check Set-Cookie Max-Age=0 header, then manually clear client cookie"

# Metrics
duration: 2min
completed: 2026-02-22
---

# Phase 3 Plan 02: UAT Gap Fixes Summary

**Fresh UUID per `/brew/best` visit unblocks repeat-best loop; `POST /beans/deactivate` with nav and detail UI buttons closes active-bean clear UX gap**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-22T00:04:15Z
- **Completed:** 2026-02-22T00:06:35Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Fixed "Repeat Best not updating" UAT failure — each `/brew/best` visit now generates a fresh UUID, so "Brew Again" always creates a new measurement (deduplication only prevents same-page-load double-submits)
- Added `POST /beans/deactivate` endpoint that deletes the `active_bean_id` cookie, with htmx support (returns updated `_active_indicator.html` fragment)
- Added "Deselect" button on bean detail page active branch and "✕" clear button in nav bar
- 5 new tests: `test_show_best_recommendation_id_is_uuid`, `test_show_best_brew_again_creates_new_measurement`, `test_deactivate_bean`, `test_deactivate_bean_detail_shows_button`, `test_deactivate_bean_nav_shows_clear_button`

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix "Repeat Best" recommendation_id to use fresh UUID per visit** - `54d1103` (fix)
2. **Task 2: Add bean deactivate endpoint and UI buttons** - `7ba1c71` (feat)

**Plan metadata:** pending (docs commit)

## Files Created/Modified

- `app/routers/brew.py` — Added `import uuid`; `show_best` now generates `best_session_id = str(uuid.uuid4())` and passes it to template
- `app/templates/brew/best.html` — Changed `recommendation_id` hidden input from `best-{{ best.id }}` to `{{ best_session_id }}`
- `app/routers/beans.py` — Added `POST /beans/deactivate` route before `/{bean_id}` wildcard; htmx-aware (returns `_active_indicator.html` fragment or redirect)
- `app/templates/beans/detail.html` — Added "Deselect" button inline next to Active badge in active-bean branch
- `app/templates/base.html` — Added "✕" button form inline next to active bean name in nav
- `tests/test_brew.py` — 2 new tests for UUID deduplication fix
- `tests/test_beans.py` — 3 new tests for deactivate endpoint

## Decisions Made

- **UUID not stored in DB or app.state** — generated fresh each request in `show_best`. Simple and stateless; no cleanup needed.
- **Deactivate placed before `/{bean_id}`** — FastAPI routes match in registration order; putting `/deactivate` after the wildcard would cause it to be interpreted as a `bean_id` value.
- **Test cookie assertion strategy** — `httpx`/TestClient doesn't evict manually-set cookies from its internal jar when server sends `Max-Age=0`. Test validates the Set-Cookie header contains `Max-Age=0` directly, then manually calls `client.cookies.delete()` before checking the page. Faithfully tests the actual server behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test cookie deletion assertion strategy**

- **Found during:** Task 2 (`test_deactivate_bean`)
- **Issue:** Plan specified "assert `active_bean_id` cookie is deleted (follow redirect to `/beans`, check that 'No bean selected' appears)" — but TestClient's httpx jar keeps manually-set cookies even after server sends `Max-Age=0`, so the page still showed the active bean after redirect
- **Fix:** Changed assertion to check `Set-Cookie` header contains `Max-Age=0` directly (proving server sent deletion instruction), then manually call `client.cookies.delete("active_bean_id")` before checking the page for "No bean selected"
- **Files modified:** `tests/test_beans.py`
- **Verification:** `test_deactivate_bean` passes
- **Committed in:** `7ba1c71` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in test assertion, not production code)
**Impact on plan:** Test correctly validates server behavior. The deviation makes the test more precise — it verifies the actual contract (server sends Max-Age=0 deletion header) rather than relying on test-client cookie jar semantics.

## Issues Encountered

None — production code executed exactly as planned. Test assertion deviation auto-fixed inline.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 UAT gaps fully closed: Repeat Best now updates on each visit, user can deselect active bean from both detail page and nav
- All 65 tests pass (37 existing + 5 new brew/bean tests + 23 optimizer tests)
- Phase 3 is fully complete — ready to plan Phase 4: Shot History & Feedback Depth

---
*Phase: 03-optimization-loop*
*Completed: 2026-02-22*

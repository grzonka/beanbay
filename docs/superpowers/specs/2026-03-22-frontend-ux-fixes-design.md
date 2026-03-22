# Frontend UX Fixes Design Spec

## Overview

Four targeted UX fixes for the BeanBay React frontend addressing grind setting display, form consistency, table interaction patterns, and search responsiveness.

## Fix 1: Grind Setting Display with Validation + Range Hint

### Problem

The brew edit dialog uses a number input for `grind_setting` (canonical float, e.g. 142). Users think in display format ("2.3.4" for multi-ring grinders, "22" for single-ring). The brew wizard already uses `grind_setting_display` as a text field, but the edit form does not.

### Solution

**Files:**
- Create: `frontend/src/utils/grindValidation.ts`
- Modify: `frontend/src/features/brews/components/BrewStepParams.tsx`
- Modify: `frontend/src/features/brews/pages/BrewDetailPage.tsx` (brew edit dialog)

**Shared validation utility** (`grindValidation.ts`):

```typescript
interface RingConfig { label: string; min: number; max: number; step: number; }

function validateGrindDisplay(input: string, rings: RingConfig[]): string | null
```

- Parse input by `.` separator → segments
- Check segment count matches ring count
- Check each segment is numeric and within `[min, max]`
- Check step alignment (value % step === 0)
- Return error message string or `null` if valid

**Helper functions:**
- `getGrindRangeDisplay(rings: RingConfig[]): string` — returns e.g. "0.0.0 — 4.9.5" or "0 — 40"
- `getGrindPlaceholder(rings: RingConfig[]): string` — returns e.g. "e.g. 2.3.4" or "e.g. 22"

**Brew wizard step 2 (`BrewStepParams.tsx`):**
- Already uses text input for `grind_setting_display` — add validation
- Add `rings?: RingConfig[]` prop to `BrewStepParams`. Parent `BrewWizard` passes rings from the selected brew setup's grinder (fetched via the setup's `grinder_id` → grinder detail endpoint)
- Show `helperText` with range: "Range: 0.0.0 — 4.9.5"
- Show `error` + validation message when input is invalid
- Disable Next button if grind validation fails (in addition to dose required check)

**Brew edit dialog (`BrewDetailPage.tsx`):**
- Change from `<TextField type="number" grind_setting>` to `<TextField type="text" grind_setting_display>`
- Pre-populate with `brew.grind_setting_display` from BrewRead response
- Resolve grinder ring config: `BrewRead.brew_setup` only has `grinder_name`, not ring config. Fetch grinder detail via `GET /grinders/{grinder_id}` using `brew_setup.grinder_id` to get rings. Cache with TanStack Query.
- Same validation, range hint, and error display as wizard
- On submit: send `grind_setting_display` instead of `grind_setting`

## Fix 2: Hide `display_format` from Grinder Form

### Problem

The "Display Format" field in the grinder creation form shows "decimal" which is meaningless to users. The field is never used by any conversion logic — ring config drives everything.

### Solution

**Files:**
- Modify: `frontend/src/features/equipment/components/GrinderFormDialog.tsx`

- Remove the `display_format` TextField from the form UI
- Remove `displayFormat` state variable
- Always send `display_format: "decimal"` as a hardcoded default in the submit body
- Backend column removal is out of scope (separate backend task)

## Fix 3: Consistent Row Interaction

### Problem

Tables are inconsistent: some have edit/retire icon buttons per row, others use row click for navigation. Users don't know what to expect.

### Solution

**Universal rule:** Click any row = take the primary action. No inline icon buttons.

**DataTable changes** (`frontend/src/components/DataTable.tsx`):
- Add new optional prop: `onRowClick?: (row: T) => void`
- `onRowClick` and `detailPath` are mutually exclusive — `onRowClick` takes precedence if both are provided
- Set `cursor: 'pointer'` when either `detailPath` or `onRowClick` is set
- Wire `onRowClick` to DataGrid's `onRowClick` handler (call `params.row` callback)

**Pages with detail routes** (use existing `detailPath` — no changes):
- `BeansListPage.tsx` — row click → `/beans/:id` (already works)
- `BrewsListPage.tsx` — row click → `/brews/:id` (already works)
- `CuppingsListPage.tsx` — row click → `/cuppings/:id` (already works)

**Pages without detail routes** (use new `onRowClick` prop):
- `GrindersPage.tsx` — remove actions column, pass `onRowClick` to open edit dialog
- `BrewersPage.tsx` — remove actions column, pass `onRowClick` to open edit dialog
- `PapersPage.tsx` — remove actions column, pass `onRowClick` to open edit dialog
- `WatersPage.tsx` — remove actions column, pass `onRowClick` to open edit dialog
- `BrewSetupsPage.tsx` — remove actions column, pass `onRowClick` to open edit dialog
- `PeoplePage.tsx` — remove actions column, pass `onRowClick` to open edit dialog
- `LookupTab.tsx` — remove programmatically appended `columnsWithActions`, pass `onRowClick` to open edit dialog

**Retire button placement:**
- Add a "Retire" button inside the edit dialog for all entities that don't have detail pages
- Positioned in `DialogActions` next to Cancel/Save, left-aligned with `color="warning"`
- Opens the existing `ConfirmDialog` for confirmation

**Bags on bean detail page** (`BeanDetailPage.tsx`):
- Remove actions column from bags DataGrid
- Row click opens BagFormDialog for editing
- Add "Retire" button inside BagFormDialog

**Ratings on bean detail page:**
- Row click already navigates to `/bean-ratings/:id` — no changes needed

## Fix 4: Live Debounced Search

### Problem

DataTable search only fires on Enter key or input blur. Users expect live filtering as they type.

### Solution

**Files:**
- Modify: `frontend/src/components/DataTable.tsx`

- Replace Enter/blur event handlers with a debounced `useEffect`
- When `searchInput` changes, wait 300ms then call `onSearchChange(searchInput)`
- Use a simple `setTimeout`/`clearTimeout` pattern (no external debounce library needed)
- Remove the `onKeyDown` Enter handler and `onBlur` handler for search
- Keep the `searchInput` local state for controlled input
- The URL params update after the 300ms debounce, triggering the API refetch via TanStack Query

```typescript
useEffect(() => {
  const timer = setTimeout(() => {
    onSearchChange?.(searchInput);
  }, 300);
  return () => clearTimeout(timer);
}, [searchInput, onSearchChange]);
```

# BeanBay Frontend Design Spec

## Overview

React SPA for the BeanBay FastAPI REST API. Mobile-first responsive design with dual theme support. Full CRUD for all entities, stats dashboard, and a structure ready to extend with BayBE optimization features.

**Location:** `frontend/` directory in the BeanBay monorepo, adjacent to `src/` (backend).

## Tech Stack

| Package | Version | Purpose |
|---|---|---|
| `react` + `react-dom` | ^19 | UI framework |
| `vite` | ^6 | Build tool + dev server |
| `typescript` | ^5.7 | Type safety |
| `@mui/material` | ^6 | Component library |
| `@mui/icons-material` | ^6 | Icon set |
| `@emotion/react` + `@emotion/styled` | ^11 | MUI styling engine |
| `@mui/x-data-grid` | ^7 (Community) | Data tables |
| `axios` | ^1 | HTTP client |
| `@tanstack/react-query` | ^5 | Data fetching, caching, mutations |
| `@tanstack/react-query-devtools` | ^5 | Dev tools (dev only) |
| `react-router` | ^7 | Client-side routing |
| `recharts` | ^2 | Charts (radar, bar) |
| `openapi-typescript` | ^7 | TS type generation from OpenAPI spec (dev) |
| `eslint` + `prettier` | latest | Code quality (dev) |

## Project Structure

```
frontend/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
├── public/
├── scripts/
│   └── generate-types.sh          # curl openapi.json | npx openapi-typescript
└── src/
    ├── main.tsx                    # Entry: React root, providers
    ├── App.tsx                     # Router + Layout
    ├── api/
    │   ├── client.ts              # Axios instance (baseURL, interceptors)
    │   └── types.ts               # Generated from OpenAPI (committed)
    ├── theme/
    │   ├── espressoDark.ts        # MUI createTheme() — dark palette
    │   ├── craftLight.ts          # MUI createTheme() — light palette
    │   ├── ThemeContext.tsx        # Toggle context + localStorage persistence
    │   └── common.ts              # Shared typography, shape, component overrides
    ├── layouts/
    │   └── AppLayout.tsx          # App bar + sidebar + main content + FAB
    ├── components/                # Shared/reusable
    │   ├── DataTable.tsx          # Wrapper around MUI DataGrid with defaults
    │   ├── AutocompleteCreate.tsx # Autocomplete + "Create new..." inline dialog
    │   ├── ConfirmDialog.tsx      # Reusable delete/retire confirmation
    │   ├── PageHeader.tsx         # Title + breadcrumb + action buttons
    │   ├── StatsCard.tsx          # Dashboard stat widget
    │   ├── TasteRadar.tsx         # Recharts radar chart for taste profiles
    │   └── FlavorTagSelect.tsx    # Multi-select autocomplete for flavor tags
    ├── features/
    │   ├── dashboard/
    │   │   ├── DashboardPage.tsx
    │   │   └── hooks.ts           # useBrewStats, useBeanStats, useTasteStats, ...
    │   ├── beans/
    │   │   ├── pages/             # BeansListPage, BeanDetailPage
    │   │   ├── components/        # BeanForm, BagForm, BagDialog
    │   │   └── hooks.ts           # useBeans, useBean, useCreateBean, useBags, ...
    │   ├── brews/
    │   │   ├── pages/             # BrewsListPage, BrewDetailPage
    │   │   ├── components/        # BrewWizard, BrewStepSetup, BrewStepParams, BrewStepTaste
    │   │   └── hooks.ts
    │   ├── equipment/
    │   │   ├── pages/             # GrindersPage, BrewersPage, PapersPage, WatersPage
    │   │   ├── components/        # GrinderForm, BrewerForm, PaperForm, WaterForm
    │   │   └── hooks.ts
    │   ├── brew-setups/
    │   │   ├── pages/
    │   │   ├── components/
    │   │   └── hooks.ts
    │   ├── cuppings/
    │   │   ├── pages/             # CuppingsListPage, CuppingDetailPage
    │   │   ├── components/        # CuppingForm, CuppingScoreCard
    │   │   └── hooks.ts
    │   ├── ratings/
    │   │   ├── pages/             # RatingDetailPage
    │   │   ├── components/        # RatingForm, BeanTasteForm (used inline on BeanDetailPage)
    │   │   └── hooks.ts
    │   ├── people/
    │   │   ├── pages/
    │   │   ├── components/
    │   │   └── hooks.ts
    │   └── settings/
    │       ├── LookupsPage.tsx     # Tabbed: all 9 lookup types
    │       └── hooks.ts
    └── utils/
        └── pagination.ts          # Shared pagination/sort state helpers
```

## Routing

All routes derived from the OpenAPI spec at `http://localhost:8000/openapi.json`.

```
/                              → DashboardPage
/beans                         → BeansListPage
/beans/:beanId                 → BeanDetailPage (bags + ratings inline)
/bags                          → BagsListPage (all bags, cross-bean)
/brews                         → BrewsListPage
/brews/new                     → BrewWizard (stepper)
/brews/:brewId                 → BrewDetailPage (taste inline)
/equipment/grinders            → GrindersPage
/equipment/brewers             → BrewersPage
/equipment/papers              → PapersPage
/equipment/waters              → WatersPage
/brew-setups                   → BrewSetupsPage
/cuppings                      → CuppingsListPage
/cuppings/:cuppingId           → CuppingDetailPage
/bean-ratings/:ratingId        → RatingDetailPage (taste inline)
/people                        → PeoplePage
/settings/lookups              → LookupsPage (tabbed)
```

## Navigation

**Layout:** Top app bar + collapsible sidebar (desktop), hamburger drawer (mobile).

**App bar contents:** Hamburger toggle (mobile), page title, theme toggle (sun/moon), person selector (if multiple people exist).

**Sidebar groups:**

```
CORE
  Dashboard              /
  Beans                  /beans
  Bags                   /bags
  Brews                  /brews

EQUIPMENT
  Grinders               /equipment/grinders
  Brewers                /equipment/brewers
  Papers                 /equipment/papers
  Waters                 /equipment/waters
  Brew Setups            /brew-setups

EVALUATION
  Cuppings               /cuppings

MANAGE
  People                 /people
  Lookups                /settings/lookups
```

**Sidebar behavior:**
- Desktop: persistent, 240px wide, collapsible to icon-only (64px)
- Mobile: hidden, opens as full-width MUI `Drawer` via hamburger in app bar
- Active route highlighted

**FAB:** Floating action button fixed bottom-right on all pages. Labeled "Log a Brew", navigates to `/brews/new`. Most frequent action always one tap away.

## Theme System

Dual mode using MUI `ThemeProvider` + `createTheme()`. User toggleable, persisted to `localStorage` key `beanbay-theme`. Default: Espresso Dark.

### Shared (`theme/common.ts`)

- **Typography:** Distinctive display font for headings (e.g., DM Serif Display), clean body font (e.g., DM Sans). Imported via Google Fonts.
- **Shape:** `borderRadius: 8` globally
- **Component overrides:** Consistent DataGrid density, button sizing, input styling across both themes
- **Breakpoints:** Default MUI (`xs:0, sm:600, md:900, lg:1200, xl:1536`)

### Espresso Dark (`theme/espressoDark.ts`)

| Token | Value | Usage |
|---|---|---|
| background.default | `#1a1210` | Page background |
| background.paper | `#2d1f1a` | Cards, surfaces |
| primary.main | `#c4956a` | Warm copper — buttons, active states |
| secondary.main | `#d4a574` | Lighter gold — accents |
| text.primary | `#e8dcc8` | Warm cream — body text |
| error/success/warning | Muted warm variants | Fit the palette |

### Craft Light (`theme/craftLight.ts`)

| Token | Value | Usage |
|---|---|---|
| background.default | `#faf8f5` | Warm off-white page background |
| background.paper | `#ffffff` | Cards, surfaces |
| primary.main | `#8b5e3c` | Rich brown — buttons, active states |
| secondary.main | `#6b4c2a` | Darker accent |
| text.primary | `#3d2b22` | Dark coffee — body text |
| divider | `#e0d6ca` | Warm gray borders |

### `ThemeContext.tsx`

- React context providing `mode: 'dark' | 'light'` and `toggleTheme()`
- Wraps MUI `ThemeProvider` with the active theme object
- Toggle button in app bar (sun/moon icon swap)

## Data Layer

### Axios Client (`api/client.ts`)

- Base URL from `VITE_API_BASE_URL` env var (default: empty, uses Vite proxy in dev)
- Response interceptor for global error handling (triggers Snackbar notifications)
- Request/response types from `openapi-typescript` generated `api/types.ts`

### TanStack Query

- `QueryClient` defaults: `staleTime: 30_000`, `gcTime: 300_000`
- Devtools enabled in development mode

**Hook pattern (consistent across all features):**

```typescript
// Example: features/beans/hooks.ts
export const useBeans = (params: BeanListParams) =>
  useQuery({ queryKey: ['beans', params], queryFn: ... })

export const useBean = (id: string) =>
  useQuery({ queryKey: ['beans', id], queryFn: ... })

export const useCreateBean = () =>
  useMutation({ mutationFn: ..., onSuccess: () => invalidate(['beans']) })

export const useUpdateBean = () =>
  useMutation({ mutationFn: ..., onSuccess: () => invalidate(['beans']) })

export const useDeleteBean = () =>
  useMutation({ mutationFn: ..., onSuccess: () => invalidate(['beans']) })
```

### Cache Invalidation

- Create/update/delete mutations invalidate the entity's list query key
- Cross-entity invalidation: deleting a bag invalidates `['beans', beanId]`, brew mutations invalidate `['stats', 'brews']` and `['stats', 'taste']`, etc.
- Stats queries keyed as `['stats', 'brews']`, `['stats', 'beans']`, `['stats', 'taste']`, `['stats', 'equipment']`, `['stats', 'cuppings']`

### Pagination

- State stored in URL search params (`?offset=0&limit=25&sort_by=created_at&sort_dir=desc`) via React Router `useSearchParams`
- Matches the backend's `offset`/`limit` pagination model (not page-based). DataGrid's page index is derived: `page = offset / limit`.
- DataGrid pagination/sorting wired to URL params — bookmarkable, back-button friendly
- Shared `usePaginationParams()` hook in `utils/pagination.ts` handles DataGrid page ↔ API offset conversion

### Type Generation

```bash
# scripts/generate-types.sh
curl -s http://localhost:8000/openapi.json | npx openapi-typescript /dev/stdin -o src/api/types.ts
```

Run manually or via `npm run generate-types`. Output committed to git so builds don't require a running backend.

## Shared Components

### `DataTable<T>`

Wrapper around MUI DataGrid Community with BeanBay defaults.

- **Props:** `columns`, `queryKey`, `fetchFn`, plus pagination/sort from URL params
- **Built-in:** Loading skeletons, empty state, "Show retired" toggle, search input (`q` param)
- **Row click:** Navigates to entity detail page
- **Responsive:** Hides low-priority columns on mobile via `colDef.minWidth` breakpoints

### `AutocompleteCreate`

Reusable FK/M2M picker with inline entity creation.

- **Props:** `label`, `queryKey`, `fetchFn`, `createFn`, `multiple` (for M2M), `renderCreateForm`
- Searches existing items via API `?q=` param
- Last option: "+ Create new {label}..." opens inline `Dialog` with the provided form component
- On create success: auto-selects the new item, invalidates the lookup query cache

### `FlavorTagSelect`

Specialized multi-select for flavor tags. Extends `AutocompleteCreate` with `multiple=true`. Displays selected tags as MUI Chips with coffee-themed colors. Used in BrewTaste, BeanTaste, and Cupping forms.

### `ConfirmDialog`

Reusable confirmation dialog for destructive actions.

- **Props:** `title`, `message`, `onConfirm`, `variant` (`'retire'` | `'delete'`)
- Shows dependency warning when API returns 409 Conflict

### `PageHeader`

Consistent page title bar.

- **Props:** `title`, `breadcrumbs`, `actions` (slot for action buttons)
- Responsive: stacks vertically on mobile

### `StatsCard`

Dashboard metric widget.

- **Props:** `label`, `value`, `icon`, `trend` (optional)
- Shows MUI Skeleton while TanStack Query `isLoading`

### `TasteRadar`

Recharts `RadarChart` for taste profiles. Adapts axes to context:

- **BrewTaste:** acidity, sweetness, body, bitterness, balance, aftertaste (0-10)
- **BeanTaste:** acidity, sweetness, body, complexity, aroma, clean_cup (0-10)
- **Cupping:** dry_fragrance, wet_aroma, brightness, flavor, body, finish, sweetness, clean_cup, complexity, uniformity (0-9, SCAA protocol)

## Feature Details

### Dashboard (`/`)

- 5 stats card groups, each wired to an independent stats endpoint via its own `useQuery` hook — loads and caches independently
- **Brew stats:** total brews, brews this week, avg taste, failure rate
- **Bean stats:** total beans, active bags, top roasters
- **Taste stats:** best score (linked to brew/bean), sensory averages as mini TasteRadar
- **Equipment stats:** counts, most-used grinder/brewer
- **Cupping stats:** total cuppings, avg total score
- **Recent brews** list below stats: last 5 via `GET /brews?limit=5&sort_by=brewed_at&sort_dir=desc`

### Beans (`/beans`, `/beans/:beanId`)

**List page:**
- DataGrid: name, roaster, mix type, use type, roast degree, bag count
- Filters: roaster (autocomplete), origin, process, variety, `include_retired` toggle

**Detail page:**
- Bean info card with all fields
- Inline bags DataGrid (scoped to this bean)
- Linked ratings section
- "Add Bag" button

**Bean form fields:**
- `name` (required), `roaster` (AutocompleteCreate), `roast_degree` (slider 0-10), `bean_mix_type` (select: single_origin/blend/unknown), `bean_use_type` (select: filter/espresso/omni), `decaf` (toggle), `url`, `ean`, `notes`
- M2M: `origins` (AutocompleteCreate multi, using `OriginWithPercentage` format — `origin_id` + optional `percentage` for blends), `processes` (AutocompleteCreate multi), `varieties` (AutocompleteCreate multi), `flavor_tags` (FlavorTagSelect)

### Bags (`/bags`, inline on bean detail)

**List page:**
- DataGrid columns from `BagRead`: roast_date, weight, price, is_preground, opened_at, frozen_at. Note: `BagRead` has `bean_id` but not `bean_name` — the list needs a client-side lookup join (fetch beans once, map by ID) or a backend enhancement to denormalize `bean_name` into `BagRead`.
- Filters: `bean_id`, `is_preground`, `opened_after`, `include_retired` (matching API query params)

**Form fields:**
- `weight` (required, grams), `roast_date`, `opened_at`, `bought_at`, `best_date`, `price`, `vendor` (AutocompleteCreate), `storage_type` (AutocompleteCreate), `is_preground` (toggle), `frozen_at`, `thawed_at`, `notes`

### Brews (`/brews`, `/brews/new`, `/brews/:brewId`)

**List page:**
- DataGrid columns from `BrewListRead`: bean_name, brew_method_name, person_name, dose, grind_setting_display, temperature, score, brewed_at, is_failed badge
- Filters: `bag_id`, `bean_id`, `brew_setup_id`, `person_id`, `brewed_after`, `brewed_before`, `include_retired` (all matching API query params)

**Wizard — 3 steps:**

1. **Setup:** Bag picker (AutocompleteCreate, displays bean name), brew setup picker (AutocompleteCreate, displays equipment summary), person picker
2. **Parameters:** Grind setting (with display conversion from grinder's ring config), temperature, pressure, flow rate, dose (required), yield, pre-infusion time, total time, stop mode picker, is_failed toggle, notes, brewed_at datetime picker
3. **Taste (optional, skippable):** Score slider (0-10), acidity/sweetness/body/bitterness/balance/aftertaste sliders (0-10), notes, FlavorTagSelect. Live TasteRadar preview.

**Detail page:**
- All brew info displayed
- Taste section with TasteRadar + flavor tag chips
- Edit / delete actions

### Equipment

**Grinders (`/equipment/grinders`):**
- DataGrid: name, dial type
- Form: `name` (required, unique), `dial_type` (select: stepless/stepped), `display_format`, `rings` (dynamic list of `RingConfig`: label, min, max, step)

**Brewers (`/equipment/brewers`):**
- DataGrid: name, brew methods, capabilities summary
- Form: `name` (required, unique), capability enums (temp_control_type, preinfusion_type, pressure_control_type, flow_control_type), ranges (temp min/max/step, pressure min/max, preinfusion max time, saturation flow rate), `has_bloom` toggle, brew methods M2M (AutocompleteCreate), stop modes M2M (AutocompleteCreate). Grouped into collapsible sections.

**Papers (`/equipment/papers`):**
- DataGrid: name, notes
- Form: `name` (required, unique), `notes`

**Waters (`/equipment/waters`):**
- DataGrid: name, mineral count
- Form: `name` (required, unique), `notes`, `minerals` (dynamic list of mineral_name + ppm pairs)

### Brew Setups (`/brew-setups`)

- DataGrid: name, brew method, grinder, brewer, paper, water
- Form: `name`, `brew_method` (AutocompleteCreate, required), `grinder` / `brewer` / `paper` / `water` (all AutocompleteCreate, optional)

### Cuppings (`/cuppings`, `/cuppings/:cuppingId`)

**List page:**
- DataGrid columns from `CuppingRead`: total_score, cupped_at. Note: `CuppingRead` has `bag_id` and `person_id` but no denormalized names — needs client-side lookup join (fetch bags+beans+people, map by ID) or backend enhancement.

**Form fields:**
- `bag` (AutocompleteCreate, required), `person` (AutocompleteCreate, required), `cupped_at` (datetime)
- 10 SCAA score sliders (0-9): dry_fragrance, wet_aroma, brightness, flavor, body, finish, sweetness, clean_cup, complexity, uniformity
- `cuppers_correction` (number, can be negative), `total_score` (0-100 SCAA scale; auto-calculated as sum of 10 axes × multiplier + cuppers_correction, with manual override option)
- `notes`, `flavor_tags` (FlavorTagSelect)

**Detail page:**
- Score breakdown card with all 10 axes
- TasteRadar (SCAA axes)
- Flavor tag chips

### Ratings (inline on bean detail + `/bean-ratings/:ratingId`)

Ratings have no standalone list endpoint — they are scoped to a bean via `GET /api/v1/beans/{bean_id}/ratings`. Shown inline on the BeanDetailPage as a DataGrid (bean name, person, rated_at, taste score).

**Create form (append-only, no edit on rating):**
- Created via `POST /api/v1/beans/{bean_id}/ratings` from the BeanDetailPage
- `person` picker (required)
- Inline taste: score (0-10), acidity/sweetness/body/complexity/aroma/clean_cup sliders (0-10), notes, FlavorTagSelect

**Detail page (`/bean-ratings/:ratingId`):**
- TasteRadar + flavor tag chips
- Taste sub-resource is editable (PATCH via `/bean-ratings/{rating_id}/taste`)

### People (`/people`)

- DataGrid: name, is_default badge
- **Create form:** `name` (required) only — `is_default` is not accepted on `PersonCreate`
- **Edit form:** `name`, `is_default` toggle — `is_default` is only available on `PersonUpdate`
- Backend auto-unsets previous default when setting a new one

### Lookups (`/settings/lookups`)

Single page with MUI Tabs — one tab per lookup type:

| Tab | Entity | Extra Fields |
|---|---|---|
| Flavor Tags | FlavorTag | — |
| Origins | Origin | country, region |
| Roasters | Roaster | — |
| Process Methods | ProcessMethod | category (enum) |
| Bean Varieties | BeanVariety | species (enum) |
| Brew Methods | BrewMethod | — |
| Stop Modes | StopMode | — |
| Vendors | Vendor | url, location, notes |
| Storage Types | StorageType | — |

Each tab: DataGrid with name + extra fields, "Show retired" toggle, row click opens edit dialog, "Add" button opens create dialog.

## Error Handling & UX

### API Errors

- Axios response interceptor catches errors globally
- **4xx:** MUI Snackbar with error message from response body
- **409 Conflict:** ConfirmDialog shows dependency information
- **422 Validation:** Map FastAPI `detail[].loc` to form field names, highlight invalid fields inline
- **5xx / network errors:** Snackbar: "Something went wrong, please try again"

### Loading States

- TanStack Query `isLoading` → MUI Skeleton placeholders (not spinners)
- DataGrid built-in loading overlay
- Stats cards shimmer independently

### Optimistic Updates

Used sparingly — only for low-risk UI actions (filter toggles, theme switching). All data mutations use standard cache invalidation to avoid stale state from complex entity relationships.

### Empty States

- No data (first-time user): Illustration + call-to-action ("Add your first bean", "Log your first brew")
- No filter results: "No results. Try adjusting your filters."

### Toast Notifications

- **Success:** "Bean created", "Brew logged" — auto-dismiss 3s
- **Error:** Persists until dismissed
- **Position:** Bottom-center (mobile), bottom-left (desktop) — avoids FAB overlap

### Form UX

- Unsaved changes warning on navigation via React Router `useBlocker`
- Controlled components with local React state, submitted via TanStack mutation
- Brew wizard preserves state across steps in local React state (not URL)

## Build & Dev

### Dev Workflow

```bash
npm run dev              # Vite dev server with HMR, proxies /api to FastAPI
npm run generate-types   # Regenerate src/api/types.ts from running backend
npm run build            # Production build to dist/
npm run lint             # ESLint
npm run format           # Prettier
```

### Vite Config

- **Proxy:** `/api` → `http://localhost:8000` (avoids CORS in development)
- **Alias:** `@/` → `src/` for clean imports

### Environment Variables

- `VITE_API_BASE_URL` — Override API base URL. Default: empty (uses Vite proxy in dev, same-origin in prod)

### Production

- `vite build` produces static `dist/` folder
- Can be served by FastAPI via `StaticFiles` mount, or independently via nginx/caddy
- Pure SPA, no SSR required

## Future Extensibility

The feature-based module structure is designed to accommodate future BayBE optimization features:

- New `features/optimize/` module for recommendation UI
- New `features/insights/` module for parameter maps and convergence charts
- New sidebar group "OPTIMIZE" between EVALUATION and MANAGE
- Stats endpoints already provide the data foundation
- Recharts handles any visualization needs (heatmaps, scatter plots, time series)

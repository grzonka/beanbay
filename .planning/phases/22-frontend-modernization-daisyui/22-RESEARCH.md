# Research: Phase 22 — Frontend Modernization (daisyUI)

**Phase:** 22 — Frontend Modernization — daisyUI
**Researched:** 2026-02-24

## 1. Tailwind CSS Integration Strategy

### The Problem
BeanBay's stack philosophy is "no Node.js toolchain." Tailwind CSS traditionally requires Node.js for its build process. Three options exist:

### Option A: Tailwind Standalone CLI (RECOMMENDED)
Tailwind v4 ships a **standalone CLI binary** — a single executable with no Node.js dependency. Download from GitHub releases for the target platform.

**How it works:**
1. Download `tailwindcss` binary (linux-x64 for Docker, darwin-arm64 for local dev)
2. Create an input CSS file with `@import "tailwindcss"` and plugin references
3. Run: `./tailwindcss -i input.css -o output.css --minify`
4. The binary scans template files for class names and generates only the CSS used

**daisyUI v5 standalone support:**
- Download `daisyui.mjs` and `daisyui-theme.mjs` from daisyUI GitHub releases
- Place alongside the Tailwind binary
- Input CSS references them: `@plugin "./daisyui.mjs"`

**Pros:** No Node.js needed. Full Tailwind features. Tree-shaking (only used CSS). Works in Docker.
**Cons:** Extra build step. Need to download binary per platform. Watch mode needed for dev.

### Option B: CDN (Simpler but Limited)
```html
<link href="https://cdn.jsdelivr.net/npm/daisyui@5" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/daisyui@5/themes.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
```

**Pros:** Zero build step. Instant setup.
**Cons:** No tree-shaking (full CSS bundle). Browser-side compilation. Some daisyUI features unavailable (e.g., `is-drawer-open` variants). Slower page load. Not production-grade.

### Option C: Pre-built CSS (Hybrid)
Use CDN during development, then switch to standalone CLI for production builds in Docker.

**Recommendation: Option A (Standalone CLI)**
- Aligns with "no Node.js" philosophy
- Production-quality output (tree-shaken, minified)
- Docker integration is clean (download binary in builder stage)
- Dev workflow: run CLI in watch mode alongside uvicorn

## 2. daisyUI Setup

### Installation (Standalone CLI approach)

**Input CSS file (`app/static/css/input.css`):**
```css
@import "tailwindcss";
@plugin "./daisyui.mjs";

@theme {
  --color-coffee-dark: oklch(24% 0.023 329.708);
}
```

**Build command:**
```bash
./tailwindcss -i app/static/css/input.css -o app/static/css/main.css --minify
```

### Theme Configuration

Activate coffee theme on `<html>` element:
```html
<html lang="en" data-theme="coffee">
```

### Key Component Classes

| Current BeanBay | daisyUI Equivalent |
|---|---|
| `.btn .btn-primary` | `btn btn-primary` |
| `.btn .btn-secondary` | `btn btn-ghost` or `btn btn-outline` |
| `.btn .btn-danger` | `btn btn-error` |
| `.card` | `card bg-base-200` + `card-body` wrapper |
| `.form-input` | `input input-bordered` |
| `.form-select` | `select select-bordered` |
| `.badge` | `badge` |
| `.nav` | `navbar bg-base-200` |
| `.nav-drawer` | `drawer` component (checkbox-based) |
| `.modal` (dialog) | `modal` + `modal-box` (uses native `<dialog>`) |
| `.table` | `table` |
| `.alert` | `alert` |
| Range sliders | `range range-primary` |
| Toggle switches | `toggle` |

### daisyUI Drawer Pattern (replaces custom drawer)

```html
<div class="drawer lg:drawer-open">
  <input id="drawer-toggle" type="checkbox" class="drawer-toggle" />
  <div class="drawer-content">
    <!-- Navbar with hamburger -->
    <div class="navbar bg-base-200 lg:hidden">
      <label for="drawer-toggle" class="btn btn-ghost drawer-button">
        <svg><!-- hamburger icon --></svg>
      </label>
      <a class="btn btn-ghost text-xl">BeanBay</a>
    </div>
    <!-- Page content -->
    <main>{% block content %}{% endblock %}</main>
  </div>
  <div class="drawer-side">
    <label for="drawer-toggle" class="drawer-overlay"></label>
    <ul class="menu bg-base-200 min-h-full w-64 p-4">
      <li><a href="/brew">Let's Brew</a></li>
      <!-- ... -->
    </ul>
  </div>
</div>
```

**Key insight:** daisyUI drawer uses a hidden checkbox for state — NO JavaScript needed for open/close. The `lg:drawer-open` class makes it permanently visible on desktop. This replaces the custom JS toggle code in current `base.html`.

### daisyUI Modal Pattern (replaces custom dialog)

```html
<dialog id="shot-modal" class="modal">
  <div class="modal-box">
    <h3 class="text-lg font-bold">Shot Details</h3>
    <p>Content...</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn">Close</button>
      </form>
    </div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

Uses native `<dialog>` element — same pattern the codebase already uses for `_shot_modal.html`.

## 3. htmx Compatibility

### Assessment: Excellent Compatibility

daisyUI v5 components are **almost entirely CSS-only** (class-based). No JavaScript framework dependency. This means htmx DOM swapping won't break component state.

**Safe patterns:**
- **Drawer:** Checkbox state lives outside `drawer-content`. htmx swapping content inside `drawer-content` won't affect drawer open/close state.
- **Modal:** Native `<dialog>` element. htmx can swap content inside `modal-box` freely.
- **Dropdown:** Uses CSS `:focus` or `<details>` element — no JS state.
- **Forms:** Pure CSS classes on inputs/selects. htmx form submissions work normally.
- **Tables, cards, badges, alerts:** Pure CSS — zero interaction concerns.

**One gotcha:**
- `is-drawer-open:` and `is-drawer-close:` variant classes (for conditional styling based on drawer state) are NOT available in CDN mode. With standalone CLI they work fine.

### htmx + daisyUI Integration Page
daisyUI has an official integration page for htmx. Key recommendation: use standard htmx attributes (`hx-get`, `hx-swap`, `hx-target`) with daisyUI's class-based components — they "just work."

## 4. Migration Strategy

### Recommended: Component-First, Then Page-by-Page

**Phase 1: Infrastructure (base.html + CSS build pipeline)**
- Set up Tailwind standalone CLI + daisyUI
- Rewrite `base.html` with daisyUI drawer/navbar layout
- This affects ALL pages at once — nav, layout, colors all change

**Phase 2: Shared components (cards, buttons, forms, badges, modals)**
- Update partial templates that are reused across pages
- Cards: `_bean_card.html`, `_grinder_card.html`, `_brewer_card.html`, etc.
- Forms: `_grinder_form.html`, `_brewer_form.html`, etc.
- Modals: `_shot_modal.html`, `_shot_edit.html`

**Phase 3: Page templates (one section at a time)**
- Beans pages (list, detail)
- Brew pages (index, recommend, manual, best, partials)
- Equipment pages (index, wizard)
- History pages (index, shot_list, filter_panel)
- Insights/Analytics pages

### Key Migration Rules:
1. **Don't mix old and new CSS.** Once base.html switches to daisyUI, the old main.css custom component styles should be removed. Keep only layout-specific overrides.
2. **Preserve all htmx attributes.** The migration is CSS-only — `hx-get`, `hx-post`, `hx-swap`, `hx-target`, `hx-trigger` attributes stay unchanged.
3. **Preserve all Jinja2 logic.** Template variables, loops, conditionals stay the same — only HTML classes change.
4. **Test each page after migration.** Functional behavior must be identical.

## 5. Docker Integration

### Build Pipeline Addition

```dockerfile
# Stage 1: CSS Builder
FROM debian:bookworm-slim AS css-builder
WORKDIR /build

# Download Tailwind standalone CLI + daisyUI plugin
RUN apt-get update && apt-get install -y curl && \
    curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 && \
    chmod +x tailwindcss-linux-x64 && \
    curl -sLO https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.mjs && \
    curl -sLO https://github.com/saadeghi/daisyui/releases/latest/download/daisyui-theme.mjs

# Copy templates + input CSS (for class scanning)
COPY app/templates/ ./app/templates/
COPY app/static/css/input.css ./app/static/css/input.css

# Build CSS
RUN ./tailwindcss-linux-x64 -i app/static/css/input.css -o app/static/css/main.css --minify

# Stage 2: Python Builder (existing)
FROM python:3.11-slim AS builder
# ... existing Python build ...

# Stage 3: Runtime (existing, with CSS from stage 1)
FROM python:3.11-slim AS runtime
# ... existing setup ...
COPY --from=css-builder /build/app/static/css/main.css ./app/static/css/main.css
```

### Local Development

For local dev, download the platform-specific Tailwind binary and run in watch mode:

```bash
# One-time setup
curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-macos-arm64
chmod +x tailwindcss-macos-arm64

# Dev watch mode (run alongside uvicorn)
./tailwindcss-macos-arm64 -i app/static/css/input.css -o app/static/css/main.css --watch
```

A Makefile target or shell script can automate this.

## 6. Coffee Theme Analysis

### daisyUI Coffee Theme Colors (from source)

| Variable | Value | Visual |
|---|---|---|
| `base-100` | `oklch(24% 0.023 329.708)` | Dark with slight purple/mauve |
| `base-200` | (auto-derived, darker) | Darker background |
| `base-300` | (auto-derived, darkest) | Darkest background |
| `base-content` | `oklch(72.354% 0.092 79.129)` | Warm tan/cream text |
| `primary` | `oklch(71.996% 0.123 62.756)` | Warm amber/orange |
| `secondary` | (theme-defined) | Complementary |
| `accent` | (theme-defined) | Accent color |

### Comparison with Current BeanBay Colors

| Element | Current BeanBay | daisyUI Coffee | Match? |
|---|---|---|---|
| Background | `#1a1612` (warm dark brown) | `oklch(24% 0.023 329.708)` (dark mauve) | Close but not exact — coffee theme has slight purple tint |
| Card bg | `#332d28` (warm brown) | Auto-derived `base-200` | Similar warmth |
| Text | `#f0e6d8` (warm cream) | `oklch(72.354% 0.092 79.129)` (warm tan) | Good match |
| Accent | `#c87941` (amber/orange) | `oklch(71.996% 0.123 62.756)` (warm amber) | Excellent match |
| Border | `#4a4038` (warm gray-brown) | Auto-derived from base | Similar |

### Customization

The coffee theme is a strong starting point. If the purple tint in backgrounds is noticeable, it can be overridden:

```css
@plugin "daisyui/theme" {
  name: "beanbay";
  default: true;
  extends: "coffee";
  --color-base-100: oklch(22% 0.015 55); /* warmer brown, less purple */
}
```

**Recommendation:** Start with the stock coffee theme. If users notice the purple tint, create a `beanbay` theme that extends `coffee` with warmer base colors. The accent/primary colors are already an excellent match.

## 7. Common Pitfalls

### Pitfall 1: Forgetting `card-body` Wrapper
daisyUI cards require a `card-body` div for proper padding/spacing. Current `.card` class applies padding directly — migration must add the wrapper.

### Pitfall 2: Form Input Sizing
daisyUI inputs default to a standard size. For 48px+ touch targets, use `input-lg` or add Tailwind's `min-h-12` class.

### Pitfall 3: Tailwind Class Scanning
The standalone CLI scans files for class names. It must be configured to scan all `.html` template files. If a class is used dynamically (via Jinja2 variable), it won't be detected. Use `safelist` or ensure classes appear literally in templates.

### Pitfall 4: Chart.js Canvas Sizing
Tailwind's preflight resets can affect Chart.js canvas sizing. Ensure chart containers have explicit dimensions or use Chart.js's `responsive: true` + `maintainAspectRatio: false` options (already used in codebase).

### Pitfall 5: Custom Range Slider Styling
BeanBay uses range sliders extensively (flavor ratings). daisyUI's `range` component works well but doesn't show current value. The existing JS for displaying slider values must be preserved.

### Pitfall 6: htmx Loading Indicators
Current CSS has custom `.htmx-indicator` styling. daisyUI has a `loading` component (`loading-spinner`, `loading-dots`) that should replace custom spinner CSS.

### Pitfall 7: Dark Theme is Default
The coffee theme is dark by default. No need for a separate dark mode toggle — it's already dark. Light mode can be offered later via daisyUI's theme switcher.

## Summary

**Integration approach:** Tailwind v4 standalone CLI + daisyUI v5 standalone plugin files. No Node.js needed. Build step in Dockerfile (new CSS builder stage). Dev uses watch mode.

**Theme:** daisyUI's built-in `coffee` theme is a strong match for BeanBay's identity. Primary/accent colors align well. Base colors have slight purple tint vs current warm browns — acceptable, can be customized if needed.

**htmx compatibility:** Excellent. daisyUI is CSS-only. No conflicts with htmx DOM swapping.

**Migration scope:** 36 templates, ~1935 lines of CSS to replace. Drawer pattern changes from JS-toggle to checkbox-toggle. Modal pattern stays similar (both use `<dialog>`). All htmx and Jinja2 logic preserved — only CSS classes change.

**Risk:** Low. This is a styling-only change. No backend modifications. No data model changes. All functionality preserved.

---
*Researched: 2026-02-24 for Phase 22: Frontend Modernization — daisyUI*

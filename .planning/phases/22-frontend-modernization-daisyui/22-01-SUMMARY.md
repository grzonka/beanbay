---
phase: 22-frontend-modernization-daisyui
plan: "01"
subsystem: ui
tags: [tailwindcss, daisyui, css, docker, makefile, html, jinja2]

requires: []
provides:
  - Tailwind CSS v4 + daisyUI v5 input.css with all custom component layers
  - daisyUI drawer layout in base.html (coffee theme, checkbox-based, no JS)
  - CSS builder Docker stage (Tailwind standalone CLI, no Node.js)
  - Local dev Makefile targets (css, css-watch, tools/tailwindcss)
affects:
  - 22-02-PLAN.md (beans templates)
  - 22-03-PLAN.md (brew templates)
  - 22-04-PLAN.md (history/shots templates)
  - 22-05-PLAN.md (equipment templates)
  - 22-06-PLAN.md (analytics/insights templates)

tech-stack:
  added: [tailwindcss-v4-standalone, daisyui-v5]
  patterns: [daisyUI-drawer-checkbox, tailwind-custom-component-layer, multi-stage-docker-css-build]

key-files:
  created:
    - app/static/css/input.css
    - Makefile
  modified:
    - app/templates/base.html
    - Dockerfile
    - .gitignore

key-decisions:
  - "Tailwind standalone CLI (no Node.js) — downloaded binary in Docker Stage 0 css-builder"
  - "@plugin ./daisyui.mjs — daisyUI loaded as standalone .mjs plugin file, not npm package"
  - "Checkbox drawer pattern — daisyUI input[type=checkbox].drawer-toggle replaces entire JS toggle script"
  - "lg:drawer-open — desktop sidebar permanently visible via Tailwind modifier, no JS needed"
  - "app/static/css/main.css gitignored — it's a build artifact generated from input.css"
  - "Custom component layer in @layer components — preserves recipe-*, flavor-*, wizard-*, chart-*, stats-*, etc."

patterns-established:
  - "CSS build: ./tools/tailwindcss -i app/static/css/input.css -o app/static/css/main.css --minify"
  - "Docker CSS stage: FROM debian:bookworm-slim AS css-builder, curl tailwindcss + daisyui.mjs, compile"
  - "daisyUI theme: data-theme=coffee on <html> element activates coffee theme globally"

duration: 3min
completed: 2026-02-24
---

# Phase 22 Plan 01: Infrastructure + Base Layout Summary

**Tailwind CSS v4 + daisyUI v5 pipeline via standalone CLI with coffee-theme drawer layout in base.html — zero JS, no Node.js, 3-stage Docker build**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-02-24T00:37:11Z
- **Completed:** 2026-02-24T00:40:00Z
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments

- Created `app/static/css/input.css` — Tailwind entry point with `@import "tailwindcss"`, `@plugin "./daisyui.mjs"`, and full `@layer components` block preserving all custom CSS that has no daisyUI equivalent (recipe params, flavor sliders, wizard steps, chart container, etc.)
- Rewrote `base.html` with daisyUI drawer pattern: `data-theme="coffee"`, checkbox-based open/close, `lg:drawer-open` permanent desktop sidebar — **entire JS drawer toggle script removed**
- Added CSS builder as Docker Stage 0 (`debian:bookworm-slim`) — downloads Tailwind standalone binary + daisyUI plugin files, compiles minified CSS, no Node.js anywhere in the pipeline
- Created `Makefile` with `css`, `css-watch`, and `tools/tailwindcss` download targets for local macOS ARM dev

## Task Commits

1. **Task 1: Create input.css + update .gitignore** — `478aef5` (feat)
2. **Task 2: Rewrite base.html + Dockerfile + Makefile** — `722fa1c` (feat)

**Plan metadata:** (pending)

## Files Created/Modified

- `app/static/css/input.css` — Tailwind v4 entry point with daisyUI plugin + all custom component layers
- `app/templates/base.html` — daisyUI drawer layout, coffee theme, checkbox toggle, no JS drawer script
- `Dockerfile` — 3-stage build (css-builder → builder → runtime); Stage 0 compiles CSS without Node.js
- `Makefile` — `css` / `css-watch` targets + macOS ARM binary download
- `.gitignore` — `app/static/css/main.css` and `tools/` added as ignored build artifacts

## Decisions Made

- **Tailwind standalone CLI over npm**: Downloads a single binary in Docker, no Node.js, no package.json needed. Clean, minimal, fast.
- **@plugin ./daisyui.mjs**: daisyUI v5 ships as a standalone `.mjs` plugin file — placed alongside `input.css` at compile time (both in Docker and local dev).
- **Checkbox drawer**: `<input type="checkbox" class="drawer-toggle">` + `<label for="drawer-toggle">` pattern is pure CSS. The old JS IIFE (`classList.add('open')`, `body.style.overflow = 'hidden'`) was removed entirely.
- **main.css gitignored**: Generated build artifact; `input.css` is the source of truth. Existing `main.css` in repo will be deleted by git after this commit.
- **Custom component layer preserved**: ~30 component classes (recipe-params, flavor-slider, wizard-step, chart-container, etc.) have no daisyUI equivalent and are kept in `@layer components` inside `input.css`.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

To build CSS locally (macOS ARM):
```bash
make css        # downloads binary first time, then compiles
make css-watch  # watch mode for development
```

Docker build handles CSS automatically via Stage 0. No additional setup required.

## Next Phase Readiness

- Foundation complete — all subsequent Phase 22 plans can now restyle templates using daisyUI components
- **Phase 22 Plan 02** (beans templates): Can begin immediately; `base.html` provides the layout shell
- **Blocker**: `app/static/css/main.css` must be regenerated (via `make css` or `docker build`) before the app renders correctly — the old hand-rolled CSS is now gitignored

---
*Phase: 22-frontend-modernization-daisyui*
*Completed: 2026-02-24*

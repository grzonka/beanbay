# BeanBay v0.1.0 Roadmap — Release & Deploy

**Milestone:** v0.1.0 — Rebrand, clean up, and ship
**Goal:** Transform the v1 MVP into a properly branded, documented, and publicly deployable product called BeanBay.
**Phases:** 7-9 (continuing from v1)
**Estimated effort:** 3 phases, 5 plans

---

### Phase 7: Rebrand & Cleanup ✓

**Goal:** Rename BrewFlow to BeanBay across the entire codebase, remove legacy artifacts, and fix accumulated tech debt so the project is clean and consistent.

**Requirements:** BRAND-01, BRAND-02, CLEAN-01, CLEAN-02, DEBT-01, DEBT-02, DEBT-03, DEBT-04, REL-02

**Status:** Complete (2026-02-22)
**Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md — Rename BrewFlow to BeanBay in all code, templates, and tests
- [x] 07-02-PLAN.md — Fix all 5 tech debt items (dedup helper, persist recs, Alembic migration, error feedback, remove dead dir)

**Success criteria:**
- All references to "BrewFlow" or "brewflow" replaced with "BeanBay" / "beanbay"
- Legacy files removed (my_espresso.py, __marimo__/, dead app/routes/)
- Tech debt items resolved (shared helper, persistent recommendations, Alembic migration, error feedback)
- All 108+ tests pass with new naming

---

### Phase 8: Documentation & Release ✓

**Goal:** Create comprehensive project documentation (README, LICENSE) and set up GitHub Actions CI for automated Docker image builds, preparing for the v0.1.0 release.

**Requirements:** CLEAN-03, CLEAN-04, DEPLOY-03, REL-01

**Status:** Complete (2026-02-22)
**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md — Create concise README.md with WIP indication (LICENSE already present)
- [x] 08-02-PLAN.md — Create GitHub Actions CI/CD workflows (test + Docker publish) + v0.1.0 release

**Success criteria:**
- README.md with concise project description, WIP indication, Docker quick start, dev setup ✅
- LICENSE file present (Apache 2.0, already exists) ✅
- GitHub Actions workflow builds and publishes Docker image on release tags ✅
- GitHub release v0.1.0 created with changelog ✅

---

### Phase 9: Deployment Templates

**Goal:** Create deployment configurations for Docker users and Unraid Community Apps, making BeanBay installable by anyone with Docker or Unraid.

**Requirements:** DEPLOY-01, DEPLOY-02, DEPLOY-04, BRAND-03

**Depends on:** Phase 8 (needs CI workflow and Docker image published)

**Plans:** 1 plan

Plans:
- [ ] 09-01-PLAN.md — Update Docker files with BeanBay naming + create Unraid CA XML template

**Success criteria:**
- docker-compose.yml updated with BeanBay naming
- Docker image published to ghcr.io/grzonka/beanbay
- Unraid XML template in repository (installable via Community Apps custom repo)
- App icon/logo created for Unraid template and GitHub

---

## Milestone Summary

| Phase | Name | Requirements | Depends On |
|-------|------|-------------|------------|
| 7 | Rebrand & Cleanup | BRAND-01,02 CLEAN-01,02 DEBT-01-04 REL-02 | — |
| 8 | Documentation & Release | CLEAN-03,04 DEPLOY-03 REL-01 | Phase 7 |
| 9 | Deployment Templates | DEPLOY-01,02,04 BRAND-03 | Phase 8 |

**After v0.1.0:** Deploy to Unraid, use with real espresso sessions, then plan v2 (multi-method optimization platform).

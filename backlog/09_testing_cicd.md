# Epic 09 — Testing, CI/CD & Containerisation

> **Status:** In Progress
> **Priority:** P1  
> **Owner:** —  

## Goal
Ensure reproducibility, code quality, and safe deployments through automated
testing, linting, and containerised environments.

## Tasks

- [x] Scaffold GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- [x] Create `tests/conftest.py` and initial smoke tests
- [x] Write Dockerfile + docker-compose.yml for pipeline + site
- [ ] Expand unit tests: ≥ 1 test per module in `src/`
- [ ] Add integration test: end-to-end download → process → visualise (mocked API)
- [x] Add Ruff linting step to CI
- [ ] Resolve 74 existing Ruff findings recorded on 2026-11-19
- [ ] Install pytest explicitly in CI; runtime requirements do not provide test tooling
- [ ] Add `black` formatting check to CI
- [ ] Set up pre-commit hooks (ruff, black, trailing whitespace, YAML lint)
- [ ] Add code coverage reporting (pytest-cov → Codecov badge)
- [ ] Test Docker build in CI (`docker build -t chicago2030 -f docker/Dockerfile .`)
- [ ] Add CD job: deploy site/ to GitHub Pages on merge to `main`
- [x] Add weekly ETL workflow (`.github/workflows/etl.yml`)
- [ ] Make ETL fail on each missing required dataset; align historical prerequisite and artifact output paths
- [ ] Pin Docker base image to specific Python digest for reproducibility

## Acceptance Criteria
- `pytest` runs ≥ 10 tests with 0 failures
- CI fails on lint/test errors; verify branch protection separately before claiming merges are blocked.
- Docker image builds without errors
- Site auto-deploys on push to `main`

## Dependencies
- Epic 01 (repo setup)
- Add regression tests alongside each implemented feature; this epic does not require every future epic to be finished.

## Audit - 2026-11-19

Status reflects checked-in implementation; unchecked acceptance criteria still require evidence. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

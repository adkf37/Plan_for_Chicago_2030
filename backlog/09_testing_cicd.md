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
- [ ] Add `ruff` linting step to CI
- [ ] Add `black` formatting check to CI
- [ ] Set up pre-commit hooks (ruff, black, trailing whitespace, YAML lint)
- [ ] Add code coverage reporting (pytest-cov → Codecov badge)
- [ ] Test Docker build in CI (`docker build -t chicago2030 -f docker/Dockerfile .`)
- [ ] Add CD job: deploy site/ to GitHub Pages on merge to `main`
- [ ] Add scheduled job: weekly data refresh (calls download pipeline)
- [ ] Pin Docker base image to specific Python digest for reproducibility

## Acceptance Criteria
- `pytest` runs ≥ 10 tests with 0 failures
- CI blocks merge if lint or tests fail
- Docker image builds without errors
- Site auto-deploys on push to `main`

## Dependencies
- Epic 01 (repo setup)
- All other epics (tests cover their modules)

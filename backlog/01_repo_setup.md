# Epic 01 — Repository & Tooling Setup

> **Status:** Done  
> **Priority:** P0 — Foundation  
> **Owner:** —  

## Goal
Establish a clean, well-documented monorepo with consistent paths, secrets
management, linting, CI, and containerised dev environment.

## Tasks

- [x] Reorganise directory structure (`src/`, `viz/`, `data/`, `maps/`, `reports/`, `site/`, `docker/`, `tests/`, `backlog/`)
- [x] Create centralised `src/config.py` with all path constants (pathlib-based)
- [x] Add `.env.example` and integrate `python-dotenv` — remove hardcoded API tokens
- [x] Write `requirements.txt` and `pyproject.toml`
- [x] Update `.gitignore` (exclude data/raw, data/geojson, maps/*.html, .env)
- [x] Move data files into `data/raw/`, `data/geojson/`, `data/reference/`, `data/processed/`
- [x] Scaffold Dockerfile + docker-compose.yml
- [x] Scaffold GitHub Actions CI workflow (`lint → test`)
- [x] Add `tests/conftest.py` and initial smoke tests
- [ ] Add `ruff` / `black` config in `pyproject.toml`
- [ ] Add pre-commit hooks (`.pre-commit-config.yaml`)

## Acceptance Criteria
- `pip install -r requirements.txt && pytest -q` passes on a fresh clone
- No hardcoded absolute Windows paths in any `src/` or `viz/` file
- `.env` is in `.gitignore`; token lives only in `.env`
- CI pipeline triggers on push to `main`

## Notes
- The old root-level Python scripts remain until Epic 01 cleanup task deletes them.
- `data/reference/` (zoning_codes.csv, upzoning_scenario_changes.csv) IS tracked in Git; everything else in `data/` is ignored.

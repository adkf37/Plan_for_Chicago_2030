# Epic 01 — Repository & Tooling Setup

> **Status:** In Progress (foundation implemented; reproducibility gaps remain)
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
- [x] Add Black config in `pyproject.toml`
- [ ] Add explicit Ruff config and resolve repository lint failures
- [ ] Add pre-commit hooks (`.pre-commit-config.yaml`)

## Acceptance Criteria
- Runtime dependencies plus explicit test dependencies install and `python -m pytest -q` passes on a fresh clone (not yet met: requirements.txt does not install pytest).
- No hardcoded absolute Windows paths in any `src/` or `viz/` file
- `.env` is in `.gitignore`; token lives only in `.env`
- CI pipeline triggers on push to `main`

## Notes
- No legacy root-level Python scripts were found in this audit.
- Correction: neither reference CSV is tracked; the final `*.csv` ignore rule overrides earlier exceptions. Track the curated zoning lookup. The existing upzoning CSV is generated output containing WKT, not a rule definition.
- [ ] Fix reference-data tracking and verify a fresh clone can run lookup-dependent tests.

## Audit - 2026-11-19

Status reflects checked-in implementation; unchecked acceptance criteria still require evidence. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

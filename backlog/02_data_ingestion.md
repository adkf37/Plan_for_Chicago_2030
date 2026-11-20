# Epic 02 — Data Ingestion Pipeline

> **Status:** In Progress (downloaders implemented; completeness and historical contract need repair)
> **Priority:** P0 — Foundation  
> **Owner:** —  

## Goal
Build a reliable, reproducible pipeline that downloads, validates, and stores
all upstream datasets so analysis modules can work from local files.

## Datasets

| Source | API / URL | Script |
|---|---|---|
| Cook County Assessor — Assessed Values | Socrata `uzyt-m557` | `src/download_data.py` |
| Cook County parcel geometry | Configured Socrata `nj4t-kc8j` | `src/download_data.py` |
| Chicago Zoning Map | Configured Socrata `dj47-wfun` (GeoJSON) | `src/download_data.py` |
| Selected study-area historical years | Socrata `uzyt-m557`; year-field contract needs verification | `src/download_historical.py` |
| Cook County census tract boundaries | 2023 TIGER/Line; ACS attributes remain planned | `src/download_data.py` |
| CTA L stops, bus routes, Metra stations | Socrata URLs in `src/config.py` | `src/download_data.py` |

## Tasks

- [x] Consolidate Socrata fetch logic into `src/data_utils.py` (JSON + GeoJSON)
- [x] Implement `src/download_data.py` — parcels, assessments, zoning
- [x] Implement study-area, selected-year historical downloader
- [ ] Repair year / tax_year schema and verify complete historical output; this is not a full-county 1999-present downloader
- [x] Add cache layer (ETag / Last-Modified headers) to avoid redundant downloads
- [x] Add data validation: row counts, required columns, CRS checks
- [x] Download census tract boundaries (`data/geojson/census_tracts.geojson`)
- [x] Download CTA rail station locations (point layer)
- [x] Add scheduled ETL via GitHub Actions cron job (weekly refresh)
- [x] Write integration test that mocks Socrata and verifies output files exist

## Acceptance Criteria
- Running `python -m src.download_data` populates `data/geojson/` with ≥ 3 files
- Historical downloader requires `data/processed/parcels_in_area.csv` and currently writes `data/processed/historical_data/historical_assessments.csv`; align workflow artifact paths with the real outputs.
- All downloads respect `SOCRATA_APP_TOKEN` from `.env`
- Pipeline is idempotent: re-running doesn't duplicate data

## Dependencies
- Epic 01 (repo structure, `.env`, config)

## Audit - 2026-11-19

Pagination currently returns and may cache partial data after a later-page failure. Validation warnings do not consistently stop exports. Add stable pagination, completeness checks and failure tests before calling the pipeline reproducible. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

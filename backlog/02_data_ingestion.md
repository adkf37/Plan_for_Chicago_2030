# Epic 02 — Data Ingestion Pipeline

> **Status:** In Progress  
> **Priority:** P0 — Foundation  
> **Owner:** —  

## Goal
Build a reliable, reproducible pipeline that downloads, validates, and stores
all upstream datasets so analysis modules can work from local files.

## Datasets

| Source | API / URL | Script |
|---|---|---|
| Cook County Assessor — Assessed Values | Socrata `uzyt-m557` | `src/download_data.py` |
| Cook County Assessor — Parcel Universe | Socrata `77tz-riq7` | `src/download_data.py` |
| Chicago Zoning Map | Socrata `7cza-jqm4` (GeoJSON) | `src/download_data.py` |
| Historical Assessments (1999-present) | Socrata `uzyt-m557` | `src/download_historical.py` |
| Census Tracts & ACS Data | Census Bureau API / TIGER shapefiles | _planned_ |
| CTA L Stations + Bus Routes | CTA GTFS / Socrata | _planned_ |

## Tasks

- [x] Consolidate Socrata fetch logic into `src/data_utils.py` (JSON + GeoJSON)
- [x] Implement `src/download_data.py` — parcels, assessments, zoning
- [x] Implement `src/download_historical.py` — full historical assessments
- [ ] Add cache layer (ETag / Last-Modified headers) to avoid redundant downloads
- [ ] Add data validation: row counts, required columns, CRS checks
- [ ] Download census tract boundaries (`data/geojson/census_tracts.geojson`)
- [ ] Download CTA rail station locations (point layer)
- [ ] Add scheduled ETL via GitHub Actions cron job (weekly refresh)
- [ ] Write integration test that mocks Socrata and verifies output files exist

## Acceptance Criteria
- Running `python -m src.download_data` populates `data/geojson/` with ≥ 3 files
- Running `python -m src.download_historical` writes historical CSV to `data/raw/`
- All downloads respect `SOCRATA_APP_TOKEN` from `.env`
- Pipeline is idempotent: re-running doesn't duplicate data

## Dependencies
- Epic 01 (repo structure, `.env`, config)

# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

An urban planning analysis platform for Chicago: geospatial data processing,
property value modelling, zoning scenario comparison, and interactive web maps.
The goal is to produce a public website with data-driven policy arguments for
transit-oriented upzoning by 2030.

## Repository Layout

```
src/            Core Python modules (all import from src.config)
  config.py     Centralised paths, constants, API settings
  data_utils.py Socrata API fetch helpers (JSON + GeoJSON)
  download_data.py        Download parcels, assessments, zoning
  download_historical.py  Historical assessments (1999-present)
  process_historical.py   Appreciation rate calculations
  improved_uplift_model.py Multi-scenario value uplift model
  analyze_area.py         Near South Side area analysis
  compare_zoning_scenarios.py  Upzoning scenario builder
  zoning_value_impact.py  Value impact heatmap
  zoning.py               Zoning classification (placeholder)
  property_value.py       Property value simulation (placeholder)
  transportation.py       Transport network analysis (placeholder)
viz/            Visualisation scripts
  visualize_zoning.py     City-wide Folium zoning map
  visualize_appreciation.py  Appreciation charts (matplotlib/seaborn)
  loading_data.py         Multi-layer interactive map
data/
  raw/          Large CSVs (gitignored)
  geojson/      Spatial datasets (gitignored)
  processed/    Analysis outputs (gitignored)
  reference/    Lookup tables (tracked): zoning_codes.csv, upzoning_scenario_changes.csv
maps/           Generated HTML maps (gitignored)
reports/visualizations/  Generated PNG charts (gitignored)
site/           Static website (index.html)
docker/         Dockerfile + docker-compose.yml
tests/          Pytest suite
backlog/        10 epic-level markdown to-do files
```

## Common Development Commands

```powershell
# Install
python -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt

# Data download
python -m src.download_data
python -m src.download_historical

# Analysis
python -m src.analyze_area
python -m src.process_historical
python -m src.improved_uplift_model

# Maps
python -m viz.visualize_zoning
python -m src.compare_zoning_scenarios
python -m src.zoning_value_impact

# Visualisation
python -m viz.visualize_appreciation

# Tests
pytest -q
```

## Key Configuration

All paths are defined in `src/config.py` using `pathlib.Path` relative to
`PROJECT_ROOT`. Never hardcode absolute paths.

**API Token:** stored in `.env` (see `.env.example`). Loaded via
`python-dotenv` in `src/config.py`. Never commit the token.

**Socrata Endpoints**:
- Parcels: `datacatalog.cookcountyil.gov/resource/77tz-riq7.geojson`
- Assessments: `datacatalog.cookcountyil.gov/resource/uzyt-m557.geojson`
- Chicago Zoning: `data.cityofchicago.org/resource/7cza-jqm4.geojson`

## Data Processing Patterns

1. `src/data_utils.py` — `fetch_all_socrata_data(url)` paginates through
   Socrata endpoints (default limit 50 000), handles JSON + GeoJSON,
   respects `SOCRATA_APP_TOKEN`.
2. `src/download_data.py` — downloads to `data/geojson/`.
3. `src/process_historical.py` — reads `data/raw/` CSVs, calculates annual
   appreciation by zone type, writes to `data/processed/`.
4. `src/improved_uplift_model.py` — reads appreciation rates + parcels,
   applies multi-scenario uplift rules, writes to `data/processed/uplift_scenarios/`.

## Housing Density Categories (from config.py)

| Code | Name | Units/Acre |
|------|------|-----------|
| SFH | Single-Family | 0–8 |
| TH | Townhouse/Duplex | 8–16 |
| LR | Low-Rise Apartment | 16–30 |
| MR | Mid-Rise Apartment | 30–60 |
| HR | High-Rise Apartment | 60–150 |
| MX_L | Mixed-Use Low | 30–60 |
| MX_H | Mixed-Use High | 60–150 |

## Backlog

Ten epics live in `backlog/01_repo_setup.md` through `backlog/10_community_engagement.md`.
Each has checkboxes, acceptance criteria, and dependency links.

## Current Limitations

- `zoning.py`, `property_value.py`, `transportation.py` are placeholders
- Uplift model uses flat $250K estimate — needs actual per-parcel values
- Census tract + CTA station downloads not yet implemented
- Vector tile pipeline for production map not started
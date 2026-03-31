# Plan for Chicago 2030

A data-driven urban planning platform that visualises and models Chicago's
zoning, property values, transit access, and development scenarios through an
interactive web map and accompanying policy website.

## Project Overview

| What | How |
|------|-----|
| Geospatial analysis | GeoPandas, Shapely, osmnx |
| Interactive mapping | Deck.gl (frontend) + PyDeck (standalone maps) + PMTiles (vector tiles) |
| Scenario modelling | Rule-based upzoning + historical appreciation rates |
| Property values | Cook County Assessor data (1999–2025) |
| Website | Static HTML/CSS/JS in `site/` (GitHub Pages) |

## Quick Start

### Option A — Local Python environment

```bash
# 1. Clone & setup
git clone <repo-url> && cd Plan_for_Chicago_2030
cp .env.example .env            # add your Socrata token
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# 2. Run the complete pipeline (recommended)
python -m src.pipeline          # downloads data → zoning → transit → web map

# OR run individual modules:
python -m src.download_data     # → data/geojson/ (parcels, zoning, transit)
python -m src.zoning            # → data/processed/parcels_enriched.geojson
python -m src.transportation    # → data/processed/transit_scores.csv
python -m src.prepare_map_data  # → site/data/*.geojson + PMTiles (web map layers)

# 3. Generate analysis maps
python -m viz.visualize_zoning           # → maps/chicago_zoning_map.html
python -m src.compare_zoning_scenarios   # → maps/zoning_comparison_map.html
python -m src.analyze_area               # → maps/area_value_map.html

# 4. Run tests
pytest -q
```

### Option B — Docker (recommended for PMTiles generation)

Docker bundles **tippecanoe** (the GeoJSON → PMTiles converter) so you don't
need to install it locally.  Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
cp .env.example .env   # add your Socrata token (optional)

# Build the image (only needed once, or after Dockerfile changes)
docker compose -f docker/docker-compose.yml build

# Download data & run the full pipeline
docker compose -f docker/docker-compose.yml run --rm pipeline python -m src.pipeline

# Export web-map layers + generate PMTiles
docker compose -f docker/docker-compose.yml run --rm tiles

# Serve the site locally at http://localhost:8080
docker compose -f docker/docker-compose.yml up site
```

| Service | What it does |
|---------|-------------|
| `pipeline` | Runs any `src.*` command inside the container with data volumes mounted |
| `tiles` | Runs `src.prepare_map_data` → exports GeoJSON layers + builds PMTiles via tippecanoe |
| `site` | Serves `site/` via nginx on port 8080 for local preview |

> **Note**: The `data/`, `maps/`, `reports/`, and `site/data/` directories are
> bind-mounted, so all outputs land on your host machine as normal.

See [QUICK_START.md](QUICK_START.md) for the full uplift-analysis walkthrough.

## Repository Structure

```
Plan_for_Chicago_2030/
├── src/                    # Core data & analysis modules
│   ├── pipeline.py         # 🚀 Master orchestrator — runs full pipeline
│   ├── config.py           # All paths, constants, API settings
│   ├── data_utils.py       # Socrata API helpers
│   ├── download_data.py    # Dataset downloader
│   ├── zoning.py           # Zoning analysis & parcel enrichment
│   ├── transportation.py   # Transit accessibility scoring
│   ├── prepare_map_data.py # Web map layer generator
│   ├── analyze_area.py     # Area-level value analysis
│   ├── compare_zoning_scenarios.py
│   ├── zoning_value_impact.py
│   ├── property_value.py
│   ├── download_historical.py
│   ├── process_historical.py
│   └── improved_uplift_model.py
├── viz/                    # Visualisation scripts
│   ├── visualize_zoning.py
│   ├── visualize_appreciation.py
│   └── loading_data.py
├── data/
│   ├── raw/                # Large CSVs (gitignored)
│   ├── geojson/            # Spatial data (gitignored)
│   ├── processed/          # Analysis outputs (gitignored)
│   └── reference/          # Small lookup tables (tracked)
├── maps/                   # Generated HTML maps (gitignored)
├── reports/visualizations/ # Generated charts (gitignored)
├── site/                   # Public website (index.html)
├── docker/                 # Dockerfile + docker-compose
├── tests/                  # Pytest suite
├── backlog/                # 10 epic-level to-do files
├── .github/workflows/      # CI pipeline
├── .env.example            # Template for secrets
├── requirements.txt
├── pyproject.toml
├── CONTRIBUTING.md
└── LICENSE (MIT)
```

## Data Files

### Tracked in Git (`data/reference/`)
- `zoning_codes.csv` — zone code definitions (FAR, max height, use type)
- `upzoning_scenario_changes.csv` — upzoning rule definitions

### Downloaded by scripts (gitignored)
- Cook County parcel geometries & assessed values
- Chicago zoning districts GeoJSON
- Historical assessments (1999–2025)
- Census tracts, CTA stations *(planned)*

## Backlog

The project roadmap lives in `backlog/` as 10 GitHub-Issues-style epics:

| # | Epic | Status |
|---|------|--------|
| 01 | Repo & Tooling Setup | Done |
| 02 | Data Ingestion Pipeline | In Progress |
| 03 | Zoning Analysis Engine | In Progress |
| 04 | Property Value Modelling | In Progress |
| 05 | Transit & Walkability Scoring | Not Started |
| 06 | Interactive Map Platform | In Progress |
| 07 | Scenario Comparison Tool | In Progress |
| 08 | Public Website & Policy Brief | Not Started |
| 09 | Testing, CI/CD & Containers | In Progress |
| 10 | Community Engagement & Outreach | Not Started |

## Chicago Zoning Primer

| Zone Type | Code Prefix | Color | FAR Range |
|-----------|-------------|-------|-----------|
| Single-Family | RS | Green | 0.5–0.9 |
| Townhouse | RT | Green | 0.9–1.2 |
| Multi-Unit | RM | Green | 1.5–4.4 |
| Business | B | Blue | 1.2–5.0 |
| Commercial/Mixed | C | Blue | 1.5–5.0 |
| Manufacturing | M | Yellow | 1.2–2.0 |
| Downtown | DX/DC/DR/DS | Blue/Green | 5.0–16.0 |
| Planned Dev | PD | Red | varies |
| Parks | — | Dark Green | — |
| Transportation | T | Gray | — |

Density is encoded in the suffix: **RS-3** = FAR 0.9, **RM-6** = FAR 4.4.

## Acknowledgements

- **Zoning Data**: [DataMade / Second City Zoning](https://github.com/datamade/second-city-zoning)
- **Assessment Data**: Cook County Open Data Portal (Socrata)
- **Geography**: OpenStreetMap, Chicago Data Portal
- **Inspiration**: Burnham Plan of Chicago (1909), SimCity 2000

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, style guide, and PR workflow.

---

**Status**: Active Development
**Last Updated**: March 2026

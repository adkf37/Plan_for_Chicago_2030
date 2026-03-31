# Freamon — Project History

## Core Context
- **Project:** Plan_for_Chicago_2030 — Python geospatial analysis for Chicago urban planning
- **User:** Aaron
- **Stack:** Python, GeoPandas, Folium, Pandas, Shapely, pytest
- **Mission:** Analyze zoning, property values, transit walkability, and land use scenarios around Chicago. Key analysis area: Soldier Field and surrounding South Loop.
- **Key constraint:** Do NOT download new external data. All data is already in the repo (data/, cache/).

## Team
- Freamon (Lead) — scope, decisions, code review
- McNulty (Geo Developer) — spatial analysis, maps, GeoJSON
- Bunk (Data Engineer) — pipelines, Pandas, data processing
- Greggs (Tester) — pytest, data validation
- Scribe — session logging
- Ralph — work monitor

## Learnings

### 2026-03-30 — Architecture Review (Session 1)

**Stack correction:** Stack is Python + GeoPandas + PyDeck (not Folium — project migrated to PyDeck/deck.gl). Static site uses MapLibre/Deck.gl with PMTiles.

**Pipeline structure (two disconnected tracks):**
- **Track A — Main pipeline** (`pipeline.py`): download_data → zoning → transportation → prepare_map_data → site/data/
- **Track B — Analysis sub-chain** (not in pipeline.py): analyze_area → download_historical → process_historical → improved_uplift_model → property_value
- Track B must be run manually and is entirely undocumented in pipeline.py. The web map's value layer (`export_value_layer`) silently skips merging value projections if `value_projections.csv` is missing.

**Critical bugs confirmed:**

1. **`RAW_HISTORICAL_CSV` path is wrong in config.py**
   - Config points to: `data/raw/historical/Assessor_-_Assessed_Values_since_1999_20251004.csv`
   - Actual file is at: `data/raw/Assessor_-_Assessed_Values_since_1999_20251004.csv`
   - `data/raw/historical/` directory is empty. `process_historical.py` will fail with FileNotFoundError.

2. **`improved_uplift_model.py` input path mismatch**
   - Expects: `data/processed/historical_data/appreciation_by_zoning.csv`
   - Actual files: `data/processed/historical_appreciation_by_zoning.csv` (different dir, different name)
   - `data/processed/historical_data/` is empty. The improved model is completely broken.

3. **`process_historical.py` output path mismatch**
   - Writes to `ANALYSIS_RESULTS_DIR` (`analysis_results/`) per current code
   - But processed CSVs exist in `data/processed/` (historical_appreciation_by_zoning.csv, etc.)
   - Likely written by a prior version of the script before refactor. Analysis results and improved_uplift paths are now out of sync.

4. **`value_projections.csv` never generated**
   - `data/processed/value_projections.csv` does not exist
   - `property_value.py` is the generator; it has never been run to completion
   - Web map parcels layer silently omits value data

**Missing data files:**
- `data/geojson/metra_stations.geojson` — not present; all scripts degrade gracefully
- `data/processed/value_projections.csv` — not present
- `data/processed/value_model_validation.csv` — not present
- `data/processed/historical_data/appreciation_by_zoning.csv` — not present

**Data files confirmed present:**
- `data/geojson/`: parcel_data.geojson, assessment_data.geojson, zoning_data.geojson, chicago_zoning_2025.geojson, cta_stations.geojson, census_tracts.geojson
- `data/raw/`: Assessor CSVs (parcel universe, assessments, historical since 1999)
- `data/processed/`: parcels_enriched.geojson, parcels_in_area.csv, transit_scores.csv, zoning_summary.csv, historical_appreciation_by_zoning.csv, appreciation_by_zone_year.csv
- `site/data/`: parcels.geojson, zoning.geojson, proposed_zoning.geojson, transit_stations.geojson, PMTiles (pipeline has been run before)

**Zoning data duality:**
- `zoning_data.geojson` = Cook County Socrata source (used by main pipeline enrichment)
- `chicago_zoning_2025.geojson` = City of Chicago zoning layer (has `ZONE_CLASS` column; used by compare_zoning_scenarios.py, zoning_value_impact.py)
- These are different datasets. Scenarios in compare/value scripts operate on the City layer, but parcel enrichment uses the County layer. Cross-module consistency is not assured.

**What's working:**
- Track A pipeline runs cleanly end-to-end (evidence: site/data/ is fully populated with PMTiles journal files present)
- zoning enrichment, transit scoring, map data preparation all produce outputs
- Tests exist for core modules

**Priority fix order:**
1. Fix `RAW_HISTORICAL_CSV` path in config.py (one-liner)
2. Align `improved_uplift_model.py` input path to match actual output of `process_historical.py`
3. Wire Track B into `pipeline.py` or document it as a separate analysis run
4. Run `property_value.py` to generate `value_projections.csv` for the web map value layer

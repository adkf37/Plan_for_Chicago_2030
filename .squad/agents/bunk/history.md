# Bunk — Project History

## Core Context
- **Project:** Plan_for_Chicago_2030 — Python geospatial analysis for Chicago urban planning
- **User:** Aaron
- **Stack:** Python, GeoPandas, Folium, Pandas, Shapely, pytest
- **Mission:** Data pipelines for zoning analysis, property value modeling, scenario comparison.
- **Key constraint:** Do NOT download new external data. All data is already in the repo.

## Key Paths
- `data/raw/`, `data/processed/`, `data/reference/`, `data/geojson/`, `cache/` — data sources
- `src/pipeline.py` — main pipeline
- `src/data_utils.py`, `src/config.py` — utilities and config
- `src/property_value.py`, `src/improved_uplift_model.py` — value modeling
- `src/compare_zoning_scenarios.py`, `src/zoning_value_impact.py` — zoning analysis
- `src/analyze_area.py`, `src/soldier_field_analysis.py` — area analysis
- `data/reference/zoning_codes.csv` — zoning reference data

## Learnings

### Pipeline Review — 2026-03-30

#### Data Inventory
- `data/raw/`: Assessor assessed values CSV (2025-04-30), historical assessed values since 1999, Parcel Universe CSV (2025-04-30).
- `data/geojson/`: parcel_data.geojson, assessment_data.geojson, zoning_data.geojson, chicago_zoning_2025.geojson, cta_stations.geojson, census_tracts.geojson.
- `data/reference/`: zoning_codes.csv, upzoning_scenario_changes.csv.
- `data/processed/`: parcels_in_area.csv (20,530 parcels), parcels_enriched.geojson (150K parcels), transit_scores.csv, zoning_summary.csv (header only, no rows), zoning_value_impact_analysis.csv, historical_appreciation_by_zoning.csv, appreciation_by_zone_year.csv, parcel_appreciation_summary.csv.
- `data/processed/historical_data/`: **EMPTY** — no download_historical.py output.
- `data/processed/uplift_scenarios/`: **EMPTY** — no improved_uplift_model.py output.
- `cache/`: Several .geojson and .json files cached from Socrata API.
- `analysis_results/`: Only soldier_field_value_projection.csv — missing historical_appreciation_by_zoning.csv (which is in data/processed/ instead).

#### Critical Bugs

**BUG-1 — parcels_enriched.geojson: zone_class NULL for ALL 150K parcels**
- `zoning.py::run_zoning_analysis()` loads `PARCEL_GEOJSON` (parcel_data.geojson) and spatially joins to `ZONING_GEOJSON` (zoning_data.geojson).
- The parcel_data.geojson was downloaded from Cook County Socrata API without geographic filtering. First feature is in zip 60305 (River Forest, suburb), `chicago_community_area_num: null`. The 150K parcels fetched are largely/entirely suburban.
- Result: `gpd.sjoin(..., how="left", predicate="within")` matches zero parcels to Chicago zoning polygons → zone_class, far, zone_type, zone_category, near_transit all null.
- Also MISSING from enriched file: `certified_tot` assessment values are never joined in — the enrichment pipeline only joins Cook County parcel universe attributes, not the assessment CSV.

**BUG-2 — improved_uplift_model.py: required input MISSING**
- Needs `HISTORICAL_DATA_DIR / "appreciation_by_zoning.csv"` = `data/processed/historical_data/appreciation_by_zoning.csv`.
- That directory is EMPTY. This file is output of `download_historical.py`, which requires live API calls. Will hard-fail on load.

**BUG-3 — Wrong Cook County class codes in improved_uplift_model.py scenarios**
- Residential scenarios target class codes "202", "203". Study area (parcels_in_area.csv) has 18,540/20,530 parcels with class "299" (Not in rules). Code "295" (commercial) has 861 matches.
- Result: Residential upzoning scenarios match 0 parcels. Only commercial scenario partially works.

**BUG-4 — near_transit filter silently unimplemented in improved_uplift_model.py**
- `apply_scenario()` only handles `rule["filter"] is None`. Rules with `filter="near_transit"` are silently skipped — no elif/else branch for the transit filter.
- The TOD scenario with near_transit rules never applies any rezoning.

**BUG-5 — parcels_enriched.geojson missing certified_tot**
- property_value.py::load_enriched_parcels() loads the enriched GeoJSON first (since it exists), but certified_tot is not in the enriched file. `current_market_value()` falls through to zone-median fallback ($250K) for ALL parcels.
- The fallback CSV (PARCELS_IN_AREA_CSV) has real certified_tot values and would work — but the code never reaches it because the GeoJSON exists.

#### Significant Data Mismatches

**MISMATCH-1 — appreciation rates path: primary MISSING, fallback EXISTS**
- property_value.py primary: `analysis_results/historical_appreciation_by_zoning.csv` — MISSING.
- Fallback: `data/processed/historical_appreciation_by_zoning.csv` — EXISTS with column `avg_annual_appreciation` (fractions, e.g. 0.06 = 6%).
- The code's prefix fallback ("RS-3" → "RS") would work BUT zone_class is null (see BUG-1), so all parcels get 3% default anyway.

**MISMATCH-2 — appreciation rate column naming between pipelines**
- process_historical.py saves to analysis_results/, column `avg_annual_appreciation` (fractions).
- download_historical.py saves to data/processed/historical_data/, column `avg_annual_appreciation_pct` (percentages, e.g. 6.0).
- improved_uplift_model.py reads from historical_data/ and expects `avg_annual_appreciation_pct`.
- These are separate pipelines with incompatible column names and scales; cannot be interchanged.

**MISMATCH-3 — transit column name**
- transit_scores.csv has column `station_distance_m`.
- property_value.py::transit_multiplier() looks for column `transit_dist_m`.
- However transit_scores.csv is not used by property_value.py (which reads parcels_enriched.geojson), so this is currently harmless.

#### Minor Issues

**MINOR-1 — UNIVERSE_ATTRIBUTES in analyze_area.py references non-existent columns**
- `["CLS_CLASS_DESCRIPTION", "NBHD_DESC", "BLDG_SQ_FT"]` — none present in Parcel Universe CSV. Always filtered to empty list. Extra attributes never added to parcels_in_area.csv.

**MINOR-2 — Dead code in process_historical.py**
- Lines ~143-147: `if False` block for a pipe-style save that is immediately superseded by explicit saves. Harmless but confusing.

**MINOR-3 — zoning_summary.csv header-only**
- File exists but has no data rows. Zoning analysis pipeline never produced summary because spatial join failed.

### Pipeline Fixes Applied — 2026-03-30

#### BUG 1 — config.py RAW_HISTORICAL_CSV wrong subdirectory
- **Was:** `RAW_HISTORICAL_DIR / "Assessor_-_..."` → `data/raw/historical/` (empty dir)
- **Fixed:** `RAW_DIR / "Assessor_-_..."` → `data/raw/` (file actually exists here)
- **File:** `src/config.py`, `RAW_HISTORICAL_CSV` constant

#### BUG 2 — Appreciation CSV path + column mismatch (config + improved_uplift_model)
- **Was:** `HISTORICAL_DATA_DIR / "appreciation_by_zoning.csv"` → `data/processed/historical_data/` (empty dir)
- **Fixed (config):** Added `APPRECIATION_BY_ZONING_CSV = PROCESSED_DIR / "historical_appreciation_by_zoning.csv"` constant
- **Fixed (model):** `load_data()` now imports and uses `APPRECIATION_BY_ZONING_CSV`
- **Column normalization added:** `process_historical.py` writes fractions + different column names; `load_data()` now renames `avg_annual_appreciation`→`avg_annual_appreciation_pct`, `median_annual_appreciation`→`median_annual_appreciation_pct`, `total_observations`→`parcel_count`, and multiplies by 100 to convert fractions to percentage scale
- **Files:** `src/config.py` (new constant), `src/improved_uplift_model.py` (load_data)

#### BUG 3 — Wrong Cook County residential class codes in scenario rules
- **Was:** `"202"` and `"203"` (absent from study area data) → 0 parcels matched
- **Fixed:** Changed to `"299"` (the actual dominant residential class, 18,540/20,530 parcels)
- **Near-transit TOD scenario:** Combined two redundant residential rules into one `"299"` rule
- **File:** `src/improved_uplift_model.py`, `define_rezoning_scenarios()`
- **Verified:** 18,540 parcels now match residential scenario; 16,868 match TOD scenario

#### BUG 4 — near_transit filter silently skipped in apply_scenario()
- **Was:** No `elif filter == "near_transit":` branch → rules silently unhandled
- **Finding:** `near_transit` column not in `parcels_in_area.csv` (only 4 columns: pin, geometry, certified_tot, class). Column computed by `transportation.py` but stored in `parcels_enriched.geojson` / `transit_scores.csv` (150K suburban parcels, all False there — wrong parcel set)
- **Fixed:** Added `_add_near_transit()` helper that parses WKT geometry column, projects to EPSG:3435, and computes distance to CTA L stations from `data/geojson/cta_stations.geojson`. `load_data()` calls it if `near_transit` not present. Added `elif filter == "near_transit":` branch in `apply_scenario()`
- **Verified:** 17,970/20,530 study area parcels flagged near_transit=True (Near South Side is heavily served by L)
- **File:** `src/improved_uplift_model.py` (`_add_near_transit`, `load_data`, `apply_scenario`)

#### BUG 5 — property_value.py primary appreciation path missing
- **Was:** Primary path = `analysis_results/historical_appreciation_by_zoning.csv` (does NOT exist); fallback = `data/processed/` (exists)
- **Fixed:** Swapped order — primary is now `data/processed/historical_appreciation_by_zoning.csv`, fallback is `analysis_results/`
- **File:** `src/property_value.py`, `load_appreciation_rates()`
- **Verified:** Loads 7 zone types successfully

#### Key Data Facts Learned
- Cook County class code `299` = dominant residential class in Near South Side study area (18,540/20,530 = 90%)
- Cook County class `295` = commercial (861 parcels)
- `parcels_in_area.csv` has only 4 columns (pin, geometry, certified_tot, class) — no transit data
- Appreciation rates in `data/processed/historical_appreciation_by_zoning.csv` use proxy zoning type keys (B/C/M/RM/RS/RT) not Cook County class codes — so uplift differential is $0 until this key mismatch is resolved (pre-existing issue)
- `data/geojson/cta_stations.geojson` exists and is usable for near_transit computation

#### What DOES Work
- analyze_area.py: Successfully created parcels_in_area.csv (20,530 parcels) with real certified_tot values and Cook County class codes.
- compare_zoning_scenarios.py: Works correctly (uses chicago_zoning_2025.geojson directly, no parcel join needed).
- zoning_value_impact.py: Works correctly (uses chicago_zoning_2025.geojson directly).
- process_historical.py: Works on RAW_HISTORICAL_CSV (7.8GB file). Outputs appreciation rates to analysis_results/ and data/processed/ using proxy zoning categories.
- upzoning_scenario_changes.csv: Valid output in data/reference/ from compare_zoning_scenarios.py.
- zoning_value_impact_analysis.csv: Valid output in data/processed/ from zoning_value_impact.py.

### Appreciation Key Mapping Fix — 2026-03-30

#### Root Cause
- `improved_uplift_model.py::apply_scenario()` looked up appreciation rates using raw Cook County class codes (e.g. "299", "295") as dictionary keys.
- `historical_appreciation_by_zoning.csv` keys are Chicago zoning zone-type strings: B, C, M, RM, RS, RT, Unknown.
- Every `appreciation_lookup.get("299", {})` returned `{}` → 0% rate → $0 uplift for all parcels.

#### Fix Applied — `src/improved_uplift_model.py`

**1. Added `CLASS_TO_ZONE_TYPE` mapping dict + `_map_class_to_zone_type()` helper**
- 40-entry dict covering all class codes observed in parcels_in_area.csv.
- Key mappings: 299 → "RT" (18,540 parcels), 295 → "B" (861 parcels), 5xx commercial → "B", 5xx/6xx industrial → "M", 2xx single-family → "RS", 2xx multi-family → "RM", EX/RR → "Unknown".

**2. Rewrote the per-parcel rate lookup loop in `apply_scenario()`**
- Replaced slow row-by-row `for idx, row in results.iterrows()` loop with vectorised `.apply(_map_class_to_zone_type)` on the class-code series.
- Added median fallback rate (computed from non-zero rates in the lookup) for any zone type absent from the CSV.

**3. Added `to_zone_type` optional field in scenario rules + `target_zone_type` column**
- Separates "which parcels to filter" (class code) from "what appreciation rate to apply" (zone type policy intent).
- When `to_zone_type` is set in a rule, `apply_scenario` uses it directly for the target rate instead of mapping the target class code.
- Scenario 1 (all residential upzoning): 299→211, `to_zone_type="C"` → RT (6.39%) → C (8.31%) = +1.92% differential.
- Scenario 2 (commercial upzoning): 295→297, `to_zone_type="C"` → B (6.07%) → C (8.31%) = +2.24% differential.
- Scenario 3 (TOD): same `to_zone_type="C"` for both residential and commercial near-transit parcels.

**4. Added `run_uplift_analysis()` public function**
- Wraps the full load → prepare → lookup → run_all_scenarios → save flow.
- Returns the scenario summary DataFrame (or None on failure).
- `main()` now calls `run_uplift_analysis()`.

#### Verified Results (10-year horizon)
| Scenario | Parcels | Total Uplift | Avg/Parcel | Annual Tax Increase |
|---|---|---|---|---|
| Upzone Residential Low→Medium | 18,540 | $1,320,190,678 | $71,208 | $33,004,770 |
| Upzone Commercial Districts | 861 | $269,327,305 | $312,808 | $6,733,183 |
| Transit-Oriented Development | 16,868 | $1,421,794,322 | $84,289 | $35,544,860 |

- Before fix: **$0 uplift for every parcel** in every scenario.
- After fix: **18,540/18,540 rezoned residential parcels have non-zero values** (min $7, max $914,851, mean $71,208).

#### Data Facts Confirmed
- Appreciation rates after normalisation (fractions×100): B=6.07%, C=8.31%, M=6.93%, RM=3.86%, RS=4.17%, RT=6.39%, Unknown=6.84%.
- Rate ordering (high→low): C (8.31) > M (6.93) > Unknown (6.84) > RT (6.39) > B (6.07) > RS (4.17) > RM (3.86).
- The `to_zone_type` override pattern is important: scenario semantics (policy intent) must drive the rate choice, not the Cook County destination class code.

### Spatial Join Fix — 2026-03-30

#### Root Cause
- `parcel_data.geojson` is fetched from the Cook County Parcel Universe Socrata **attribute** endpoint (not the geometry endpoint). All 150,000 parcel rows have `geometry = None`.
- The file does contain `lat`/`lon` columns, but they are stored as **strings** (not floats) — pandas `pd.to_numeric()` is required before use.
- `spatial_join_parcels_to_zoning()` calls `gpd.sjoin()` on the null-geometry GeoDataFrame → 0 matches → 0.0% join rate → all zone_class/zone_category null → 0 upzoning candidates.
- Downstream: `transportation.py::run_transit_scoring()` loads `parcels_enriched.geojson` (which inherited null geometries). `to_crs()` on null-geometry GeoDataFrame produces NaN centroids → no valid distances → all transit tiers = "Unknown" → TOD score = 15 (only the neutral walk_score_proxy=50 component).
- **Secondary issue**: 150K parcel file covers all of Cook County. Chicago zoning polygons only cover Chicago. Suburban parcels (≈115K of 150K) would never match and inflate the join-rate denominator.

#### Fix Applied — `src/zoning.py`

**Added `_rebuild_parcel_geometries(parcels_gdf)` helper** (inserted before `run_zoning_analysis()`):
- Detects when all (or any) geometries are null.
- Casts `lon`/`lat` string columns to float via `pd.to_numeric(..., errors='coerce')`.
- Builds `Point` geometries via `gpd.points_from_xy(lon, lat)`, sets CRS to EPSG:4326.
- Filters to Chicago parcels using `chicago_community_area_num.notna()` (primary) with a bounding-box fallback.
- Falls back gracefully if lat/lon columns are absent.

**Called in `run_zoning_analysis()`** immediately after loading parcels, before any spatial join.

#### Before / After
| Metric | Before | After |
|---|---|---|
| Parcel geometries | 0 valid (all null) | 34,701 Chicago Points |
| Spatial join rate | 0.0% | **100.0%** |
| zone_category Unknown | 150,000 (100%) | 0 |
| zone_category Residential | 0 | 28,525 (82.2%) |
| Transit upzoning candidates | 0 | **10,028 (28.9%)** |
| Tier 1 (<400m) | 0 parcels (0.0%) | **5,896 (17.0%)** |
| TOD score median | 15 | **51.8** |

#### Data Facts Confirmed
- `parcel_data.geojson` = 150K Cook County attribute rows; only 34,701 are Chicago (community_area_num not null).
- `lat`/`lon` are string columns in this GeoJSON — always cast with `pd.to_numeric()`.
- `zoning_data.geojson` (ZONING_GEOJSON) has lowercase `zone_type`/`zone_class` columns; `chicago_zoning_2025.geojson` has UPPERCASE. The pipeline correctly uses the lowercase file.
- CRS is EPSG:4326 for all three relevant files (parcels, zoning, CTA stations) — no reprojection needed for the join itself.

# McNulty — Project History

## Core Context
- **Project:** Plan_for_Chicago_2030 — Python geospatial analysis for Chicago urban planning
- **User:** Aaron
- **Stack:** Python, GeoPandas, Folium, Pandas, Shapely, pytest
- **Mission:** Analyze zoning, property values, transit walkability, and land use scenarios. Maps output to maps/ directory as HTML.
- **Key constraint:** Do NOT download new external data. All data is already in the repo (data/geojson/, cache/).

## Key Paths
- `maps/` — output HTML maps (Folium)
- `data/geojson/` — GeoJSON source files
- `src/zoning.py`, `src/transportation.py`, `src/prepare_map_data.py`, `src/pydeck_utils.py`

## Learnings

### Geo Review — 2026-03-30

#### Available Geo Data (data/geojson/)
| File | Size | Content |
|---|---|---|
| assessment_data.geojson | 860 MB | Cook County parcel assessments |
| parcel_data.geojson | 714 MB | Cook County parcel polygons |
| zoning_data.geojson | 40.6 MB | Full city zoning (has `zone_type`, `zone_class`) |
| chicago_zoning_2025.geojson | 13.9 MB | Smaller zoning snapshot (same schema) |
| census_tracts.geojson | 6.4 MB | Census tract boundaries |
| cta_stations.geojson | 0.15 MB | CTA L stops (stop-level, NOT deduplicated to stations) |

#### Missing GeoJSON Files (code expects but absent)
- `data/geojson/metra_stations.geojson` — transportation.py and prepare_map_data.py handle gracefully (None), but all Metra transit analysis is silently absent from maps and TOD scores.
- `data/geojson/cta_bus_routes.geojson` — referenced in config.py, not loaded by any analysis script. Lower priority.

#### Missing Processed Files
- `data/processed/value_projections.csv` — prepare_map_data.py `export_value_layer()` gracefully skips the merge; web map value heatmap has no `current_value` / `moderate_projected` columns.
- `data/processed/value_model_validation.csv` — not used in spatial pipeline.

#### Cache Files
- `429d6033a116d93011816cb29013a8f2.geojson` (2.1 GB): raw Cook County parcel geometry download
- `a3f5460ccf1bcbb28fc297dc94d1c9a0.geojson` (2.6 GB): raw parcel/assessment download
- `bfcb85f4ac3af3fc5938c5281ccfb825.geojson` (0.15 MB): CTA L stops (same source as cta_stations.geojson)
- `f353369c65d7853ad271ae1f3a5f7875.geojson` (40.5 MB): Zoning polygons (same as zoning_data.geojson)
- `94296a9daf1b16d0aed071e4a2e84706.geojson` (0 MB): STUB — 2 fake features with PINs "1234567890"/"0987654321". Test/placeholder data.

#### CRS Notes
- All analysis uses EPSG:3435 (Illinois State Plane, **feet** not meters). Code correctly converts meters → feet for buffers (`buffer_meters * 3.28084`) and feet → meters for output distances (divide by `_FEET_PER_METRE = 3.28084`). Arithmetic correct but confusing — the inline comment in zoning.py says "use EPSG:26971 for meters" suggesting future migration to a metric CRS would be cleaner.
- All source GeoJSON uses EPSG:4326 (WGS84 / CRS84). Code reprojects as needed.

#### Code Bugs Found

**Bug 1 — cta_stations.geojson is stop-level, not station-level**
File contains ~600+ directional stop records (has `direction_id`, `stop_id`), but physically represents ~145 station locations. `load_cta_stations()` returns all stops. For distance calculations this is near-harmless (stops at same station have nearly identical coords), but semantically wrong and doubles computation. Should deduplicate on `map_id` (the station ID field) or `station_name`.

**Bug 2 — osmnx API version mismatch in `compute_walk_score_proxy`**
`transportation.py` calls `ox.features_from_bbox(bbox=(N, S, E, W))` — the old osmnx format. osmnx >= 1.9 changed to `(W, S, E, N)`. The whole function is in try/except so it silently falls back to `walk_score_proxy = 50` on any error. Walk scores in transit_scores.csv are likely all 50 (neutral) if osmnx fails. TOD scores are therefore underweighted on walkability.

**Bug 3 — `compute_walk_score_proxy` makes live OSM downloads**
Violates the project's no-download constraint. osmnx fetches live OSM amenity nodes and walk network graphs. Falls back gracefully to score=50, so not a crash risk.

**Bug 4 — Spatial join centroid geometry index risk**
In `spatial_join_parcels_to_zoning()` (zoning.py): after `gpd.sjoin(how="left", predicate="within")`, the code restores original polygon geometry via `joined["geometry"] = joined["_original_geometry"]`. If any centroid intersects zero or multiple zoning polygons, sjoin returns NaN zone_class or duplicate index rows respectively. The restoration assigns geometry by positional alignment — if the index has duplicates, Pandas may silently misalign geometries. Low probability but not guarded.

**Bug 5 — `value_projections.csv` missing → value heatmap is empty**
`export_value_layer()` in prepare_map_data.py conditionally merges value projections. Since the file doesn't exist, `site/data/parcels.geojson` will be exported without `current_value`, `moderate_projected`, or `moderate_uplift_pct`. The web map value overlay will show no data gradient.

### Bug Fixes Applied — 2026-03-30

#### Bug 1 — CTA stations deduplication (FIXED)
- **File:** `src/transportation.py`, `load_cta_stations()`
- **Problem:** `cta_stations.geojson` has 302 directional stop records; loading without dedup returned all 302. Confirmed column: `map_id`.
- **Fix:** Added `gdf = gdf.drop_duplicates(subset="map_id").reset_index(drop=True)` immediately after `gpd.read_file()`. Result: 144 unique stations.
- **Verified:** Smoke test confirmed `len(stations) == 144`.

#### Bug 2 — osmnx walk score proxy (FIXED)
- **File:** `src/transportation.py`, `compute_walk_score_proxy()`
- **Problem:** Function called `ox.features_from_bbox(bbox=(N,S,E,W))` — old osmnx format. osmnx ≥ 1.9 changed to `(W,S,E,N)`. Entire function was in try/except, so all parcels silently received `walk_score_proxy = 50`. Also violated no-download constraint.
- **Fix:** Removed osmnx entirely. Replaced with CTA-proximity formula: `walk_score = clip(100 * (1 - dist_m / 2000), 0, 100)`. Uses `station_distance_m` if already on the DataFrame (normal pipeline order), or computes it on-the-fly from local CTA GeoJSON. Fully deterministic, no network calls.
- **Verified:** Formula gives 100 at 0 m, 50 at 1 km, 0 at ≥2 km as expected.

#### Map HTML Stack
- Folium/Leaflet maps (chicago_zoning_map.html, chicago_interactive_map.html): embed all GeoJSON inline — the 40 MB zoning file will produce very large HTML.
- PyDeck maps (transit_shed_map.html, area_value_map.html, soldier_field_analysis_map.html): use Mapbox GL JS v1.13.0 from 2020. Old but functional. CARTO Positron style URL is compatible.
- soldier_field_analysis_map.html: Leaflet-based (not PyDeck), clean structure. References `../site/index.html` as back-link.
- **Mixed rendering stack**: Folium and PyDeck maps coexist in maps/. Decision needed on which to standardize on.

#### Reference Data
- `data/reference/zoning_codes.csv` ✓ — has `district_type_code` index matching zone_class values (e.g., "B1-1", "RS-3"). FAR, max_height, lot size columns all present. `enrich_with_zoning_codes()` will work correctly.
- `data/reference/upzoning_scenario_changes.csv` ✓ — exists.

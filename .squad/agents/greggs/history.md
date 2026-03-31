# Greggs — Project History

## Core Context
- **Project:** Plan_for_Chicago_2030 — Python geospatial analysis for Chicago urban planning
- **User:** Aaron
- **Stack:** Python, GeoPandas, Folium, Pandas, Shapely, pytest
- **Mission:** Validate data pipelines and analysis correctness through tests.
- **Key constraint:** Do NOT download new external data. All data is already in the repo.

## Key Paths
- `tests/` — pytest test suite
- `tests/conftest.py` — fixtures
- `tests/test_data_completeness.py`, `tests/test_data_utils.py`, etc.

## Learnings

### 2026-03-30 — Initial Test Suite Review

**Test Files Found (7 total):**
- `tests/conftest.py` — nearly empty; only adds PROJECT_ROOT to sys.path. No shared fixtures.
- `tests/test_data_completeness.py` — data universe checks
- `tests/test_data_utils.py` — config + data_utils smoke tests
- `tests/test_download_data.py` — mocked HTTP integration tests
- `tests/test_prepare_map_data.py` — map export layer tests
- `tests/test_property_value.py` — uplift model unit tests
- `tests/test_transportation.py` — transit scoring unit tests
- `tests/test_zoning.py` — zoning classification unit tests

**Pytest config (pyproject.toml):** `testpaths = ["tests"]`, `pythonpath = ["."]`. No markers defined.

**Status by file:**
- `test_data_completeness.py`: ~18 tests — ALL SKIPPED. Every fixture calls `_skip_if_missing()` which does `pytest.skip()` if the data file is absent. Data files live in `data/geojson/` which is gitignored and not present out-of-box.
- `test_data_utils.py`: 3 tests — LIKELY PASSING. Mocked HTTP, tests config path exports and `ensure_dirs()`. Fragile: manually patches 13 config module attributes in test body.
- `test_download_data.py`: ~5 tests — LIKELY PASSING. Mocked HTTP; `mock_config` fixture patches 7 config attributes. Same fragility pattern.
- `test_property_value.py`: ~15 tests — LIKELY PASSING. Pure logic, no file I/O. All referenced functions exist in src. Scenarios ("baseline", "moderate", "aggressive") match test assertions.
- `test_transportation.py`: ~15 tests — LIKELY PASSING. All functions (build_proposed_stations, combine_stations, compute_station_distances, assign_transit_tiers, compute_walk_score_proxy, compute_tod_score) exist in src.
- `test_zoning.py`: ~15 tests — LIKELY PASSING. All functions (spatial_join_parcels_to_zoning, add_zone_category, enrich_with_zoning_codes, identify_transit_corridor_parcels, identify_upzoning_candidates, calculate_zone_summary, classify_existing_density, generate_proposed_zoning) exist in src.
- `test_prepare_map_data.py`: ~8 tests — LIKELY PASSING. Uses monkeypatch on module-level config vars and tmp_path for file I/O.

**Src modules with ZERO test coverage (9 of 14 total):**
- `src/pipeline.py` — master orchestrator, complex stage logic
- `src/analyze_area.py`
- `src/compare_zoning_scenarios.py`
- `src/download_historical.py`
- `src/improved_uplift_model.py`
- `src/process_historical.py`
- `src/soldier_field_analysis.py`
- `src/pydeck_utils.py`
- `src/zoning_value_impact.py`

**Key Issues:**
1. `conftest.py` is essentially empty — fixtures duplicated across test files (`sample_parcels`, `sample_stations` defined separately in both `test_transportation.py` and `test_zoning.py`).
2. Config attribute patching pattern (manually save/restore 13 vars) is fragile — if config gains a new directory variable, tests silently miss resetting it.
3. No pytest markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`) — can't run subsets.
4. `test_data_completeness.py` provides zero value in CI; needs a fixture strategy (small bundled sample GeoJSON files) to be runnable.
5. No test for `apply_scenario` with an unknown/invalid `scenario_key` (expected `ValueError`).
6. No test for multi-page pagination in `fetch_all_socrata_data`.
7. No test for `pipeline.run_pipeline()` end-to-end or stage isolation.
8. Transit decay test uses `transit_dist_m=600` → expects 1.08 (400–800m band). Passes per code. ✓
9. `_zone_class` handles both "zone_class" and "ZONE_CLASS" column names — test uses uppercase which falls to the second check. ✓

"""
Data Universe Fact-Checking Tests
==================================
Validates that downloaded datasets represent the complete universe of data
from their respective sources. Uses known reference totals and cross-dataset
checks to catch truncated downloads, missing records, or spatial misalignment.

These tests require downloaded data files in data/geojson/.
Run ``python -m src.download_data`` first, then::

    pytest tests/test_data_completeness.py -v

Tests that depend on missing files are automatically skipped.
"""

import geopandas as gpd
import pandas as pd
import pytest
from pathlib import Path

from src.config import (
    PARCEL_GEOJSON,
    ASSESSMENT_GEOJSON,
    ZONING_GEOJSON,
    CTA_STATIONS_GEOJSON,
    CTA_BUS_ROUTES_GEOJSON,
    METRA_STATIONS_GEOJSON,
    CENSUS_TRACTS_GEOJSON,
    ZONING_CODES_CSV,
    PARCELS_ENRICHED_GEOJSON,
)


# ── Known reference totals ───────────────────────────────────────────────────
# Cook County GIS: "over 1.8 million parcels"
# The Socrata API may return a filtered subset, but should still be substantial.
COOK_COUNTY_MIN_PARCELS = 500_000

# CTA has 146 L stations (as of August 2024, per CTA/Wikipedia).
# Socrata endpoint 8pix-ypme returns directional *stops* (~2 per station).
CTA_L_STATION_COUNT = 146
CTA_L_STOPS_MIN = 280

# CTA operates 8 L lines.
CTA_L_LINES = {"Red", "Blue", "Brown", "Green", "Orange", "Pink", "Purple", "Yellow"}

# Cook County has ~1,318 census tracts (2020 Census, FIPS 17031).
COOK_COUNTY_MIN_CENSUS_TRACTS = 1_200
COOK_COUNTY_FIPS = "031"
ILLINOIS_FIPS = "17"

# Cook County bounding box (generous, covers suburbs too).
COOK_COUNTY_BOUNDS = {
    "min_lon": -88.30,
    "max_lon": -87.40,
    "min_lat": 41.40,
    "max_lat": 42.20,
}

# All 12 Chicago zone types should be present in the data.
EXPECTED_ZONE_TYPES = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _skip_if_missing(path: Path):
    """Skip the calling test when the data file has not been downloaded."""
    if not path.exists():
        pytest.skip(f"Data file not found: {path}")


def _find_column(df, candidates):
    """Return the first column name from *candidates* that exists in *df*."""
    for col in candidates:
        if col in df.columns:
            return col
    return None


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def parcels_gdf():
    _skip_if_missing(PARCEL_GEOJSON)
    return gpd.read_file(PARCEL_GEOJSON)


@pytest.fixture
def assessments_gdf():
    _skip_if_missing(ASSESSMENT_GEOJSON)
    return gpd.read_file(ASSESSMENT_GEOJSON)


@pytest.fixture
def zoning_gdf():
    _skip_if_missing(ZONING_GEOJSON)
    return gpd.read_file(ZONING_GEOJSON)


@pytest.fixture
def cta_stations_gdf():
    _skip_if_missing(CTA_STATIONS_GEOJSON)
    return gpd.read_file(CTA_STATIONS_GEOJSON)


@pytest.fixture
def census_tracts_gdf():
    _skip_if_missing(CENSUS_TRACTS_GEOJSON)
    return gpd.read_file(CENSUS_TRACTS_GEOJSON)


@pytest.fixture
def zoning_codes_df():
    _skip_if_missing(ZONING_CODES_CSV)
    return pd.read_csv(ZONING_CODES_CSV)


@pytest.fixture
def enriched_gdf():
    _skip_if_missing(PARCELS_ENRICHED_GEOJSON)
    return gpd.read_file(PARCELS_ENRICHED_GEOJSON)


# ═════════════════════════════════════════════════════════════════════════════
# 1. PARCEL DATA COMPLETENESS
# ═════════════════════════════════════════════════════════════════════════════

class TestParcelCompleteness:
    """Verify the parcel dataset represents a meaningful share of Cook County."""

    def test_parcel_count_above_minimum(self, parcels_gdf):
        """Downloaded parcels should meet the minimum threshold."""
        assert len(parcels_gdf) >= COOK_COUNTY_MIN_PARCELS, (
            f"Expected >= {COOK_COUNTY_MIN_PARCELS:,} parcels, "
            f"got {len(parcels_gdf):,}. Download may be truncated."
        )

    def test_no_null_geometries(self, parcels_gdf):
        """Every parcel record must have a non-null geometry."""
        null_ct = parcels_gdf.geometry.isna().sum()
        assert null_ct == 0, (
            f"{null_ct:,} / {len(parcels_gdf):,} parcels have null geometry."
        )

    def test_parcels_within_cook_county_bounds(self, parcels_gdf):
        """Parcel bounding box should fall within Cook County."""
        minx, miny, maxx, maxy = parcels_gdf.total_bounds
        b = COOK_COUNTY_BOUNDS
        assert minx >= b["min_lon"], f"Min lon {minx} is west of Cook County"
        assert maxx <= b["max_lon"], f"Max lon {maxx} is east of Cook County"
        assert miny >= b["min_lat"], f"Min lat {miny} is south of Cook County"
        assert maxy <= b["max_lat"], f"Max lat {maxy} is north of Cook County"

    def test_parcel_pin_uniqueness(self, parcels_gdf):
        """Parcel PINs should be largely unique (< 5 % duplicates)."""
        pin_col = _find_column(parcels_gdf, ["pin", "PIN", "pin14", "pin10"])
        if pin_col is None:
            pytest.skip("No PIN column found in parcel data")

        total = len(parcels_gdf)
        unique = parcels_gdf[pin_col].nunique()
        dup_rate = (total - unique) / total
        assert dup_rate < 0.05, (
            f"PIN duplicate rate is {dup_rate:.1%} "
            f"({total - unique:,} duplicates out of {total:,})."
        )

    def test_crs_is_wgs84(self, parcels_gdf):
        """Parcels should use EPSG:4326 (WGS 84)."""
        assert parcels_gdf.crs is not None, "CRS is not set"
        assert parcels_gdf.crs.to_epsg() == 4326, (
            f"Expected EPSG:4326, got {parcels_gdf.crs}"
        )


# ═════════════════════════════════════════════════════════════════════════════
# 2. ASSESSMENT DATA — CROSS-REFERENCE WITH PARCELS
# ═════════════════════════════════════════════════════════════════════════════

class TestAssessmentCrossReference:
    """Cross-check assessment records against parcels by PIN."""

    def test_assessment_count_reasonable(self, assessments_gdf):
        """Assessment dataset should have a substantial number of records."""
        assert len(assessments_gdf) >= 100_000, (
            f"Only {len(assessments_gdf):,} assessment records — "
            f"expected >= 100,000 for Cook County."
        )

    def test_assessments_have_value_columns(self, assessments_gdf):
        """At least one assessed-value column should be present."""
        value_candidates = {
            "mailed_tot", "certified_tot", "assessed_value",
            "total_value", "mailed_land", "certified_land",
        }
        found = value_candidates & set(assessments_gdf.columns)
        assert found, (
            f"No value column found.  Columns: {list(assessments_gdf.columns)}"
        )

    def test_parcel_to_assessment_pin_overlap(self, parcels_gdf, assessments_gdf):
        """A meaningful share of parcel PINs should appear in assessments."""
        p_pin = _find_column(parcels_gdf, ["pin", "PIN", "pin14", "pin10"])
        a_pin = _find_column(assessments_gdf, ["pin", "PIN", "pin14", "pin10"])
        if p_pin is None or a_pin is None:
            pytest.skip("PIN column not found in both datasets")

        parcel_pins = set(parcels_gdf[p_pin].dropna().astype(str))
        assess_pins = set(assessments_gdf[a_pin].dropna().astype(str))
        if not parcel_pins or not assess_pins:
            pytest.skip("No valid PINs to compare")

        overlap = len(parcel_pins & assess_pins)
        overlap_rate = overlap / len(parcel_pins)
        assert overlap_rate > 0.10, (
            f"Only {overlap_rate:.1%} PIN overlap between parcels "
            f"({len(parcel_pins):,}) and assessments ({len(assess_pins):,}). "
            f"Data sources may not align."
        )


# ═════════════════════════════════════════════════════════════════════════════
# 3. ZONING DATA COMPLETENESS
# ═════════════════════════════════════════════════════════════════════════════

class TestZoningCompleteness:
    """Verify zoning polygons fully represent Chicago's zoning map."""

    def test_zoning_polygon_count(self, zoning_gdf):
        """Chicago should have thousands of zoning polygons."""
        assert len(zoning_gdf) >= 1_000, (
            f"Only {len(zoning_gdf):,} zoning polygons — expected thousands."
        )

    def test_zoning_has_classification_column(self, zoning_gdf):
        """At least one zoning-classification column must be present."""
        candidates = {"zone_class", "ZONE_CLASS", "zone_type", "ZONE_TYPE",
                      "zoning_classification"}
        found = candidates & set(zoning_gdf.columns)
        assert found, (
            f"No zoning column found.  Available: {list(zoning_gdf.columns)}"
        )

    def test_all_zone_types_represented(self, zoning_gdf):
        """All 12 Chicago zone types should appear in the data."""
        zt_col = _find_column(zoning_gdf, ["zone_type", "ZONE_TYPE"])
        if zt_col is None:
            pytest.skip("No zone_type column in zoning data")

        actual_types = set(
            pd.to_numeric(zoning_gdf[zt_col], errors="coerce")
            .dropna().astype(int).unique()
        )
        missing = EXPECTED_ZONE_TYPES - actual_types
        # Allow at most 2 missing — very rare types might not download
        assert len(missing) <= 2, (
            f"Missing zone types: {missing}.  "
            f"Found: {sorted(actual_types)}."
        )

    def test_zoning_codes_match_reference(self, zoning_gdf, zoning_codes_df):
        """Most base zone codes in the reference table should appear in the data."""
        zc_col = _find_column(zoning_gdf, ["zone_class", "ZONE_CLASS"])
        if zc_col is None:
            pytest.skip("No zone_class column in zoning data")

        ref_base = {c.split(" ")[0] for c in
                    zoning_codes_df["district_type_code"].dropna().str.strip()}
        actual_base = {c.split(" ")[0] for c in
                       zoning_gdf[zc_col].dropna().astype(str).str.strip()}

        matched = ref_base & actual_base
        match_rate = len(matched) / len(ref_base) if ref_base else 0
        assert match_rate > 0.50, (
            f"Only {match_rate:.0%} of reference zoning codes found in data. "
            f"Missing: {sorted(ref_base - actual_base)[:10]}"
        )

    def test_zoning_geometries_are_polygons(self, zoning_gdf):
        """Zoning geometries must be Polygon or MultiPolygon."""
        valid = {"Polygon", "MultiPolygon"}
        invalid = set(zoning_gdf.geometry.geom_type.unique()) - valid
        assert not invalid, f"Unexpected geometry types: {invalid}"


# ═════════════════════════════════════════════════════════════════════════════
# 4. TRANSIT DATA COMPLETENESS
# ═════════════════════════════════════════════════════════════════════════════

class TestTransitCompleteness:
    """Verify CTA L, bus, and Metra datasets are complete."""

    def test_cta_stop_count(self, cta_stations_gdf):
        """CTA L stop count should be consistent with the 146-station network."""
        count = len(cta_stations_gdf)
        assert count >= CTA_L_STATION_COUNT, (
            f"Only {count} CTA L stops/stations. "
            f"The network has {CTA_L_STATION_COUNT} stations "
            f"(~{CTA_L_STOPS_MIN}+ directional stops)."
        )

    def test_cta_stations_within_service_area(self, cta_stations_gdf):
        """All CTA stations should be in the greater Chicago area."""
        minx, miny, maxx, maxy = cta_stations_gdf.total_bounds
        assert minx >= -88.10, f"Stations extend too far west ({minx})"
        assert maxx <= -87.50, f"Stations extend too far east ({maxx})"
        assert miny >= 41.70, f"Stations extend too far south ({miny})"
        assert maxy <= 42.10, f"Stations extend too far north ({maxy})"

    def test_cta_bus_route_count(self):
        """CTA should have at least 100 bus routes."""
        _skip_if_missing(CTA_BUS_ROUTES_GEOJSON)
        gdf = gpd.read_file(CTA_BUS_ROUTES_GEOJSON)
        assert len(gdf) >= 100, (
            f"Only {len(gdf)} bus routes — CTA operates ~120+."
        )

    def test_metra_station_count(self):
        """Metra should have a substantial number of stations."""
        _skip_if_missing(METRA_STATIONS_GEOJSON)
        gdf = gpd.read_file(METRA_STATIONS_GEOJSON)
        assert len(gdf) >= 50, (
            f"Only {len(gdf)} Metra stations — expected >= 50."
        )


# ═════════════════════════════════════════════════════════════════════════════
# 5. CENSUS TRACT COMPLETENESS
# ═════════════════════════════════════════════════════════════════════════════

class TestCensusTractCompleteness:
    """Verify Cook County census tract coverage."""

    def test_tract_count(self, census_tracts_gdf):
        """Cook County should have ~1,300+ census tracts."""
        assert len(census_tracts_gdf) >= COOK_COUNTY_MIN_CENSUS_TRACTS, (
            f"Only {len(census_tracts_gdf):,} tracts — "
            f"Cook County has ~1,300+."
        )

    def test_tracts_are_cook_county(self, census_tracts_gdf):
        """Every tract should belong to Cook County (FIPS 031)."""
        if "COUNTYFP" not in census_tracts_gdf.columns:
            pytest.skip("No COUNTYFP column")
        bad = census_tracts_gdf[
            census_tracts_gdf["COUNTYFP"] != COOK_COUNTY_FIPS
        ]
        assert len(bad) == 0, (
            f"{len(bad)} tracts have a non-Cook-County FIPS code."
        )

    def test_geoid_format(self, census_tracts_gdf):
        """GEOIDs should start with '17031' (IL + Cook County FIPS)."""
        if "GEOID" not in census_tracts_gdf.columns:
            pytest.skip("No GEOID column")
        prefix = f"{ILLINOIS_FIPS}{COOK_COUNTY_FIPS}"
        bad = census_tracts_gdf[
            ~census_tracts_gdf["GEOID"].astype(str).str.startswith(prefix)
        ]
        assert len(bad) == 0, (
            f"{len(bad)} tracts have GEOIDs not starting with '{prefix}'."
        )

    def test_tract_geometries_are_polygons(self, census_tracts_gdf):
        """Census tract geometries must be Polygon or MultiPolygon."""
        valid = {"Polygon", "MultiPolygon"}
        invalid = set(census_tracts_gdf.geometry.geom_type.unique()) - valid
        assert not invalid, f"Unexpected geometry types: {invalid}"


# ═════════════════════════════════════════════════════════════════════════════
# 6. CROSS-DATASET SPATIAL CONSISTENCY
# ═════════════════════════════════════════════════════════════════════════════

class TestCrossDatasetConsistency:
    """Validate spatial alignment across the different datasets."""

    def test_cta_stations_within_census_tracts(
        self, cta_stations_gdf, census_tracts_gdf
    ):
        """Most CTA stations should fall inside a census tract polygon."""
        if cta_stations_gdf.crs != census_tracts_gdf.crs:
            census_tracts_gdf = census_tracts_gdf.to_crs(cta_stations_gdf.crs)

        joined = gpd.sjoin(
            cta_stations_gdf, census_tracts_gdf, how="left", predicate="within"
        )
        matched = joined["index_right"].notna().sum()
        rate = matched / len(cta_stations_gdf)
        assert rate > 0.80, (
            f"Only {rate:.0%} of CTA stations fall within a census tract. "
            f"Spatial layers may be misaligned."
        )

    def test_parcel_and_zoning_extent_overlap(self, parcels_gdf, zoning_gdf):
        """Parcel and zoning bounding boxes should overlap substantially."""
        pb = parcels_gdf.total_bounds
        zb = zoning_gdf.total_bounds

        x_overlap = min(pb[2], zb[2]) - max(pb[0], zb[0])
        y_overlap = min(pb[3], zb[3]) - max(pb[1], zb[1])

        assert x_overlap > 0.1, (
            f"Longitude overlap is only {x_overlap:.4f}° — "
            f"parcels and zoning may cover different areas."
        )
        assert y_overlap > 0.1, (
            f"Latitude overlap is only {y_overlap:.4f}° — "
            f"parcels and zoning may cover different areas."
        )

    def test_enriched_parcels_have_zoning(self, enriched_gdf):
        """After the spatial join, most enriched parcels should have a zone class."""
        zc_col = _find_column(enriched_gdf, ["zone_class", "ZONE_CLASS"])
        if zc_col is None:
            pytest.skip("No zone_class in enriched data")

        rate = enriched_gdf[zc_col].notna().sum() / len(enriched_gdf)
        assert rate > 0.70, (
            f"Only {rate:.0%} of enriched parcels have zone_class — "
            f"spatial join may be failing for many parcels."
        )


# ═════════════════════════════════════════════════════════════════════════════
# 7. REFERENCE DATA INTEGRITY
# ═════════════════════════════════════════════════════════════════════════════

class TestReferenceDataIntegrity:
    """Validate the small reference / lookup tables checked into git."""

    def test_zoning_codes_cover_all_zone_types(self, zoning_codes_df):
        """The reference table should list entries for all 12 zone types."""
        actual = set(zoning_codes_df["zone_type"].dropna().astype(int).unique())
        missing = EXPECTED_ZONE_TYPES - actual
        assert not missing, f"Missing zone types in reference: {missing}"

    def test_zoning_codes_have_far_values(self, zoning_codes_df):
        """Most zoning codes should have a numeric floor-area-ratio."""
        if "floor_area_ratio" not in zoning_codes_df.columns:
            pytest.skip("No floor_area_ratio column")

        numeric_far = pd.to_numeric(
            zoning_codes_df["floor_area_ratio"], errors="coerce"
        )
        rate = numeric_far.notna().sum() / len(zoning_codes_df)
        # PD and some special districts say "Varies" — allow for that
        assert rate > 0.50, (
            f"Only {rate:.0%} of zoning codes have a numeric FAR."
        )

    def test_no_duplicate_district_codes(self, zoning_codes_df):
        """Each district_type_code should appear exactly once."""
        dupes = zoning_codes_df["district_type_code"].duplicated().sum()
        assert dupes == 0, (
            f"{dupes} duplicate district_type_code(s) in reference table."
        )

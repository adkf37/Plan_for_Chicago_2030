"""
Unit tests for zoning classification and analysis module.

Tests spatial join logic, zone categorization, transit proximity,
and upzoning candidate detection.
"""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, box


@pytest.fixture
def sample_parcels():
    """Create sample parcel GeoDataFrame for testing."""
    parcels = gpd.GeoDataFrame({
        "pin": ["001", "002", "003", "004", "005"],
        "address": ["100 Main St", "200 Oak Ave", "300 Elm St", "400 Park Blvd", "500 Lake Dr"],
    }, geometry=[
        Point(-87.630, 41.880),  # Parcel 1 - in zone A
        Point(-87.625, 41.880),  # Parcel 2 - in zone A
        Point(-87.620, 41.880),  # Parcel 3 - in zone B
        Point(-87.615, 41.880),  # Parcel 4 - in zone B
        Point(-87.610, 41.880),  # Parcel 5 - outside zones
    ], crs="EPSG:4326")
    return parcels


@pytest.fixture
def sample_zoning():
    """Create sample zoning polygon GeoDataFrame for testing."""
    zoning = gpd.GeoDataFrame({
        "zone_class": ["RS-3", "RM-5"],
        "zone_type": [4, 4],  # Both residential
    }, geometry=[
        box(-87.632, 41.878, -87.622, 41.882),  # Zone A (RS-3)
        box(-87.622, 41.878, -87.612, 41.882),  # Zone B (RM-5)
    ], crs="EPSG:4326")
    return zoning


@pytest.fixture
def sample_stations():
    """Create sample CTA station GeoDataFrame for testing."""
    stations = gpd.GeoDataFrame({
        "station_name": ["Test Station 1", "Test Station 2"],
    }, geometry=[
        Point(-87.628, 41.880),  # Station near parcels 1-2
        Point(-87.618, 41.880),  # Station near parcels 3-4
    ], crs="EPSG:4326")
    return stations


@pytest.fixture
def sample_zoning_codes():
    """Create sample zoning codes reference DataFrame."""
    return pd.DataFrame({
        "district_type_code": ["RS-3", "RM-5", "B1-2"],
        "zone_type": [4, 4, 1],
        "floor_area_ratio": [0.9, 2.0, 2.2],
        "maximum_building_height": ["30 ft", "47 ft", "45 ft"],
    })


class TestSpatialJoin:
    """Tests for spatial_join_parcels_to_zoning function."""
    
    def test_spatial_join_basic(self, sample_parcels, sample_zoning):
        """Spatial join should match parcels to correct zones."""
        from src.zoning import spatial_join_parcels_to_zoning
        
        result = spatial_join_parcels_to_zoning(sample_parcels, sample_zoning)
        
        assert result is not None
        assert len(result) == 5
        assert "zone_class" in result.columns
        
        # Parcels 1-2 should be in RS-3
        assert result.loc[result["pin"] == "001", "zone_class"].values[0] == "RS-3"
        assert result.loc[result["pin"] == "002", "zone_class"].values[0] == "RS-3"
        
        # Parcels 3-4 should be in RM-5
        assert result.loc[result["pin"] == "003", "zone_class"].values[0] == "RM-5"
        assert result.loc[result["pin"] == "004", "zone_class"].values[0] == "RM-5"
    
    def test_spatial_join_handles_unmatched_parcels(self, sample_parcels, sample_zoning):
        """Parcels outside zoning polygons should have NaN zone_class."""
        from src.zoning import spatial_join_parcels_to_zoning
        
        result = spatial_join_parcels_to_zoning(sample_parcels, sample_zoning)
        
        # Parcel 5 is outside all zones
        parcel_5_zone = result.loc[result["pin"] == "005", "zone_class"].values[0]
        assert pd.isna(parcel_5_zone)
    
    def test_spatial_join_handles_empty_parcels(self, sample_zoning):
        """Spatial join should handle empty parcels GeoDataFrame."""
        from src.zoning import spatial_join_parcels_to_zoning
        
        empty_parcels = gpd.GeoDataFrame(columns=["pin", "geometry"], geometry="geometry", crs="EPSG:4326")
        result = spatial_join_parcels_to_zoning(empty_parcels, sample_zoning)
        
        assert result is None
    
    def test_spatial_join_handles_none(self):
        """Spatial join should handle None inputs."""
        from src.zoning import spatial_join_parcels_to_zoning
        
        result = spatial_join_parcels_to_zoning(None, None)
        assert result is None


class TestZoneCategory:
    """Tests for add_zone_category function."""
    
    def test_add_zone_category_maps_correctly(self):
        """Zone categories should be mapped correctly from zone_type."""
        from src.zoning import add_zone_category, ZONE_TYPE_TO_CATEGORY
        
        gdf = gpd.GeoDataFrame({
            "zone_type": [1, 2, 3, 4, 5, 6, 7, 12],
        }, geometry=[Point(0, 0)] * 8, crs="EPSG:4326")
        
        result = add_zone_category(gdf)
        
        assert result["zone_category"].tolist() == [
            "Commercial",   # 1 - Business
            "Commercial",   # 2 - Commercial/Mixed-Use
            "Industrial",   # 3 - Manufacturing
            "Residential",  # 4 - Residential
            "Mixed",        # 5 - Planned Development
            "Industrial",   # 6 - Planned Manufacturing
            "Mixed",        # 7 - Downtown Mixed-Use
            "Parks",        # 12 - Parks and Open Space
        ]
    
    def test_add_zone_category_handles_missing_column(self):
        """Should return 'Unknown' when zone_type column is missing."""
        from src.zoning import add_zone_category
        
        gdf = gpd.GeoDataFrame({
            "zone_class": ["RS-3", "RM-5"],
        }, geometry=[Point(0, 0)] * 2, crs="EPSG:4326")
        
        result = add_zone_category(gdf)
        
        assert all(result["zone_category"] == "Unknown")
    
    def test_add_zone_category_handles_none(self):
        """Should return None when input is None."""
        from src.zoning import add_zone_category
        
        result = add_zone_category(None)
        assert result is None


class TestZoningEnrichment:
    """Tests for enrich_with_zoning_codes function."""
    
    def test_enrich_adds_far(self, sample_parcels, sample_zoning, sample_zoning_codes):
        """Enrichment should add FAR from zoning codes."""
        from src.zoning import spatial_join_parcels_to_zoning, enrich_with_zoning_codes
        
        # First join parcels to zoning
        joined = spatial_join_parcels_to_zoning(sample_parcels, sample_zoning)
        
        # Then enrich
        result = enrich_with_zoning_codes(joined, sample_zoning_codes)
        
        assert "far" in result.columns
        
        # RS-3 parcels should have FAR 0.9
        rs3_parcels = result[result["zone_class"] == "RS-3"]
        assert all(rs3_parcels["far"] == 0.9)
        
        # RM-5 parcels should have FAR 2.0
        rm5_parcels = result[result["zone_class"] == "RM-5"]
        assert all(rm5_parcels["far"] == 2.0)
    
    def test_enrich_adds_max_height(self, sample_parcels, sample_zoning, sample_zoning_codes):
        """Enrichment should add max_height from zoning codes."""
        from src.zoning import spatial_join_parcels_to_zoning, enrich_with_zoning_codes
        
        joined = spatial_join_parcels_to_zoning(sample_parcels, sample_zoning)
        result = enrich_with_zoning_codes(joined, sample_zoning_codes)
        
        assert "max_height" in result.columns


class TestTransitProximity:
    """Tests for identify_transit_corridor_parcels function."""
    
    def test_identifies_parcels_near_transit(self, sample_parcels, sample_stations):
        """Should identify parcels within buffer of transit stations."""
        from src.zoning import identify_transit_corridor_parcels
        
        # Use a large buffer to ensure some matches
        result = identify_transit_corridor_parcels(
            sample_parcels, sample_stations, buffer_meters=1000
        )
        
        assert "near_transit" in result.columns
        # At least some parcels should be near transit
        assert result["near_transit"].sum() > 0
    
    def test_handles_none_stations(self, sample_parcels):
        """Should return original parcels when stations is None."""
        from src.zoning import identify_transit_corridor_parcels
        
        result = identify_transit_corridor_parcels(sample_parcels, None)
        
        # Should return original without near_transit column
        assert len(result) == len(sample_parcels)


class TestUpzoningCandidates:
    """Tests for identify_upzoning_candidates function."""
    
    def test_identifies_low_density_near_transit(self):
        """Low-density zones near transit should be candidates."""
        from src.zoning import identify_upzoning_candidates, LOW_DENSITY_ZONES
        
        gdf = gpd.GeoDataFrame({
            "zone_class": ["RS-3", "RS-3", "RM-5", "RM-5"],
            "near_transit": [True, False, True, False],
        }, geometry=[Point(0, 0)] * 4, crs="EPSG:4326")
        
        result = identify_upzoning_candidates(gdf)
        
        assert "upzoning_candidate" in result.columns
        assert "upzoning_reason" in result.columns
        
        # Only RS-3 near transit should be a candidate
        assert result.iloc[0]["upzoning_candidate"] == True
        assert result.iloc[1]["upzoning_candidate"] == False  # RS-3 but not near transit
        assert result.iloc[2]["upzoning_candidate"] == False  # RM-5 (not low density)
        assert result.iloc[3]["upzoning_candidate"] == False
    
    def test_handles_missing_near_transit_column(self):
        """Should handle case when near_transit column is missing."""
        from src.zoning import identify_upzoning_candidates
        
        gdf = gpd.GeoDataFrame({
            "zone_class": ["RS-3", "RM-5"],
        }, geometry=[Point(0, 0)] * 2, crs="EPSG:4326")
        
        result = identify_upzoning_candidates(gdf)
        
        # Should still work but no candidates found
        assert "upzoning_candidate" in result.columns
        assert result["upzoning_candidate"].sum() == 0


class TestZoneSummary:
    """Tests for calculate_zone_summary function."""
    
    def test_calculates_parcel_counts(self, sample_parcels, sample_zoning):
        """Summary should include parcel counts per zone."""
        from src.zoning import spatial_join_parcels_to_zoning, calculate_zone_summary
        
        joined = spatial_join_parcels_to_zoning(sample_parcels, sample_zoning)
        summary = calculate_zone_summary(joined)
        
        assert "zone_class" in summary.columns
        assert "parcel_count" in summary.columns
        
        # Check counts
        rs3_count = summary.loc[summary["zone_class"] == "RS-3", "parcel_count"].values[0]
        rm5_count = summary.loc[summary["zone_class"] == "RM-5", "parcel_count"].values[0]
        
        assert rs3_count == 2  # Parcels 1-2
        assert rm5_count == 2  # Parcels 3-4
    
    def test_handles_none_input(self):
        """Should return empty DataFrame for None input."""
        from src.zoning import calculate_zone_summary
        
        result = calculate_zone_summary(None)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestLegacyFunctions:
    """Tests for backward-compatible legacy functions."""
    
    def test_classify_existing_density(self, sample_parcels):
        """classify_existing_density should add density category column."""
        from src.zoning import classify_existing_density
        
        # Add zone_category for testing
        sample_parcels["zone_category"] = "Residential"
        
        result = classify_existing_density(sample_parcels)
        
        assert "existing_density_category" in result.columns
    
    def test_generate_proposed_zoning_applies_rules(self, sample_zoning):
        """generate_proposed_zoning should apply upzoning rules."""
        from src.zoning import generate_proposed_zoning
        
        rules = {"RS-3": "RM-5"}  # Upzone RS-3 to RM-5
        
        result = generate_proposed_zoning(sample_zoning, rules)
        
        assert "proposed_zoning_class" in result.columns
        
        # RS-3 should now be proposed as RM-5
        rs3_proposed = result.loc[result["zone_class"] == "RS-3", "proposed_zoning_class"].values[0]
        assert rs3_proposed == "RM-5"
        
        # RM-5 should stay RM-5
        rm5_proposed = result.loc[result["zone_class"] == "RM-5", "proposed_zoning_class"].values[0]
        assert rm5_proposed == "RM-5"

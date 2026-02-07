"""
Integration tests for download_data module.

Tests the data download pipeline with mocked Socrata API responses
to verify that output files are created correctly.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon


# Sample GeoJSON response for mocking
MOCK_GEOJSON_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"pin": "1234567890", "class": "2-99"},
            "geometry": {"type": "Point", "coordinates": [-87.6298, 41.8781]}
        },
        {
            "type": "Feature",
            "properties": {"pin": "0987654321", "class": "2-11"},
            "geometry": {"type": "Point", "coordinates": [-87.6250, 41.8800]}
        }
    ]
}

MOCK_ZONING_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"zone_class": "RS-3", "zone_type": "4"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-87.63, 41.87], [-87.62, 41.87],
                    [-87.62, 41.88], [-87.63, 41.88], [-87.63, 41.87]
                ]]
            }
        }
    ]
}

MOCK_CTA_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"station_name": "Clark/Lake", "lines": "Blue,Brown,Green,Orange,Pink,Purple"},
            "geometry": {"type": "Point", "coordinates": [-87.6308, 41.8858]}
        }
    ] * 120  # Simulate 120 stations to pass validation
}


@pytest.fixture
def temp_data_dirs(tmp_path):
    """Create temporary data directories for testing."""
    geojson_dir = tmp_path / "data" / "geojson"
    geojson_dir.mkdir(parents=True)
    
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    
    processed_dir = tmp_path / "data" / "processed"
    processed_dir.mkdir(parents=True)
    
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    
    return {
        "root": tmp_path,
        "geojson": geojson_dir,
        "raw": raw_dir,
        "processed": processed_dir,
        "cache": cache_dir,
    }


@pytest.fixture
def mock_config(temp_data_dirs):
    """Patch config paths to use temporary directories."""
    from src import config
    
    original_geojson_dir = config.GEOJSON_DIR
    original_parcel = config.PARCEL_GEOJSON
    original_assessment = config.ASSESSMENT_GEOJSON
    original_zoning = config.ZONING_GEOJSON
    original_cta = config.CTA_STATIONS_GEOJSON
    original_census = config.CENSUS_TRACTS_GEOJSON
    original_cache = config.CACHE_DIR
    
    config.GEOJSON_DIR = temp_data_dirs["geojson"]
    config.PARCEL_GEOJSON = temp_data_dirs["geojson"] / "parcel_data.geojson"
    config.ASSESSMENT_GEOJSON = temp_data_dirs["geojson"] / "assessment_data.geojson"
    config.ZONING_GEOJSON = temp_data_dirs["geojson"] / "zoning_data.geojson"
    config.CTA_STATIONS_GEOJSON = temp_data_dirs["geojson"] / "cta_stations.geojson"
    config.CENSUS_TRACTS_GEOJSON = temp_data_dirs["geojson"] / "census_tracts.geojson"
    config.CACHE_DIR = temp_data_dirs["cache"]
    
    yield temp_data_dirs
    
    # Restore original paths
    config.GEOJSON_DIR = original_geojson_dir
    config.PARCEL_GEOJSON = original_parcel
    config.ASSESSMENT_GEOJSON = original_assessment
    config.ZONING_GEOJSON = original_zoning
    config.CTA_STATIONS_GEOJSON = original_cta
    config.CENSUS_TRACTS_GEOJSON = original_census
    config.CACHE_DIR = original_cache


def create_mock_response(json_data, status_code=200):
    """Create a mock requests response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text = json.dumps(json_data)
    mock_resp.json.return_value = json_data
    mock_resp.headers = {"ETag": "test-etag", "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@patch("src.data_utils.requests.get")
@patch("src.data_utils.requests.head")
def test_fetch_all_socrata_data_creates_geodataframe(mock_head, mock_get):
    """fetch_all_socrata_data should return a GeoDataFrame for GeoJSON endpoints."""
    from src.data_utils import fetch_all_socrata_data
    
    # Mock HEAD request (cache check)
    mock_head.return_value = create_mock_response({}, status_code=200)
    
    # Mock GET request
    mock_get.return_value = create_mock_response(MOCK_GEOJSON_RESPONSE)
    
    result = fetch_all_socrata_data("https://example.com/resource/test.geojson", use_cache=False)
    
    assert result is not None
    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) == 2
    assert "pin" in result.columns


@patch("src.data_utils.requests.get")
@patch("src.data_utils.requests.head")
def test_fetch_parcel_data(mock_head, mock_get, mock_config):
    """Parcel data download should create geojson file."""
    from src.data_utils import fetch_all_socrata_data
    from src import config
    
    mock_head.return_value = create_mock_response({}, status_code=200)
    mock_get.return_value = create_mock_response(MOCK_GEOJSON_RESPONSE)
    
    result = fetch_all_socrata_data("https://example.com/parcels.geojson", use_cache=False)
    
    assert result is not None
    output_path = mock_config["geojson"] / "test_parcels.geojson"
    result.to_file(str(output_path), driver="GeoJSON")
    
    assert output_path.exists()
    
    # Verify file can be read back
    loaded = gpd.read_file(output_path)
    assert len(loaded) == len(result)


@patch("src.data_utils.requests.get")
@patch("src.data_utils.requests.head")
def test_fetch_zoning_data(mock_head, mock_get, mock_config):
    """Zoning data download should create polygon geojson file."""
    from src.data_utils import fetch_all_socrata_data
    
    mock_head.return_value = create_mock_response({}, status_code=200)
    mock_get.return_value = create_mock_response(MOCK_ZONING_RESPONSE)
    
    result = fetch_all_socrata_data("https://example.com/zoning.geojson", use_cache=False)
    
    assert result is not None
    assert "zone_class" in result.columns
    # Verify it's polygon geometry
    assert result.geometry.iloc[0].geom_type == "Polygon"


def test_validate_dataframe_catches_missing_columns():
    """validate_dataframe should report missing required columns."""
    from src.data_utils import validate_dataframe
    
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    
    errors = validate_dataframe(df, "TestData", required_columns=["a", "c", "d"])
    
    assert len(errors) == 1
    assert "Missing required columns" in errors[0]
    assert "c" in errors[0] or "d" in errors[0]


def test_validate_dataframe_catches_low_row_count():
    """validate_dataframe should report when row count is too low."""
    from src.data_utils import validate_dataframe
    
    df = pd.DataFrame({"a": [1, 2]})
    
    errors = validate_dataframe(df, "TestData", min_rows=100)
    
    assert len(errors) == 1
    assert "Expected at least 100 rows" in errors[0]


def test_validate_dataframe_passes_valid_data():
    """validate_dataframe should return empty list for valid data."""
    from src.data_utils import validate_dataframe
    
    df = pd.DataFrame({"a": range(100), "b": range(100)})
    
    errors = validate_dataframe(df, "TestData", required_columns=["a", "b"], min_rows=50)
    
    assert errors == []


@patch("src.data_utils.requests.get")
@patch("src.data_utils.requests.head")
def test_caching_saves_metadata(mock_head, mock_get, mock_config):
    """Caching should save ETag and Last-Modified metadata."""
    from src.data_utils import fetch_all_socrata_data, _get_cache_key, _get_cache_metadata_path
    from src import config
    
    mock_head.return_value = create_mock_response({}, status_code=200)
    
    mock_resp = create_mock_response(MOCK_GEOJSON_RESPONSE)
    mock_resp.headers = {"ETag": "abc123", "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
    mock_get.return_value = mock_resp
    
    url = "https://example.com/cached.geojson"
    result = fetch_all_socrata_data(url, use_cache=True)
    
    assert result is not None
    
    # Check metadata file was created
    cache_key = _get_cache_key(url)
    meta_path = _get_cache_metadata_path(cache_key)
    
    assert meta_path.exists()
    
    with open(meta_path) as f:
        metadata = json.load(f)
    
    assert metadata["etag"] == "abc123"


@patch("src.download_data.fetch_all_socrata_data")
@patch("src.download_data.download_census_tracts")
def test_download_all_datasets_creates_files(mock_census, mock_fetch, mock_config):
    """download_all_datasets should create all expected output files."""
    from src.download_data import download_all_datasets
    from src import config
    
    # Create mock GeoDataFrames
    mock_parcel_gdf = gpd.GeoDataFrame(
        {"pin": ["123", "456"] * 1000},
        geometry=[Point(-87.6, 41.8)] * 2000,
        crs="EPSG:4326"
    )
    mock_zoning_gdf = gpd.GeoDataFrame(
        {"zone_class": ["RS-3"] * 100},
        geometry=[Polygon([(-87.63, 41.87), (-87.62, 41.87), (-87.62, 41.88), (-87.63, 41.88)])] * 100,
        crs="EPSG:4326"
    )
    mock_cta_gdf = gpd.GeoDataFrame(
        {"station_name": ["Test"] * 120},
        geometry=[Point(-87.6, 41.8)] * 120,
        crs="EPSG:4326"
    )
    
    # Configure mock to return appropriate data based on URL
    def mock_fetch_side_effect(url, *args, **kwargs):
        if "parcel" in url.lower() or "nj4t" in url.lower():
            return mock_parcel_gdf
        elif "zoning" in url.lower() or "dj47" in url.lower():
            return mock_zoning_gdf
        elif "assessment" in url.lower() or "uzyt" in url.lower():
            return mock_parcel_gdf  # Use same as parcels for simplicity
        elif "cta" in url.lower() or "8pix" in url.lower():
            return mock_cta_gdf
        return None
    
    mock_fetch.side_effect = mock_fetch_side_effect
    
    # Mock census tract download
    mock_census_gdf = gpd.GeoDataFrame(
        {"GEOID": ["17031010100"] * 1000, "COUNTYFP": ["031"] * 1000},
        geometry=[Polygon([(-87.63, 41.87), (-87.62, 41.87), (-87.62, 41.88), (-87.63, 41.88)])] * 1000,
        crs="EPSG:4326"
    )
    mock_census.return_value = mock_census_gdf
    
    # Run the download
    result = download_all_datasets()
    
    # Check files were created
    assert config.PARCEL_GEOJSON.exists(), "Parcel GeoJSON not created"
    assert config.ZONING_GEOJSON.exists(), "Zoning GeoJSON not created"
    assert config.CTA_STATIONS_GEOJSON.exists(), "CTA stations GeoJSON not created"
    assert config.CENSUS_TRACTS_GEOJSON.exists(), "Census tracts GeoJSON not created"
    
    # Verify file contents
    parcels = gpd.read_file(config.PARCEL_GEOJSON)
    assert len(parcels) > 0

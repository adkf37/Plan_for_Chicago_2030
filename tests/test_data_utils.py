"""
Smoke tests for data_utils module.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_config_paths_exist():
    """Verify config module exports all expected path constants."""
    from src.config import (
        PROJECT_ROOT, RAW_DIR, GEOJSON_DIR,
        PROCESSED_DIR, REFERENCE_DIR, MAPS_DIR, REPORTS_DIR,
    )
    assert PROJECT_ROOT.is_dir()
    assert RAW_DIR == PROJECT_ROOT / "data" / "raw"


def test_ensure_dirs_creates_directories(tmp_path):
    """ensure_dirs() should create all configured directories."""
    from src import config
    # Temporarily override PROJECT_ROOT
    original = config.PROJECT_ROOT
    original_raw = config.RAW_DIR
    original_geojson = config.GEOJSON_DIR
    original_processed = config.PROCESSED_DIR
    original_reference = config.REFERENCE_DIR
    original_maps = config.MAPS_DIR
    original_reports = config.REPORTS_DIR
    original_viz = config.VISUALIZATIONS_DIR
    original_analysis = config.ANALYSIS_RESULTS_DIR
    original_cache = config.CACHE_DIR
    original_historical = config.RAW_HISTORICAL_DIR
    original_uplift = config.UPLIFT_SCENARIOS_DIR
    original_hist_data = config.HISTORICAL_DATA_DIR
    
    config.PROJECT_ROOT = tmp_path
    config.RAW_DIR = tmp_path / "data" / "raw"
    config.RAW_HISTORICAL_DIR = config.RAW_DIR / "historical"
    config.GEOJSON_DIR = tmp_path / "data" / "geojson"
    config.PROCESSED_DIR = tmp_path / "data" / "processed"
    config.REFERENCE_DIR = tmp_path / "data" / "reference"
    config.HISTORICAL_DATA_DIR = config.PROCESSED_DIR / "historical_data"
    config.UPLIFT_SCENARIOS_DIR = config.PROCESSED_DIR / "uplift_scenarios"
    config.MAPS_DIR = tmp_path / "maps"
    config.REPORTS_DIR = tmp_path / "reports"
    config.VISUALIZATIONS_DIR = config.REPORTS_DIR / "visualizations"
    config.ANALYSIS_RESULTS_DIR = tmp_path / "analysis_results"
    config.CACHE_DIR = tmp_path / "cache"

    config.ensure_dirs()

    assert config.RAW_DIR.is_dir()
    assert config.GEOJSON_DIR.is_dir()
    assert config.MAPS_DIR.is_dir()

    # Restore
    config.PROJECT_ROOT = original
    config.RAW_DIR = original_raw
    config.GEOJSON_DIR = original_geojson
    config.PROCESSED_DIR = original_processed
    config.REFERENCE_DIR = original_reference
    config.MAPS_DIR = original_maps
    config.REPORTS_DIR = original_reports
    config.VISUALIZATIONS_DIR = original_viz
    config.ANALYSIS_RESULTS_DIR = original_analysis
    config.CACHE_DIR = original_cache
    config.RAW_HISTORICAL_DIR = original_historical
    config.UPLIFT_SCENARIOS_DIR = original_uplift
    config.HISTORICAL_DATA_DIR = original_hist_data


@patch("src.data_utils.requests.get")
@patch("src.data_utils.requests.head")
def test_fetch_all_socrata_data_single_page(mock_head, mock_get):
    """fetch_all_socrata_data returns records from a single page."""
    from src.data_utils import fetch_all_socrata_data

    # Mock HEAD request for cache check
    mock_head_resp = MagicMock()
    mock_head_resp.status_code = 200
    mock_head.return_value = mock_head_resp

    # Mock GET request
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"pin": "1234"}]
    mock_resp.text = '[{"pin": "1234"}]'
    mock_resp.headers = {"ETag": "test-etag", "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    result = fetch_all_socrata_data("https://example.com/resource/test.json", use_cache=False)
    assert len(result) >= 1
    assert result.iloc[0]["pin"] == "1234"

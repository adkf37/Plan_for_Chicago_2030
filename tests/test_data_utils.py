"""
Smoke tests for data_utils module.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


def test_config_paths_exist():
    """Verify config module exports all expected path constants."""
    from src.config import (
        PROJECT_ROOT, DATA_DIR, RAW_DIR, GEOJSON_DIR,
        PROCESSED_DIR, REFERENCE_DIR, MAPS_DIR, REPORTS_DIR,
    )
    assert PROJECT_ROOT.is_dir()
    assert DATA_DIR == PROJECT_ROOT / "data"


def test_ensure_dirs_creates_directories(tmp_path):
    """ensure_dirs() should create all configured directories."""
    from src import config
    # Temporarily override PROJECT_ROOT
    original = config.PROJECT_ROOT
    config.PROJECT_ROOT = tmp_path
    config.DATA_DIR = tmp_path / "data"
    config.RAW_DIR = config.DATA_DIR / "raw"
    config.GEOJSON_DIR = config.DATA_DIR / "geojson"
    config.PROCESSED_DIR = config.DATA_DIR / "processed"
    config.REFERENCE_DIR = config.DATA_DIR / "reference"
    config.MAPS_DIR = tmp_path / "maps"
    config.REPORTS_DIR = tmp_path / "reports"
    config.VISUALIZATIONS_DIR = config.REPORTS_DIR / "visualizations"
    config.ANALYSIS_RESULTS_DIR = tmp_path / "analysis_results"

    config.ensure_dirs()

    assert config.RAW_DIR.is_dir()
    assert config.GEOJSON_DIR.is_dir()
    assert config.MAPS_DIR.is_dir()

    # Restore
    config.PROJECT_ROOT = original


@patch("src.data_utils.requests.get")
def test_fetch_all_socrata_data_single_page(mock_get):
    """fetch_all_socrata_data returns records from a single page."""
    from src.data_utils import fetch_all_socrata_data

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [{"pin": "1234"}]
    mock_get.return_value = mock_resp

    result = fetch_all_socrata_data("https://example.com/resource/test.json")
    assert len(result) >= 1
    assert result[0]["pin"] == "1234"

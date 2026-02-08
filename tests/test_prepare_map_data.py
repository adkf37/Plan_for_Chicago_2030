"""
Tests for src/prepare_map_data.py  — Map Data Preparation (Epic 06)
===================================================================
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon, box

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tiny_zoning(tmp_path) -> Path:
    """Create a minimal zoning GeoJSON file."""
    gdf = gpd.GeoDataFrame(
        {
            "ZONE_CLASS": ["RS-3", "B1-2", "RM-5"],
            "ZONE_TYPE": [4, 1, 4],
            "geometry": [
                box(-87.64, 41.87, -87.63, 41.88),
                box(-87.63, 41.87, -87.62, 41.88),
                box(-87.62, 41.87, -87.61, 41.88),
            ],
        },
        crs="EPSG:4326",
    )
    p = tmp_path / "zoning_data.geojson"
    gdf.to_file(p, driver="GeoJSON")
    return p


@pytest.fixture
def tiny_enriched(tmp_path) -> Path:
    """Create minimal enriched parcels for proposed-zoning and values tests."""
    gdf = gpd.GeoDataFrame(
        {
            "pin": ["P1", "P2", "P3"],
            "zone_class": ["RS-3", "RS-1", "RM-5"],
            "near_transit": [True, True, False],
            "upzoning_candidate": [True, True, False],
            "geometry": [
                Point(-87.630, 41.875),
                Point(-87.625, 41.876),
                Point(-87.615, 41.877),
            ],
        },
        crs="EPSG:4326",
    )
    p = tmp_path / "parcels_enriched.geojson"
    gdf.to_file(p, driver="GeoJSON")
    return p


@pytest.fixture
def tiny_stations(tmp_path) -> Path:
    """Create minimal CTA station file."""
    gdf = gpd.GeoDataFrame(
        {
            "station_name": ["Alpha", "Beta"],
            "geometry": [Point(-87.629, 41.879), Point(-87.636, 41.878)],
        },
        crs="EPSG:4326",
    )
    p = tmp_path / "cta_stations.geojson"
    gdf.to_file(p, driver="GeoJSON")
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# _simplify_gdf
# ---------------------------------------------------------------------------

def test_simplify_preserves_row_count():
    from src.prepare_map_data import _simplify_gdf
    gdf = gpd.GeoDataFrame(
        {"geometry": [box(0, 0, 1, 1), box(1, 0, 2, 1)]},
        crs="EPSG:4326",
    )
    result = _simplify_gdf(gdf)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# _truncate_coords
# ---------------------------------------------------------------------------

def test_truncate_rounds_coordinates():
    from src.prepare_map_data import _truncate_coords
    gj = {"features": [{"geometry": {"coordinates": [[-87.62981234567, 41.87812345678]]}}]}
    result = _truncate_coords(gj, precision=4)
    coords = result["features"][0]["geometry"]["coordinates"][0]
    assert coords == [-87.6298, 41.8781]


# ---------------------------------------------------------------------------
# _save_geojson
# ---------------------------------------------------------------------------

def test_save_geojson_creates_file(tmp_path):
    from src.prepare_map_data import _save_geojson
    gdf = gpd.GeoDataFrame(
        {"name": ["A"], "geometry": [Point(0, 0)]},
        crs="EPSG:4326",
    )
    out = tmp_path / "out.geojson"
    _save_geojson(gdf, out)
    assert out.exists()
    data = _read(out)
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1


def test_save_geojson_samples_when_over_max(tmp_path):
    from src.prepare_map_data import _save_geojson
    gdf = gpd.GeoDataFrame(
        {"id": range(100), "geometry": [Point(i, 0) for i in range(100)]},
        crs="EPSG:4326",
    )
    out = tmp_path / "big.geojson"
    _save_geojson(gdf, out, max_features=10)
    data = _read(out)
    assert len(data["features"]) == 10


# ---------------------------------------------------------------------------
# export_zoning_layer
# ---------------------------------------------------------------------------

def test_export_zoning_layer(monkeypatch, tiny_zoning, tmp_path):
    import src.prepare_map_data as mod
    monkeypatch.setattr(mod, "ZONING_GEOJSON", tiny_zoning)
    out = mod.export_zoning_layer(tmp_path)
    assert out is not None and out.exists()
    data = _read(out)
    assert len(data["features"]) == 3
    props = data["features"][0]["properties"]
    assert "zone_name" in props
    assert "zone_color" in props


# ---------------------------------------------------------------------------
# export_proposed_zoning_layer
# ---------------------------------------------------------------------------

def test_export_proposed_zoning(monkeypatch, tiny_enriched, tmp_path):
    import src.prepare_map_data as mod
    monkeypatch.setattr(mod, "PARCELS_ENRICHED_GEOJSON", tiny_enriched)
    out = mod.export_proposed_zoning_layer(tmp_path)
    assert out is not None and out.exists()
    data = _read(out)
    # Check that near-transit RS-3 was upzoned to RT-4
    for feat in data["features"]:
        p = feat["properties"]
        if p.get("zone_class") == "RS-3":
            assert p["proposed_zone"] == "RT-4"
            assert p["changed"] is True
        elif p.get("zone_class") == "RS-1":
            assert p["proposed_zone"] == "RS-3"
            assert p["changed"] is True
        elif p.get("zone_class") == "RM-5":
            assert p["changed"] is False


# ---------------------------------------------------------------------------
# export_transit_layer
# ---------------------------------------------------------------------------

def test_export_transit_layer(monkeypatch, tiny_stations, tmp_path):
    import src.prepare_map_data as mod
    # Only CTA exists; Metra does not
    monkeypatch.setattr(mod, "CTA_STATIONS_GEOJSON", tiny_stations)
    monkeypatch.setattr(mod, "METRA_STATIONS_GEOJSON", tmp_path / "nonexistent.geojson")
    out = mod.export_transit_layer(tmp_path)
    assert out is not None and out.exists()
    data = _read(out)
    # 2 CTA + proposed extensions from config
    assert len(data["features"]) >= 2
    types = {f["properties"]["station_type"] for f in data["features"]}
    assert "CTA_L" in types
    assert "Proposed" in types


# ---------------------------------------------------------------------------
# export_value_layer
# ---------------------------------------------------------------------------

def test_export_value_layer(monkeypatch, tiny_enriched, tmp_path):
    import src.prepare_map_data as mod
    monkeypatch.setattr(mod, "PARCELS_ENRICHED_GEOJSON", tiny_enriched)
    monkeypatch.setattr(mod, "VALUE_PROJECTIONS_CSV", tmp_path / "nope.csv")
    monkeypatch.setattr(mod, "TRANSIT_SCORES_CSV", tmp_path / "nope2.csv")
    out = mod.export_value_layer(tmp_path)
    assert out is not None and out.exists()
    data = _read(out)
    assert len(data["features"]) == 3
    # Should keep pin column
    assert "pin" in data["features"][0]["properties"]


# ---------------------------------------------------------------------------
# prepare_all (integration)
# ---------------------------------------------------------------------------

def test_prepare_all_creates_manifest(monkeypatch, tiny_zoning, tiny_enriched, tiny_stations, tmp_path):
    import src.prepare_map_data as mod
    monkeypatch.setattr(mod, "ZONING_GEOJSON", tiny_zoning)
    monkeypatch.setattr(mod, "CHICAGO_ZONING_GEOJSON", tiny_zoning)
    monkeypatch.setattr(mod, "PARCELS_ENRICHED_GEOJSON", tiny_enriched)
    monkeypatch.setattr(mod, "CTA_STATIONS_GEOJSON", tiny_stations)
    monkeypatch.setattr(mod, "METRA_STATIONS_GEOJSON", tmp_path / "no.geojson")
    monkeypatch.setattr(mod, "VALUE_PROJECTIONS_CSV", tmp_path / "no.csv")
    monkeypatch.setattr(mod, "TRANSIT_SCORES_CSV", tmp_path / "no2.csv")

    out_dir = tmp_path / "site_data"
    results = mod.prepare_all(out_dir)

    # All 4 layers should have been exported
    for key in ("zoning", "proposed_zoning", "transit", "parcels"):
        assert results[key] is not None, f"{key} was not exported"

    # Manifest should exist
    manifest_path = out_dir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert "zoning" in manifest

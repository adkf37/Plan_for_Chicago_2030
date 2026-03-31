"""
Tests for src/transportation.py  — Transit & Walkability Scoring (Epic 05)
==========================================================================
Covers station loading, distance computation, tier assignment, walk-score
proxy, composite TOD score, and export.
"""

from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_parcels() -> gpd.GeoDataFrame:
    """Four parcels at known Chicago-area locations (WGS 84)."""
    return gpd.GeoDataFrame(
        {
            "pin": ["A", "B", "C", "D"],
            "zone_class": ["RS-3", "RT-4", "RM-5", "RS-1"],
            "geometry": [
                # ~200 m from a Loop station
                Point(-87.6298, 41.8781),
                # ~600 m away
                Point(-87.6350, 41.8781),
                # ~1200 m away
                Point(-87.6450, 41.8781),
                # ~3000 m away – far south
                Point(-87.6298, 41.8500),
            ],
        },
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_stations() -> gpd.GeoDataFrame:
    """Two fake stations near the Loop."""
    return gpd.GeoDataFrame(
        {
            "station_name": ["Station_Alpha", "Station_Beta"],
            "station_type": ["CTA_L", "Metra"],
            "geometry": [
                Point(-87.6298, 41.8790),  # very close to parcel A
                Point(-87.6400, 41.8790),  # between B and C
            ],
        },
        crs="EPSG:4326",
    )


# ---------------------------------------------------------------------------
# build_proposed_stations
# ---------------------------------------------------------------------------

def test_build_proposed_stations_not_empty():
    from src.transportation import build_proposed_stations
    gdf = build_proposed_stations()
    assert len(gdf) > 0
    assert "station_name" in gdf.columns
    assert "station_type" in gdf.columns
    assert (gdf["station_type"] == "Proposed").all()
    assert gdf.crs is not None


def test_build_proposed_stations_crs():
    from src.transportation import build_proposed_stations
    gdf = build_proposed_stations()
    assert gdf.crs.to_epsg() == 4326


# ---------------------------------------------------------------------------
# combine_stations
# ---------------------------------------------------------------------------

def test_combine_stations_proposed_only(monkeypatch):
    """If CTA / Metra files don't exist, still returns proposed stations."""
    from src import transportation as trans
    # Monkey-patch loaders to return None
    monkeypatch.setattr(trans, "load_cta_stations", lambda path=None: None)
    monkeypatch.setattr(trans, "load_metra_stations", lambda path=None: None)

    combined = trans.combine_stations(include_metra=True, include_proposed=True)
    assert len(combined) > 0
    assert (combined["station_type"] == "Proposed").all()


# ---------------------------------------------------------------------------
# compute_station_distances
# ---------------------------------------------------------------------------

def test_distance_columns_exist(sample_parcels, sample_stations):
    from src.transportation import compute_station_distances
    result = compute_station_distances(sample_parcels, sample_stations)

    for col in ("nearest_station", "station_distance_m", "nearest_station_type"):
        assert col in result.columns, f"Missing column {col}"


def test_distances_positive(sample_parcels, sample_stations):
    from src.transportation import compute_station_distances
    result = compute_station_distances(sample_parcels, sample_stations)
    assert (result["station_distance_m"] >= 0).all()


def test_nearest_station_is_alpha_for_parcel_a(sample_parcels, sample_stations):
    """Parcel A is closest to Station_Alpha by construction."""
    from src.transportation import compute_station_distances
    result = compute_station_distances(sample_parcels, sample_stations)
    a_row = result[result["pin"] == "A"].iloc[0]
    assert a_row["nearest_station"] == "Station_Alpha"


def test_distance_parcel_a_lt_400m(sample_parcels, sample_stations):
    """Parcel A is ~100 m from Station_Alpha → well under 400 m."""
    from src.transportation import compute_station_distances
    result = compute_station_distances(sample_parcels, sample_stations)
    a_dist = result.loc[result["pin"] == "A", "station_distance_m"].iloc[0]
    assert a_dist < 400


def test_empty_stations_returns_nan(sample_parcels):
    from src.transportation import compute_station_distances
    empty = gpd.GeoDataFrame(
        columns=["station_name", "station_type", "geometry"], crs="EPSG:4326"
    )
    result = compute_station_distances(sample_parcels, empty)
    assert result["station_distance_m"].isna().all()


def test_none_stations_returns_nan(sample_parcels):
    from src.transportation import compute_station_distances
    result = compute_station_distances(sample_parcels, None)
    assert result["station_distance_m"].isna().all()


# ---------------------------------------------------------------------------
# assign_transit_tiers
# ---------------------------------------------------------------------------

def test_tier_assignment_all_tiers(sample_parcels, sample_stations):
    from src.transportation import compute_station_distances, assign_transit_tiers
    scored = compute_station_distances(sample_parcels, sample_stations)
    tiered = assign_transit_tiers(scored)

    assert "transit_tier" in tiered.columns
    # Parcel A (< 400 m)
    assert "Tier 1" in tiered.loc[tiered["pin"] == "A", "transit_tier"].iloc[0]


def test_tier_no_distance_col():
    """If station_distance_m is absent, tier = Unknown."""
    from src.transportation import assign_transit_tiers
    gdf = gpd.GeoDataFrame({"geometry": [Point(0, 0)]}, crs="EPSG:4326")
    result = assign_transit_tiers(gdf)
    assert result["transit_tier"].iloc[0] == "Unknown"


def test_custom_tiers(sample_parcels, sample_stations):
    from src.transportation import compute_station_distances, assign_transit_tiers
    scored = compute_station_distances(sample_parcels, sample_stations)
    custom = [(0, 500, "Close"), (500, float("inf"), "Far")]
    tiered = assign_transit_tiers(scored, tiers=custom)
    assert set(tiered["transit_tier"].unique()).issubset({"Close", "Far", "Unknown"})


# ---------------------------------------------------------------------------
# compute_walk_score_proxy (without OSM — falls back to neutral 50)
# ---------------------------------------------------------------------------

def test_walk_score_fallback_without_osmnx(sample_parcels, monkeypatch):
    """When osmnx is not importable, every parcel gets 50."""
    import builtins
    real_import = builtins.__import__

    def block_osmnx(name, *args, **kwargs):
        if name == "osmnx":
            raise ImportError("mocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_osmnx)
    from src.transportation import compute_walk_score_proxy
    result = compute_walk_score_proxy(sample_parcels)
    assert (result["walk_score_proxy"] == 50.0).all()


# ---------------------------------------------------------------------------
# compute_tod_score
# ---------------------------------------------------------------------------

def test_tod_score_range(sample_parcels, sample_stations):
    from src.transportation import compute_station_distances, compute_tod_score
    scored = compute_station_distances(sample_parcels, sample_stations)
    scored["walk_score_proxy"] = 50.0
    result = compute_tod_score(scored)
    assert result["tod_score"].between(0, 100).all()


def test_tod_score_closer_is_higher(sample_parcels, sample_stations):
    """Parcel A (close) should have higher TOD score than parcel D (far)."""
    from src.transportation import compute_station_distances, compute_tod_score
    scored = compute_station_distances(sample_parcels, sample_stations)
    scored["walk_score_proxy"] = 50.0
    result = compute_tod_score(scored)
    tod_a = result.loc[result["pin"] == "A", "tod_score"].iloc[0]
    tod_d = result.loc[result["pin"] == "D", "tod_score"].iloc[0]
    assert tod_a > tod_d


def test_tod_score_zoning_gap_boost():
    """RS-3 parcel at same distance should score higher than RM-5 (zoning gap)."""
    from src.transportation import compute_tod_score
    gdf = gpd.GeoDataFrame(
        {
            "zone_class": ["RS-3", "RM-5"],
            "station_distance_m": [500, 500],
            "walk_score_proxy": [50, 50],
            "geometry": [Point(0, 0), Point(0, 0)],
        },
        crs="EPSG:4326",
    )
    result = compute_tod_score(gdf)
    assert result.iloc[0]["tod_score"] > result.iloc[1]["tod_score"]


def test_tod_score_weights_sum():
    """Custom weights should still produce 0-100 scores."""
    from src.transportation import compute_tod_score
    gdf = gpd.GeoDataFrame(
        {
            "station_distance_m": [100],
            "walk_score_proxy": [80],
            "zone_class": ["RS-1"],
            "geometry": [Point(0, 0)],
        },
        crs="EPSG:4326",
    )
    result = compute_tod_score(
        gdf, weight_transit=0.6, weight_walk=0.2, weight_zoning_gap=0.2
    )
    assert 0 <= result["tod_score"].iloc[0] <= 100


# ---------------------------------------------------------------------------
# score_parcels (integration — uses monkeypatch to skip file I/O)
# ---------------------------------------------------------------------------

def test_score_parcels_full_pipeline(sample_parcels, sample_stations, monkeypatch):
    from src import transportation as trans
    monkeypatch.setattr(
        trans, "combine_stations",
        lambda include_metra=True, include_proposed=False: sample_stations,
    )
    result = trans.score_parcels(
        sample_parcels, compute_walkability=False,
    )
    for col in ("nearest_station", "station_distance_m", "transit_tier",
                "walk_score_proxy", "tod_score"):
        assert col in result.columns


# ---------------------------------------------------------------------------
# export_transit_scores
# ---------------------------------------------------------------------------

def test_export_creates_csv(sample_parcels, sample_stations, tmp_path):
    from src.transportation import compute_station_distances, assign_transit_tiers, export_transit_scores
    scored = compute_station_distances(sample_parcels, sample_stations)
    scored = assign_transit_tiers(scored)
    scored["walk_score_proxy"] = 50.0
    scored["tod_score"] = 60.0
    out = tmp_path / "transit_scores.csv"
    export_transit_scores(scored, output_path=out)
    assert out.exists()
    df = pd.read_csv(out)
    assert len(df) == len(sample_parcels)
    assert "nearest_station" in df.columns


# ---------------------------------------------------------------------------
# visualise_transit_shed
# ---------------------------------------------------------------------------

def test_visualise_creates_html(sample_stations, tmp_path):
    from src.transportation import visualise_transit_shed
    out = tmp_path / "shed.html"
    visualise_transit_shed(stations=sample_stations, output_path=out)
    assert out.exists()
    html = out.read_text()
    assert "pydeck" in html.lower() or "deck.gl" in html.lower()

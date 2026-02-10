"""
Transit & Walkability Scoring  (Epic 05)
=========================================
Compute per-parcel transit accessibility, walkability proxy, and composite
TOD Suitability Score.  Supports both the *current* and *proposed* transit
networks so that scenario comparison is straightforward.

Key outputs
-----------
- ``nearest_station``      – name of nearest L / Metra station
- ``station_distance_m``   – metres from parcel centroid to that station
- ``transit_tier``         – categorical tier (< 400 m … > 1.6 km)
- ``walk_score_proxy``     – 0-100 walkability proxy from OSM
- ``tod_score``            – composite TOD Suitability Score 0-100
- ``transit_scores.csv``   – full export

Usage::

    python -m src.transportation          # run scoring pipeline
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

from src.config import (
    CTA_STATIONS_GEOJSON,
    METRA_STATIONS_GEOJSON,
    PARCELS_ENRICHED_GEOJSON,
    PROPOSED_TRANSIT_EXTENSIONS,
    TRANSIT_SCORES_CSV,
    TRANSIT_SHED_MAP,
    TRANSIT_TIERS,
    ensure_dirs,
)

# Illinois State Plane East — CRS in feet; we convert to metres as needed.
_IL_CRS = "EPSG:3435"
_FEET_PER_METRE = 3.28084


# ---------------------------------------------------------------------------
# 1. Load / create station data
# ---------------------------------------------------------------------------

def load_cta_stations(path: Path | None = None) -> gpd.GeoDataFrame | None:
    """Load CTA L station GeoJSON.  Returns ``None`` if the file is missing."""
    path = path or CTA_STATIONS_GEOJSON
    if not path.exists():
        print(f"WARNING: CTA stations file not found – {path}")
        return None
    gdf = gpd.read_file(path)
    if "station_name" not in gdf.columns:
        # try common alternatives
        for alt in ["STATION_NAME", "name", "NAME", "stop_name"]:
            if alt in gdf.columns:
                gdf = gdf.rename(columns={alt: "station_name"})
                break
        else:
            gdf["station_name"] = [f"CTA_{i}" for i in range(len(gdf))]
    gdf["station_type"] = "CTA_L"
    return gdf


def load_metra_stations(path: Path | None = None) -> gpd.GeoDataFrame | None:
    """Load Metra commuter rail station GeoJSON."""
    path = path or METRA_STATIONS_GEOJSON
    if not path.exists():
        print(f"WARNING: Metra stations file not found – {path}")
        return None
    gdf = gpd.read_file(path)
    for col in ["station_name", "STATION_NAME", "name", "NAME", "stop_name"]:
        if col in gdf.columns and col != "station_name":
            gdf = gdf.rename(columns={col: "station_name"})
            break
    if "station_name" not in gdf.columns:
        gdf["station_name"] = [f"Metra_{i}" for i in range(len(gdf))]
    gdf["station_type"] = "Metra"
    return gdf


def build_proposed_stations() -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame from the hypothetical station list in config.

    These represent the Ashland BRT, Circle Line, and Red Line Extension
    proposals referenced in the Plan for Chicago outline.
    """
    rows = []
    for name, lat, lon in PROPOSED_TRANSIT_EXTENSIONS:
        rows.append({"station_name": name, "station_type": "Proposed",
                      "geometry": Point(lon, lat)})
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def combine_stations(
    include_metra: bool = True,
    include_proposed: bool = False,
) -> gpd.GeoDataFrame:
    """
    Merge CTA L + (optionally) Metra + (optionally) proposed stations
    into a single GeoDataFrame with ``station_name`` and ``station_type``.
    """
    parts: list[gpd.GeoDataFrame] = []

    cta = load_cta_stations()
    if cta is not None:
        parts.append(cta[["station_name", "station_type", "geometry"]].reset_index(drop=True))

    if include_metra:
        metra = load_metra_stations()
        if metra is not None:
            parts.append(metra[["station_name", "station_type", "geometry"]].reset_index(drop=True))

    if include_proposed:
        parts.append(build_proposed_stations().reset_index(drop=True))

    if not parts:
        print("ERROR: No station data available.")
        return gpd.GeoDataFrame(
            columns=["station_name", "station_type", "geometry"],
            crs="EPSG:4326",
        )

    combined = pd.concat(parts, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")
    print(f"Combined stations: {len(combined)} "
          f"(CTA_L={sum(combined.station_type=='CTA_L')}, "
          f"Metra={sum(combined.station_type=='Metra')}, "
          f"Proposed={sum(combined.station_type=='Proposed')})")
    return combined


# ---------------------------------------------------------------------------
# 2. Distance computation & tier assignment
# ---------------------------------------------------------------------------

def compute_station_distances(
    parcels: gpd.GeoDataFrame,
    stations: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    For every parcel, find the nearest station and compute the distance
    in *metres*.

    Adds columns:
    - ``nearest_station`` – station name
    - ``station_distance_m`` – distance in metres
    - ``nearest_station_type`` – CTA_L / Metra / Proposed

    Uses Illinois State Plane (EPSG:3435, feet) for the spatial index
    then converts feet → metres for the final distance.
    """
    result = parcels.copy()

    if stations is None or stations.empty:
        result["nearest_station"] = None
        result["station_distance_m"] = np.nan
        result["nearest_station_type"] = None
        return result

    # Project to IL State Plane
    parcels_proj = result.to_crs(_IL_CRS)
    stations_proj = stations.to_crs(_IL_CRS)

    # Use parcel centroids
    centroids = parcels_proj.geometry.centroid

    # Build arrays for vectorised nearest-neighbour lookup
    stn_points = np.column_stack([
        stations_proj.geometry.x.values,
        stations_proj.geometry.y.values,
    ])

    nearest_idx = np.empty(len(centroids), dtype=int)
    nearest_dist_ft = np.empty(len(centroids), dtype=float)

    cx = centroids.x.values
    cy = centroids.y.values

    # Vectorised brute-force – fine for ~300 stations vs parcels
    for i in range(len(cx)):
        dists = np.sqrt((stn_points[:, 0] - cx[i]) ** 2 +
                        (stn_points[:, 1] - cy[i]) ** 2)
        idx = int(np.argmin(dists))
        nearest_idx[i] = idx
        nearest_dist_ft[i] = dists[idx]

    result["nearest_station"] = stations.iloc[nearest_idx]["station_name"].values
    result["nearest_station_type"] = stations.iloc[nearest_idx]["station_type"].values
    result["station_distance_m"] = nearest_dist_ft / _FEET_PER_METRE

    print(f"Distance stats (m): "
          f"min={result['station_distance_m'].min():.0f}, "
          f"median={result['station_distance_m'].median():.0f}, "
          f"max={result['station_distance_m'].max():.0f}")

    return result


def assign_transit_tiers(
    parcels: gpd.GeoDataFrame,
    tiers: list[tuple] | None = None,
) -> gpd.GeoDataFrame:
    """
    Assign a categorical transit tier based on ``station_distance_m``.

    Tiers default to ``config.TRANSIT_TIERS``::

        Tier 1: <400 m
        Tier 2: 400-800 m
        Tier 3: 800 m - 1.6 km
        Tier 4: >1.6 km
    """
    tiers = tiers or TRANSIT_TIERS
    result = parcels.copy()

    if "station_distance_m" not in result.columns:
        result["transit_tier"] = "Unknown"
        return result

    conditions = []
    labels = []
    for lo, hi, label in tiers:
        conditions.append(
            (result["station_distance_m"] >= lo) &
            (result["station_distance_m"] < hi)
        )
        labels.append(label)

    result["transit_tier"] = np.select(conditions, labels, default="Unknown")

    # Pretty-print distribution
    for label in labels:
        n = (result["transit_tier"] == label).sum()
        pct = n / len(result) * 100
        print(f"  {label}: {n:,} parcels ({pct:.1f}%)")

    return result


# ---------------------------------------------------------------------------
# 3. Walk Score proxy via OSM network analysis
# ---------------------------------------------------------------------------

def compute_walk_score_proxy(
    parcels: gpd.GeoDataFrame,
    bbox: dict | None = None,
    *,
    amenity_radius_m: float = 800,
    intersection_radius_m: float = 400,
    max_amenity_count: int = 50,
    max_intersection_density: float = 200,
) -> gpd.GeoDataFrame:
    """
    Compute a 0-100 walkability proxy for each parcel using OSM data.

    Components (equally weighted by default):
    1. **Amenity richness** – count of POI nodes (amenity, shop tags) within
       *amenity_radius_m* of the parcel centroid, capped at *max_amenity_count*.
    2. **Intersection density** – node degree >= 3 within *intersection_radius_m*,
       capped at *max_intersection_density*.

    Falls back to 50 (neutral) if osmnx is unavailable.
    """
    result = parcels.copy()

    try:
        import osmnx as ox  # type: ignore[import-untyped]
    except ImportError:
        print("WARNING: osmnx not installed – assigning neutral walk_score_proxy = 50")
        result["walk_score_proxy"] = 50.0
        return result

    # Determine bounding box
    if bbox is None:
        bounds = result.total_bounds  # [minx, miny, maxx, maxy]
        # Pad bounding box by ~1 km so edge parcels have full context
        pad = 0.01  # ~1 km at Chicago latitude
        bbox_tuple = (bounds[3] + pad, bounds[1] - pad,
                      bounds[2] + pad, bounds[0] - pad)  # N, S, E, W
    else:
        pad = 0.01
        bbox_tuple = (
            bbox["max_lat"] + pad, bbox["min_lat"] - pad,
            bbox["max_lon"] + pad, bbox["min_lon"] - pad,
        )

    # --- 3a. Amenity count ------------------------------------------------
    try:
        print("Downloading OSM amenity nodes …")
        amenities = ox.features_from_bbox(
            bbox=bbox_tuple,
            tags={"amenity": True, "shop": True},
        )
        amenity_points = amenities.copy()
        amenity_points["geometry"] = amenity_points.geometry.centroid
        amenity_proj = amenity_points.to_crs(_IL_CRS)
    except Exception as e:
        print(f"WARNING: Could not fetch OSM amenities: {e}")
        amenity_proj = None

    # --- 3b. Intersection density -----------------------------------------
    try:
        print("Downloading OSM walk network …")
        G = ox.graph_from_bbox(bbox=bbox_tuple, network_type="walk")
        nodes_gdf = ox.graph_to_gdfs(G, edges=False)
        # degree >= 3 -> "real" intersection (not dead-ends / bends)
        node_degree = dict(G.degree())
        intersection_nodes = nodes_gdf[
            nodes_gdf.index.map(lambda n: node_degree.get(n, 0) >= 3)
        ]
        intersection_proj = intersection_nodes.to_crs(_IL_CRS)
    except Exception as e:
        print(f"WARNING: Could not fetch OSM walk network: {e}")
        intersection_proj = None

    # --- 3c. Score each parcel --------------------------------------------
    parcels_proj = result.to_crs(_IL_CRS)
    centroids = parcels_proj.geometry.centroid

    amenity_radius_ft = amenity_radius_m * _FEET_PER_METRE
    intersection_radius_ft = intersection_radius_m * _FEET_PER_METRE

    amenity_scores = np.full(len(centroids), 0.5)  # default neutral
    intersection_scores = np.full(len(centroids), 0.5)

    if amenity_proj is not None and not amenity_proj.empty:
        from shapely.strtree import STRtree
        amenity_tree = STRtree(amenity_proj.geometry.values)
        print("Computing amenity counts per parcel …")
        for i, centroid in enumerate(centroids):
            nearby = amenity_tree.query(centroid.buffer(amenity_radius_ft))
            count = len(nearby)
            amenity_scores[i] = min(count / max_amenity_count, 1.0)

    if intersection_proj is not None and not intersection_proj.empty:
        from shapely.strtree import STRtree
        int_tree = STRtree(intersection_proj.geometry.values)
        print("Computing intersection density per parcel …")
        for i, centroid in enumerate(centroids):
            nearby = int_tree.query(centroid.buffer(intersection_radius_ft))
            count = len(nearby)
            intersection_scores[i] = min(count / max_intersection_density, 1.0)

    # Composite walk score: average of two components, scaled 0-100
    result["walk_score_proxy"] = np.round(
        (amenity_scores * 0.5 + intersection_scores * 0.5) * 100, 1
    )

    print(f"Walk score proxy stats: "
          f"min={result['walk_score_proxy'].min():.0f}, "
          f"median={result['walk_score_proxy'].median():.0f}, "
          f"max={result['walk_score_proxy'].max():.0f}")

    return result


# ---------------------------------------------------------------------------
# 4. Composite TOD Suitability Score
# ---------------------------------------------------------------------------

def compute_tod_score(
    parcels: gpd.GeoDataFrame,
    *,
    weight_transit: float = 0.50,
    weight_walk: float = 0.30,
    weight_zoning_gap: float = 0.20,
    max_transit_distance_m: float = 3000,
) -> gpd.GeoDataFrame:
    """
    Composite TOD Suitability Score (0-100).

    Components:
    - **Transit proximity** (default 50 %): inverse of distance capped at
      ``max_transit_distance_m``.
    - **Walkability** (default 30 %): ``walk_score_proxy`` / 100.
    - **Zoning gap** (default 20 %): whether the parcel is currently
      low-density residential (indicating upzoning opportunity).

    The three sub-scores are each normalised 0-1, then combined
    with configured weights and scaled to 0-100.
    """
    result = parcels.copy()

    # --- Transit sub-score ---
    dist = result.get("station_distance_m", pd.Series(np.nan, index=result.index))
    transit_sub = 1 - (dist.clip(upper=max_transit_distance_m) / max_transit_distance_m)
    transit_sub = transit_sub.fillna(0)

    # --- Walkability sub-score ---
    walk_sub = result.get("walk_score_proxy",
                          pd.Series(50, index=result.index)) / 100.0

    # --- Zoning gap sub-score ---
    LOW_DENSITY_ZONES = {"RS-1", "RS-2", "RS-3"}
    zone_col = None
    for col in ("zone_class", "ZONE_CLASS", "zoning_class"):
        if col in result.columns:
            zone_col = col
            break
    if zone_col:
        zoning_gap_sub = result[zone_col].isin(LOW_DENSITY_ZONES).astype(float)
    else:
        zoning_gap_sub = pd.Series(0.0, index=result.index)

    # --- Composite ---
    raw = (weight_transit * transit_sub +
           weight_walk * walk_sub +
           weight_zoning_gap * zoning_gap_sub)

    result["tod_score"] = np.round(raw * 100, 1)

    print(f"TOD score stats: "
          f"min={result['tod_score'].min():.0f}, "
          f"median={result['tod_score'].median():.0f}, "
          f"max={result['tod_score'].max():.0f}")

    return result


# ---------------------------------------------------------------------------
# 5. Scenario scoring (current vs proposed network)
# ---------------------------------------------------------------------------

def score_parcels(
    parcels: gpd.GeoDataFrame,
    include_metra: bool = True,
    include_proposed: bool = False,
    compute_walkability: bool = True,
) -> gpd.GeoDataFrame:
    """
    Full scoring pipeline: distance -> tiers -> walk proxy -> TOD composite.

    Parameters
    ----------
    parcels : GeoDataFrame
        Must have ``geometry``; optionally ``zone_class`` for zoning gap.
    include_metra : bool
        Include Metra commuter rail stations.
    include_proposed : bool
        Include hypothetical proposed stations from config.
    compute_walkability : bool
        Run the OSM-based walk score proxy (slow for large areas).

    Returns
    -------
    GeoDataFrame with new columns added in-place:
        nearest_station, station_distance_m, nearest_station_type,
        transit_tier, walk_score_proxy, tod_score.
    """
    stations = combine_stations(
        include_metra=include_metra,
        include_proposed=include_proposed,
    )

    result = compute_station_distances(parcels, stations)
    result = assign_transit_tiers(result)

    if compute_walkability:
        result = compute_walk_score_proxy(result)
    else:
        result["walk_score_proxy"] = 50.0  # neutral default

    result = compute_tod_score(result)
    return result


def score_current_and_proposed(
    parcels: gpd.GeoDataFrame,
    compute_walkability: bool = True,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """
    Score parcels under *current* (CTA + Metra) and *proposed*
    (CTA + Metra + hypothetical) networks.

    Returns (current_scored, proposed_scored).
    """
    print("\n=== Scoring under CURRENT transit network ===")
    current = score_parcels(
        parcels, include_proposed=False,
        compute_walkability=compute_walkability,
    )

    print("\n=== Scoring under PROPOSED transit network ===")
    proposed = score_parcels(
        parcels, include_proposed=True,
        compute_walkability=compute_walkability,
    )

    return current, proposed


# ---------------------------------------------------------------------------
# 6. Export
# ---------------------------------------------------------------------------

def export_transit_scores(
    parcels: gpd.GeoDataFrame,
    output_path: Path | None = None,
) -> Path:
    """Export transit scores to CSV, keeping essential columns."""
    output_path = output_path or TRANSIT_SCORES_CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Columns we want in the export
    desired = [
        "pin", "PIN", "pin14", "PIN14",
        "nearest_station", "nearest_station_type",
        "station_distance_m", "transit_tier",
        "walk_score_proxy", "tod_score",
        "zone_class", "ZONE_CLASS",
        "near_transit",
    ]
    keep = [c for c in desired if c in parcels.columns]
    parcels[keep].to_csv(output_path, index=False)
    print(f"Exported transit scores ({len(parcels):,} rows) -> {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 7. Transit shed visualisation (Folium)
# ---------------------------------------------------------------------------

def visualise_transit_shed(
    stations: gpd.GeoDataFrame | None = None,
    output_path: Path | None = None,
    rings_m: tuple[float, ...] = (400, 800),
) -> Path:
    """
    Generate a Folium HTML map showing concentric buffer rings around
    each L / Metra station.

    Parameters
    ----------
    stations : GeoDataFrame, optional
        Defaults to CTA + Metra combined.
    output_path : Path, optional
        Defaults to ``TRANSIT_SHED_MAP``.
    rings_m : tuple of float
        Buffer radii in metres (default 400 m and 800 m).
    """
    import folium  # type: ignore[import-untyped]

    output_path = output_path or TRANSIT_SHED_MAP
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if stations is None:
        stations = combine_stations(include_proposed=True)

    # Chicago centre
    m = folium.Map(location=[41.8781, -87.6298], zoom_start=11,
                   tiles="CartoDB positron")

    # Project for buffering then reproject back to 4326 for Folium
    stations_proj = stations.to_crs(_IL_CRS)

    ring_colours = ["#ff000060", "#ffa50040", "#ffff0030"]  # inner -> outer

    for idx, radius_m in enumerate(sorted(rings_m)):
        colour = ring_colours[idx % len(ring_colours)]
        radius_ft = radius_m * _FEET_PER_METRE
        buffers = stations_proj.geometry.buffer(radius_ft)
        buf_gdf = gpd.GeoDataFrame(geometry=buffers, crs=_IL_CRS).to_crs("EPSG:4326")

        folium.GeoJson(
            buf_gdf.__geo_interface__,
            name=f"{radius_m} m ring",
            style_function=lambda _feat, c=colour: {
                "fillColor": c[:7],
                "color": c[:7],
                "weight": 0.5,
                "fillOpacity": 0.25,
            },
        ).add_to(m)

    # Station markers
    type_colours = {"CTA_L": "blue", "Metra": "green", "Proposed": "red"}
    for _, row in stations.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4,
            color=type_colours.get(row["station_type"], "gray"),
            fill=True, fill_opacity=0.8,
            popup=f"{row['station_name']} ({row['station_type']})",
        ).add_to(m)

    folium.LayerControl().add_to(m)
    m.save(str(output_path))
    print(f"Transit shed map saved -> {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# 8. Main pipeline
# ---------------------------------------------------------------------------

def run_transit_scoring(
    parcels_path: Path | None = None,
    compute_walkability: bool = True,
) -> gpd.GeoDataFrame | None:
    """
    End-to-end pipeline: load enriched parcels, score under current +
    proposed networks, export CSV, generate map.
    """
    ensure_dirs()

    parcels_path = parcels_path or PARCELS_ENRICHED_GEOJSON
    if not parcels_path.exists():
        print(f"ERROR: Enriched parcels not found – {parcels_path}")
        print("Run zoning analysis first (src.zoning) to generate enriched parcels.")
        return None

    parcels = gpd.read_file(parcels_path)
    print(f"Loaded {len(parcels):,} parcels from {parcels_path}")

    # Score under current network
    print("\n" + "=" * 50)
    print("CURRENT TRANSIT NETWORK SCORING")
    print("=" * 50)
    scored = score_parcels(
        parcels, include_proposed=False,
        compute_walkability=compute_walkability,
    )

    # Also update near_transit boolean for back-compat with property_value.py
    scored["near_transit"] = scored["station_distance_m"] <= 800
    scored["transit_dist_m"] = scored["station_distance_m"]

    # Export CSV
    export_transit_scores(scored)

    # Generate transit shed map (includes proposed stations for visual context)
    print("\nGenerating transit shed map …")
    visualise_transit_shed()

    # Quick proposed-network comparison summary
    print("\n" + "=" * 50)
    print("PROPOSED TRANSIT NETWORK COMPARISON")
    print("=" * 50)
    proposed_stations = combine_stations(include_proposed=True)
    proposed_scored = compute_station_distances(scored, proposed_stations)
    proposed_scored = assign_transit_tiers(proposed_scored)

    # Show net tier improvement
    tier_improve = (
        (proposed_scored["station_distance_m"] < scored["station_distance_m"])
        .sum()
    )
    print(f"Parcels with improved transit access under proposed network: "
          f"{tier_improve:,}")

    return scored


if __name__ == "__main__":
    print("Transit & Walkability Scoring Module")
    print("=" * 50)
    run_transit_scoring(compute_walkability=False)
    print("  load_gtfs_data()         - Parse CTA GTFS feed")
    print("  prepare_network_for_simulation() - Modify network for scenarios")
    print("  run_traffic_simulation() - Run SUMO/A-B Street simulation")
    print("\nNote: Simulation functions are placeholders.")

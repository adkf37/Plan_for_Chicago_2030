"""
Prepare Map Data for MapLibre GL JS  (Epic 06)
===============================================
Reads enriched parcels, transit scores, value projections, zoning, and
CTA/Metra station data, then exports **lightweight** GeoJSON files into
``site/data/`` ready for the web map.

Optimisations applied:
- Geometry simplified to ~2 m tolerance (imperceptible at city zoom)
- Only columns needed for tooltips / styling are kept
- Coordinate precision truncated to 6 decimal places (~0.1 m)
- Proposed-zoning layer generated from upzoning rules

Usage::

    python -m src.prepare_map_data
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import mapping, shape

from src.config import (
    CTA_STATIONS_GEOJSON,
    CHICAGO_ZONING_GEOJSON,
    METRA_STATIONS_GEOJSON,
    PARCELS_ENRICHED_GEOJSON,
    SITE_DATA_DIR,
    TRANSIT_SCORES_CSV,
    VALUE_PROJECTIONS_CSV,
    ZONING_GEOJSON,
    ZONE_TYPE_COLORS,
    ZONE_TYPE_NAMES,
    ensure_dirs,
)

# Simplification tolerance in *degrees* (~2 m at Chicago latitude)
_SIMPLIFY_TOLERANCE = 0.00002

# Coordinate precision (6 dp ≈ 0.1 m)
_COORD_PRECISION = 6

# Maximum features per layer (safety valve for browser perf)
_MAX_FEATURES = 200_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simplify_gdf(gdf: gpd.GeoDataFrame, tolerance: float = _SIMPLIFY_TOLERANCE) -> gpd.GeoDataFrame:
    """Simplify geometries while preserving topology."""
    result = gdf.copy()
    result["geometry"] = result.geometry.simplify(tolerance, preserve_topology=True)
    return result


def _truncate_coords(geojson_dict: dict, precision: int = _COORD_PRECISION) -> dict:
    """Recursively truncate coordinate precision in a GeoJSON dict."""

    def _round(coords):
        if isinstance(coords, (list, tuple)):
            if coords and isinstance(coords[0], (int, float)):
                return [round(c, precision) for c in coords]
            return [_round(c) for c in coords]
        return coords

    if "features" in geojson_dict:
        for feat in geojson_dict["features"]:
            if "geometry" in feat and feat["geometry"] is not None:
                feat["geometry"]["coordinates"] = _round(feat["geometry"]["coordinates"])
    return geojson_dict


def _save_geojson(gdf: gpd.GeoDataFrame, path: Path, *, max_features: int = _MAX_FEATURES) -> Path:
    """Save a GeoDataFrame as a compact GeoJSON file with truncated coords."""
    if len(gdf) > max_features:
        print(f"  Sampling {max_features:,} of {len(gdf):,} features for {path.name}")
        gdf = gdf.sample(n=max_features, random_state=42)

    gj = json.loads(gdf.to_json())
    gj = _truncate_coords(gj)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(gj, f, separators=(",", ":"))  # compact

    size_kb = path.stat().st_size / 1024
    print(f"  Saved {path.name} — {len(gdf):,} features, {size_kb:.0f} KB")
    return path


# ---------------------------------------------------------------------------
# Layer exporters
# ---------------------------------------------------------------------------

def export_zoning_layer(output_dir: Path | None = None) -> Path | None:
    """Export current zoning polygons with colour / name info."""
    output_dir = output_dir or SITE_DATA_DIR
    src = ZONING_GEOJSON
    if not src.exists():
        src = CHICAGO_ZONING_GEOJSON
    if not src.exists():
        print("  SKIP zoning — source file not found")
        return None

    gdf = gpd.read_file(src).to_crs("EPSG:4326")
    gdf = _simplify_gdf(gdf)

    # Keep only useful columns
    keep = ["geometry"]
    for col in ("ZONE_CLASS", "zone_class", "ZONE_TYPE", "zone_type"):
        if col in gdf.columns:
            keep.append(col)

    # Map zone type integer to readable name + colour
    zt_col = "ZONE_TYPE" if "ZONE_TYPE" in gdf.columns else "zone_type" if "zone_type" in gdf.columns else None
    if zt_col:
        gdf["zone_name"] = gdf[zt_col].map(ZONE_TYPE_NAMES).fillna("Other")
        gdf["zone_color"] = gdf[zt_col].map(ZONE_TYPE_COLORS).fillna("#808080")
        keep += ["zone_name", "zone_color"]

    gdf = gdf[[c for c in keep if c in gdf.columns]]
    return _save_geojson(gdf, output_dir / "zoning.geojson")


def export_proposed_zoning_layer(output_dir: Path | None = None) -> Path | None:
    """
    Export a *proposed* zoning layer that applies upzoning rules to
    low-density residential parcels near transit.
    """
    output_dir = output_dir or SITE_DATA_DIR
    enriched_path = PARCELS_ENRICHED_GEOJSON
    if not enriched_path.exists():
        print("  SKIP proposed zoning — enriched parcels not found")
        return None

    gdf = gpd.read_file(enriched_path).to_crs("EPSG:4326")

    zone_col = None
    for col in ("zone_class", "ZONE_CLASS"):
        if col in gdf.columns:
            zone_col = col
            break
    if zone_col is None:
        print("  SKIP proposed zoning — no zone_class column")
        return None

    gdf["proposed_zone"] = gdf[zone_col]

    # Upzoning rules: RS-2/RS-3 near transit → RT-4;  RS-1 near transit → RS-3
    near = gdf.get("near_transit", pd.Series(False, index=gdf.index))
    gdf.loc[near & gdf[zone_col].isin(["RS-2", "RS-3"]), "proposed_zone"] = "RT-4"
    gdf.loc[near & (gdf[zone_col] == "RS-1"), "proposed_zone"] = "RS-3"
    gdf["changed"] = gdf["proposed_zone"] != gdf[zone_col]

    gdf = _simplify_gdf(gdf)
    keep_cols = ["geometry", zone_col, "proposed_zone", "changed"]
    gdf = gdf[[c for c in keep_cols if c in gdf.columns]]
    return _save_geojson(gdf, output_dir / "proposed_zoning.geojson")


def export_transit_layer(output_dir: Path | None = None) -> Path | None:
    """Export CTA + Metra station points."""
    output_dir = output_dir or SITE_DATA_DIR
    parts = []

    for path, stype in [(CTA_STATIONS_GEOJSON, "CTA_L"), (METRA_STATIONS_GEOJSON, "Metra")]:
        if path.exists():
            g = gpd.read_file(path).to_crs("EPSG:4326")
            # Normalise name column
            for col in ("station_name", "STATION_NAME", "name", "NAME", "stop_name"):
                if col in g.columns and col != "station_name":
                    g = g.rename(columns={col: "station_name"})
                    break
            if "station_name" not in g.columns:
                g["station_name"] = [f"{stype}_{i}" for i in range(len(g))]
            g["station_type"] = stype
            parts.append(g[["geometry", "station_name", "station_type"]])

    # Add proposed stations from config
    from src.config import PROPOSED_TRANSIT_EXTENSIONS
    from shapely.geometry import Point
    rows = [{"station_name": n, "station_type": "Proposed",
             "geometry": Point(lon, lat)} for n, lat, lon in PROPOSED_TRANSIT_EXTENSIONS]
    parts.append(gpd.GeoDataFrame(rows, crs="EPSG:4326"))

    if not parts:
        print("  SKIP transit — no station files found")
        return None

    combined = pd.concat(parts, ignore_index=True)
    combined = gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")
    return _save_geojson(combined, output_dir / "transit_stations.geojson")


def export_value_layer(output_dir: Path | None = None) -> Path | None:
    """Export parcels with value projection data for the heatmap overlay."""
    output_dir = output_dir or SITE_DATA_DIR
    enriched_path = PARCELS_ENRICHED_GEOJSON
    if not enriched_path.exists():
        print("  SKIP values — enriched parcels not found")
        return None

    gdf = gpd.read_file(enriched_path).to_crs("EPSG:4326")

    # Try to merge value projections
    if VALUE_PROJECTIONS_CSV.exists():
        vp = pd.read_csv(VALUE_PROJECTIONS_CSV)
        # Find join key
        for key in ("pin", "PIN", "pin14", "PIN14"):
            if key in gdf.columns and key in vp.columns:
                gdf = gdf.merge(
                    vp[[key, "current_value", "moderate_projected", "moderate_uplift_pct"]].drop_duplicates(key),
                    on=key, how="left",
                )
                break

    # Try to merge transit scores
    if TRANSIT_SCORES_CSV.exists():
        ts = pd.read_csv(TRANSIT_SCORES_CSV)
        for key in ("pin", "PIN", "pin14", "PIN14"):
            if key in gdf.columns and key in ts.columns:
                merge_cols = [key]
                for c in ("tod_score", "transit_tier", "station_distance_m"):
                    if c in ts.columns:
                        merge_cols.append(c)
                gdf = gdf.merge(ts[merge_cols].drop_duplicates(key), on=key, how="left")
                break

    gdf = _simplify_gdf(gdf)

    keep = ["geometry"]
    desired = [
        "pin", "PIN", "pin14", "PIN14",
        "zone_class", "ZONE_CLASS",
        "current_value", "moderate_projected", "moderate_uplift_pct",
        "tod_score", "transit_tier", "station_distance_m",
        "near_transit", "upzoning_candidate",
    ]
    keep += [c for c in desired if c in gdf.columns]

    gdf = gdf[keep]
    return _save_geojson(gdf, output_dir / "parcels.geojson")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def prepare_all(output_dir: Path | None = None) -> dict[str, Path | None]:
    """Export all map layers and return paths dict."""
    ensure_dirs()
    output_dir = output_dir or SITE_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Preparing map data layers …")

    results = {}
    print("\n[1/4] Zoning layer")
    results["zoning"] = export_zoning_layer(output_dir)

    print("\n[2/4] Proposed zoning layer")
    results["proposed_zoning"] = export_proposed_zoning_layer(output_dir)

    print("\n[3/4] Transit stations layer")
    results["transit"] = export_transit_layer(output_dir)

    print("\n[4/4] Parcel values layer")
    results["parcels"] = export_value_layer(output_dir)

    # Write a small manifest so the JS app knows which layers are available
    manifest = {k: v.name if v else None for k, v in results.items()}
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest → {manifest_path}")

    return results


if __name__ == "__main__":
    prepare_all()

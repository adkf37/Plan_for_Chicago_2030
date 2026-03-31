"""
Prepare Map Data for Deck.gl + PMTiles  (Epic 06)
==================================================
Reads enriched parcels, transit scores, value projections, zoning, and
CTA/Metra station data, then exports **lightweight** GeoJSON files into
``site/data/`` ready for the web map.

For polygon-heavy layers (zoning, proposed zoning, parcels) we also
generate **PMTiles** archives so the Deck.gl ``MVTLayer`` can stream
vector tiles on demand instead of loading the full GeoJSON into memory.

Optimisations applied:
- Geometry simplified to ~2 m tolerance (imperceptible at city zoom)
- Only columns needed for tooltips / styling are kept
- Coordinate precision truncated to 6 decimal places (~0.1 m)
- Proposed-zoning layer generated from upzoning rules
- PMTiles generated via tippecanoe (if available) or Python pmtiles fallback

Usage::

    python -m src.prepare_map_data
"""

from __future__ import annotations

import json
import shutil
import subprocess
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
_MAX_FEATURES = 600_000  # covers the full ~550 K parcel universe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _recover_geometry(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    If all geometries are null but lat/lon columns exist, build Point
    geometries from them.  This handles datasets (like the Cook County
    Assessor parcel universe) where coordinates are stored as attributes
    rather than as GeoJSON geometry.

    Returns the GeoDataFrame with geometry populated (or unchanged if
    geometry was already valid).
    """
    null_ct = gdf.geometry.isna().sum()
    if null_ct == 0:
        return gdf

    # Look for lat/lon columns
    lat_col = lon_col = None
    for c in gdf.columns:
        cl = c.lower()
        if cl in ("lat", "latitude", "y"):
            lat_col = c
        elif cl in ("lon", "lng", "longitude", "x"):
            lon_col = c

    if lat_col is None or lon_col is None:
        return gdf

    # Convert to numeric, coercing errors (handles string-typed coords)
    lats = pd.to_numeric(gdf[lat_col], errors="coerce")
    lons = pd.to_numeric(gdf[lon_col], errors="coerce")
    valid_mask = lats.notna() & lons.notna()
    recoverable = valid_mask.sum()

    if recoverable == 0:
        return gdf

    from shapely.geometry import Point

    print(f"  Recovering {recoverable:,} geometries from {lat_col}/{lon_col} columns")
    result = gdf.copy()
    # Build points only where lat/lon are valid
    result.loc[valid_mask, "geometry"] = [
        Point(lon, lat) for lon, lat in zip(lons[valid_mask], lats[valid_mask])
    ]
    result = gpd.GeoDataFrame(result, geometry="geometry", crs="EPSG:4326")
    return result


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
    # Drop null / empty geometries — tippecanoe and deck.gl both reject them
    before = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    dropped = before - len(gdf)
    if dropped:
        print(f"  Dropped {dropped:,} null/empty geometries from {path.name}")

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
    Export a *proposed* zoning layer that applies upzoning rules.

    Uses the actual zoning polygons (which have real geometry) as the
    spatial base, then joins enrichment attributes (near_transit, etc.)
    from the enriched parcels file to determine which zones to upzone.
    """
    output_dir = output_dir or SITE_DATA_DIR

    # --- Load zoning polygons (real geometry) ---
    zoning_src = ZONING_GEOJSON
    if not zoning_src.exists():
        zoning_src = CHICAGO_ZONING_GEOJSON
    if not zoning_src.exists():
        print("  SKIP proposed zoning — zoning source not found")
        return None

    gdf = gpd.read_file(zoning_src).to_crs("EPSG:4326")
    print(f"  Loaded {len(gdf):,} zoning polygons for proposed zoning")

    # Normalise zone_class column name
    zone_col = None
    for col in ("zone_class", "ZONE_CLASS"):
        if col in gdf.columns:
            zone_col = col
            break
    if zone_col is None:
        print("  SKIP proposed zoning — no zone_class column")
        return None

    # --- Determine which zones are near transit ---
    # Use 800m buffer around CTA + Metra stations to flag zoning polygons
    # that intersect the transit catchment area.  We build the buffer in a
    # projected CRS (EPSG:3435 — IL StatePlane, metres) then convert the
    # single union polygon back to WGS 84 so we never need to project the
    # 14 k+ zoning MultiPolygons (which is >60 s on most machines).
    transit_parts = []
    for path in (CTA_STATIONS_GEOJSON, METRA_STATIONS_GEOJSON):
        if path.exists():
            transit_parts.append(gpd.read_file(path).to_crs("EPSG:3435"))
    if transit_parts:
        stations = pd.concat(transit_parts, ignore_index=True)
        stations = gpd.GeoDataFrame(stations, geometry="geometry", crs="EPSG:3435")
        # Build union buffer in projected CRS, then reproject to WGS 84
        transit_buffer_3435 = stations.geometry.buffer(800).union_all()
        transit_buffer_wgs = (
            gpd.GeoSeries([transit_buffer_3435], crs="EPSG:3435")
            .to_crs("EPSG:4326")
            .iloc[0]
        )
        gdf["near_transit"] = gdf.geometry.intersects(transit_buffer_wgs)
        print(f"  {gdf['near_transit'].sum():,} zoning polygons within 800 m of transit")
    else:
        gdf["near_transit"] = False
        print("  No transit station files found — skipping near-transit flagging")

    # Apply upzoning rules
    gdf["proposed_zone"] = gdf[zone_col]
    near = gdf["near_transit"]
    gdf.loc[near & gdf[zone_col].isin(["RS-2", "RS-3"]), "proposed_zone"] = "RT-4"
    gdf.loc[near & (gdf[zone_col] == "RS-1"), "proposed_zone"] = "RS-3"
    gdf["changed"] = gdf["proposed_zone"] != gdf[zone_col]
    changed_ct = gdf["changed"].sum()
    print(f"  Upzoning applied: {changed_ct:,} zones changed out of {len(gdf):,}")

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
            # Normalise name column — only rename if station_name doesn't already exist,
            # otherwise we'd create duplicate columns and break pd.concat.
            if "station_name" not in g.columns:
                for col in ("STATION_NAME", "name", "NAME", "stop_name"):
                    if col in g.columns:
                        g = g.rename(columns={col: "station_name"})
                        break
            if "station_name" not in g.columns:
                g["station_name"] = [f"{stype}_{i}" for i in range(len(g))]
            g["station_type"] = stype
            # Create clean copy with only needed columns and reset index
            subset = g[["geometry", "station_name", "station_type"]].copy()
            subset.reset_index(drop=True, inplace=True)
            parts.append(subset)

    # Add proposed stations from config
    from src.config import PROPOSED_TRANSIT_EXTENSIONS
    from shapely.geometry import Point
    rows = [{"station_name": n, "station_type": "Proposed",
             "geometry": Point(lon, lat)} for n, lat, lon in PROPOSED_TRANSIT_EXTENSIONS]
    proposed = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    proposed.reset_index(drop=True, inplace=True)
    parts.append(proposed)

    if not parts:
        print("  SKIP transit — no station files found")
        return None

    # Concatenate all parts and ensure it's a proper GeoDataFrame
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

    gdf = gpd.read_file(enriched_path)

    # Recover geometry from lat/lon if all geometries are null
    # (Cook County Assessor data stores coords as attributes, not geometry)
    gdf = _recover_geometry(gdf)
    gdf = gdf.to_crs("EPSG:4326")

    # Try to merge transit scores (has tod_score, transit_tier, etc.)
    if TRANSIT_SCORES_CSV.exists():
        ts = pd.read_csv(TRANSIT_SCORES_CSV)
        for key in ("pin", "PIN", "pin14", "PIN14"):
            if key in gdf.columns and key in ts.columns:
                gdf[key] = gdf[key].astype(str)
                ts[key] = ts[key].astype(str)
                merge_cols = [key]
                for c in ("tod_score", "transit_tier", "station_distance_m"):
                    if c in ts.columns and c not in gdf.columns:
                        merge_cols.append(c)
                if len(merge_cols) > 1:
                    gdf = gdf.merge(ts[merge_cols].drop_duplicates(key), on=key, how="left")
                    print(f"  Merged transit scores — tod_score present: {'tod_score' in gdf.columns}")
                break

    # Try to merge value projections
    if VALUE_PROJECTIONS_CSV.exists():
        vp = pd.read_csv(VALUE_PROJECTIONS_CSV)
        for key in ("pin", "PIN", "pin14", "PIN14"):
            if key in gdf.columns and key in vp.columns:
                gdf[key] = gdf[key].astype(str)
                vp[key] = vp[key].astype(str)
                gdf = gdf.merge(
                    vp[[key, "current_value", "moderate_projected", "moderate_uplift_pct"]].drop_duplicates(key),
                    on=key, how="left",
                )
                print("  Merged value projections")
                break

    # Points don't need simplification — only simplify polygons
    is_point_layer = gdf.geometry.notna().any() and gdf[gdf.geometry.notna()].geometry.iloc[0].geom_type == "Point"
    if not is_point_layer:
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
    print(f"  Parcel geometry type: {gdf[gdf.geometry.notna()].geometry.iloc[0].geom_type if gdf.geometry.notna().any() else 'NONE'}")
    return _save_geojson(gdf, output_dir / "parcels.geojson")


# ---------------------------------------------------------------------------
# PMTiles generation
# ---------------------------------------------------------------------------

# Layers to convert to vector tiles (polygon-heavy layers only)
_PMTILES_LAYERS = {
    "zoning": {"min_zoom": 10, "max_zoom": 16},
    "proposed_zoning": {"min_zoom": 10, "max_zoom": 16},
    "parcels": {"min_zoom": 12, "max_zoom": 16},
}


def _has_tippecanoe() -> bool:
    """Check whether tippecanoe is available on the system PATH."""
    return shutil.which("tippecanoe") is not None


def build_pmtiles_tippecanoe(geojson_path: Path, output_path: Path,
                              *, min_zoom: int = 10, max_zoom: int = 16,
                              layer_name: str | None = None) -> Path | None:
    """Convert a GeoJSON file to PMTiles via tippecanoe (preferred)."""
    layer_name = layer_name or geojson_path.stem
    cmd = [
        "tippecanoe",
        "-o", str(output_path),
        f"-Z{min_zoom}", f"-z{max_zoom}",
        "--no-feature-limit",
        "--no-tile-size-limit",
        "--minimum-detail=7",
        "--simplification=4",
        f"--layer={layer_name}",
        "--force",                 # overwrite existing
        str(geojson_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            size_kb = output_path.stat().st_size / 1024
            print(f"  PMTiles → {output_path.name} ({size_kb:.0f} KB)")
            return output_path
        else:
            print(f"  tippecanoe failed: {result.stderr[:200]}")
            return None
    except FileNotFoundError:
        print("  tippecanoe not found — skipping PMTiles generation")
        return None
    except subprocess.TimeoutExpired:
        print("  tippecanoe timed out")
        return None


def build_pmtiles_python(geojson_path: Path, output_path: Path,
                          *, min_zoom: int = 10, max_zoom: int = 16,
                          layer_name: str | None = None) -> Path | None:
    """
    Fallback: generate a minimal PMTiles file using the Python pmtiles library.

    This creates a single-tile-per-zoom approximation by writing the full
    GeoJSON as an MVT tile at each zoom level. For production use, tippecanoe
    is strongly preferred — this fallback exists so the pipeline works on
    Windows without WSL/Docker.
    """
    try:
        from pmtiles.tile import Tile, zxy_to_tileid
        from pmtiles.writer import Writer as PMTilesWriter
        import io
    except ImportError:
        print("  pmtiles package not installed — pip install pmtiles")
        return None

    # For the Python fallback we just copy the GeoJSON; the frontend will
    # detect that vector tiles failed and fall back to loading GeoJSON directly.
    # A proper Python MVT encoder (like vt2geojson in reverse) is non-trivial.
    print(f"  PMTiles Python fallback: {output_path.name} (stub — use tippecanoe for production)")
    return None


def build_all_pmtiles(output_dir: Path, geojson_results: dict[str, Path | None]) -> dict[str, Path | None]:
    """Build PMTiles for all eligible layers. Returns {layer_id: pmtiles_path}."""
    has_tc = _has_tippecanoe()
    if not has_tc:
        print("\n  tippecanoe not found on PATH.")
        print("  Install via: WSL2 (apt install tippecanoe), Docker, or brew (macOS).")
        print("  Polygon layers will be served as GeoJSON (slower for large datasets).\n")

    pmtiles_results: dict[str, Path | None] = {}
    for layer_id, opts in _PMTILES_LAYERS.items():
        geojson_path = geojson_results.get(layer_id)
        if geojson_path is None or not geojson_path.exists():
            pmtiles_results[layer_id] = None
            continue

        pm_path = output_dir / f"{layer_id}.pmtiles"
        if has_tc:
            pmtiles_results[layer_id] = build_pmtiles_tippecanoe(
                geojson_path, pm_path,
                min_zoom=opts["min_zoom"], max_zoom=opts["max_zoom"],
                layer_name=layer_id,
            )
        else:
            pmtiles_results[layer_id] = build_pmtiles_python(
                geojson_path, pm_path,
                min_zoom=opts["min_zoom"], max_zoom=opts["max_zoom"],
                layer_name=layer_id,
            )
    return pmtiles_results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def prepare_all(output_dir: Path | None = None) -> dict[str, Path | None]:
    """Export all map layers, build PMTiles, and return paths dict."""
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

    # Build PMTiles for polygon-heavy layers
    print("\n[PMTiles] Building vector tiles …")
    pmtiles_results = build_all_pmtiles(output_dir, results)

    # Write manifest — includes both GeoJSON and PMTiles availability
    # sourceType: "vector" means PMTiles is available; "geojson" means raw only
    manifest: dict[str, dict | None] = {}
    for layer_id, geojson_path in results.items():
        if geojson_path is None:
            manifest[layer_id] = None
            continue

        pm_path = pmtiles_results.get(layer_id)
        if pm_path is not None and pm_path.exists():
            manifest[layer_id] = {
                "file": pm_path.name,
                "sourceType": "vector",
                "sourceLayer": layer_id,
                "geojsonFallback": geojson_path.name,
            }
        else:
            manifest[layer_id] = {
                "file": geojson_path.name,
                "sourceType": "geojson",
            }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest → {manifest_path}")

    return results


if __name__ == "__main__":
    prepare_all()

"""
Zoning Classification & Density Mapping
========================================
Classifies parcels by zoning district via spatial join, enriches with FAR/height/use
data, and produces city-wide zoning analytics for visualization and modeling.

Usage:
    python -m src.zoning
"""

import geopandas as gpd
import pandas as pd
import warnings
from pathlib import Path

from src.config import (
    HOUSING_DENSITY_CATEGORIES,
    ZONE_TYPE_NAMES,
    PARCEL_GEOJSON,
    ZONING_GEOJSON,
    CTA_STATIONS_GEOJSON,
    ZONING_CODES_CSV,
    PARCELS_ENRICHED_GEOJSON,
    ZONING_SUMMARY_CSV,
    PROCESSED_DIR,
    ensure_dirs,
)

# Suppress warnings from geopandas spatial operations
warnings.filterwarnings("ignore", category=UserWarning, module="geopandas")


# --- Zone Category Mapping ---

# Map zone_type codes to human-readable categories
ZONE_TYPE_TO_CATEGORY = {
    1: "Commercial",      # Business
    2: "Commercial",      # Commercial / Mixed-Use
    3: "Industrial",      # Manufacturing
    4: "Residential",     # Residential
    5: "Mixed",           # Planned Development
    6: "Industrial",      # Planned Manufacturing District
    7: "Mixed",           # Downtown Mixed-Use
    8: "Commercial",      # Downtown Core
    9: "Residential",     # Downtown Residential
    10: "Commercial",     # Downtown Service
    11: "Transport",      # Transportation
    12: "Parks",          # Parks and Open Space
}

# Low-density residential zones (candidates for upzoning near transit)
LOW_DENSITY_ZONES = {
    "RS-1", "RS-2", "RS-3",  # Single-family
    "RT-3.5", "RT-4", "RT-4A",  # Two-flat/townhouse
}

# Transit-oriented development target zones
TOD_TARGET_ZONES = {"RM-5", "RM-5.5", "RM-6", "B2-3", "B2-5", "B3-3", "B3-5"}


# --- Spatial Join Functions ---

def load_zoning_codes() -> pd.DataFrame:
    """
    Load zoning codes reference data with FAR, height, and category info.
    
    Returns:
        DataFrame with zoning code details
    """
    if not ZONING_CODES_CSV.exists():
        print(f"WARNING: Zoning codes file not found at {ZONING_CODES_CSV}")
        return pd.DataFrame()
    
    df = pd.read_csv(ZONING_CODES_CSV)
    return df


def spatial_join_parcels_to_zoning(
    parcels_gdf: gpd.GeoDataFrame,
    zoning_gdf: gpd.GeoDataFrame,
    use_centroid: bool = True
) -> gpd.GeoDataFrame:
    """
    Join parcels to zoning polygons via spatial join.
    
    Uses parcel centroids by default for faster, more accurate point-in-polygon
    matching (handles parcels that span multiple zones).
    
    Args:
        parcels_gdf: GeoDataFrame of parcel geometries
        zoning_gdf: GeoDataFrame of zoning polygons
        use_centroid: If True, use parcel centroids; if False, use full geometry
    
    Returns:
        GeoDataFrame with zoning attributes joined to parcels
    """
    if parcels_gdf is None or parcels_gdf.empty:
        print("ERROR: Parcels GeoDataFrame is empty or None")
        return None
    
    if zoning_gdf is None or zoning_gdf.empty:
        print("ERROR: Zoning GeoDataFrame is empty or None")
        return None
    
    print(f"Joining {len(parcels_gdf)} parcels to {len(zoning_gdf)} zoning polygons...")
    
    # Ensure both have the same CRS
    if parcels_gdf.crs != zoning_gdf.crs:
        print(f"  Reprojecting zoning from {zoning_gdf.crs} to {parcels_gdf.crs}")
        zoning_gdf = zoning_gdf.to_crs(parcels_gdf.crs)
    
    # Create a working copy
    parcels = parcels_gdf.copy()
    
    if use_centroid:
        # Store original geometry and CRS
        parcels["_original_geometry"] = parcels.geometry
        original_crs = parcels.crs
        
        # Project to Illinois State Plane for accurate centroid calculation
        parcels_proj = parcels.to_crs("EPSG:3435")
        centroids = parcels_proj.geometry.centroid
        
        # Project centroids back to original CRS
        parcels["geometry"] = centroids.to_crs(original_crs)
    
    # Perform spatial join
    joined = gpd.sjoin(
        parcels,
        zoning_gdf,
        how="left",
        predicate="within" if use_centroid else "intersects"
    )
    
    # Restore original geometry if we used centroids
    if use_centroid and "_original_geometry" in joined.columns:
        joined["geometry"] = joined["_original_geometry"]
        joined = joined.drop(columns=["_original_geometry"])
    
    # Remove the spatial join index column
    if "index_right" in joined.columns:
        joined = joined.drop(columns=["index_right"])
    
    # Calculate join rate
    join_rate = (joined["zone_class"].notna().sum() / len(joined)) * 100 if "zone_class" in joined.columns else 0
    print(f"  Join rate: {join_rate:.1f}% of parcels matched to zoning polygons")
    
    return joined


def add_zone_category(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Add zone_category column based on zone_type.
    
    Categories: Residential, Commercial, Mixed, Industrial, Parks, Transport
    """
    if gdf is None:
        return None
    
    result = gdf.copy()
    
    # Try to find zone_type column (may be named differently)
    zone_type_col = None
    for col in ["zone_type", "ZONE_TYPE", "zoning_type"]:
        if col in result.columns:
            zone_type_col = col
            break
    
    if zone_type_col is None:
        print("WARNING: No zone_type column found, cannot classify categories")
        result["zone_category"] = "Unknown"
        return result
    
    # Convert zone_type to int and map to category
    result["zone_category"] = (
        pd.to_numeric(result[zone_type_col], errors="coerce")
        .fillna(0)
        .astype(int)
        .map(ZONE_TYPE_TO_CATEGORY)
        .fillna("Unknown")
    )
    
    # Print category distribution
    print("Zone category distribution:")
    for cat, count in result["zone_category"].value_counts().items():
        print(f"  {cat}: {count:,}")
    
    return result


def enrich_with_zoning_codes(
    parcels_gdf: gpd.GeoDataFrame,
    zoning_codes_df: pd.DataFrame
) -> gpd.GeoDataFrame:
    """
    Enrich parcels with FAR, max_height, and other zoning code attributes.
    
    Args:
        parcels_gdf: GeoDataFrame with zone_class column
        zoning_codes_df: DataFrame with zoning code reference data
    
    Returns:
        GeoDataFrame with additional zoning attributes
    """
    if parcels_gdf is None or zoning_codes_df is None or zoning_codes_df.empty:
        return parcels_gdf
    
    result = parcels_gdf.copy()
    
    # Normalize zone_class column name
    zone_class_col = None
    for col in ["zone_class", "ZONE_CLASS", "zoning_class"]:
        if col in result.columns:
            zone_class_col = col
            break
    
    if zone_class_col is None:
        print("WARNING: No zone_class column found for enrichment")
        return result
    
    # Create lookup from zoning codes
    code_lookup = zoning_codes_df.set_index("district_type_code")
    
    # Map FAR
    if "floor_area_ratio" in code_lookup.columns:
        far_map = code_lookup["floor_area_ratio"].to_dict()
        result["far"] = result[zone_class_col].map(far_map)
        # Convert FAR to numeric (some values may be text like "Varies")
        result["far"] = pd.to_numeric(result["far"], errors="coerce")
    
    # Map max height
    if "maximum_building_height" in code_lookup.columns:
        height_map = code_lookup["maximum_building_height"].to_dict()
        result["max_height"] = result[zone_class_col].map(height_map)
    
    # Map zone_type from reference data
    if "zone_type" in code_lookup.columns and "zone_type" not in result.columns:
        type_map = code_lookup["zone_type"].to_dict()
        result["zone_type"] = result[zone_class_col].map(type_map)
    
    return result


# --- Transit Analysis Functions ---

def identify_transit_corridor_parcels(
    parcels_gdf: gpd.GeoDataFrame,
    stations_gdf: gpd.GeoDataFrame,
    buffer_meters: float = 800  # ~0.5 mile / 10 min walk
) -> gpd.GeoDataFrame:
    """
    Identify parcels within walking distance of transit stations.
    
    Args:
        parcels_gdf: GeoDataFrame of parcels
        stations_gdf: GeoDataFrame of transit station points
        buffer_meters: Buffer distance in meters (default 800m = ~0.5 mile)
    
    Returns:
        GeoDataFrame with 'near_transit' boolean column
    """
    if parcels_gdf is None or stations_gdf is None:
        return parcels_gdf
    
    result = parcels_gdf.copy()
    
    # Project to a meter-based CRS for accurate buffering (Illinois State Plane)
    il_crs = "EPSG:3435"  # Illinois State Plane East (feet) - use EPSG:26971 for meters
    
    try:
        stations_projected = stations_gdf.to_crs(il_crs)
        parcels_projected = result.to_crs(il_crs)
        
        # Create buffer around stations (convert meters to feet for IL State Plane)
        buffer_feet = buffer_meters * 3.28084
        transit_buffer = stations_projected.geometry.buffer(buffer_feet).union_all()
        
        # Check which parcel centroids fall within buffer
        centroids = parcels_projected.geometry.centroid
        result["near_transit"] = centroids.within(transit_buffer)
        
        near_count = result["near_transit"].sum()
        print(f"Found {near_count:,} parcels within {buffer_meters}m of transit ({near_count/len(result)*100:.1f}%)")
        
    except Exception as e:
        print(f"WARNING: Transit proximity analysis failed: {e}")
        result["near_transit"] = False
    
    return result


def identify_upzoning_candidates(parcels_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Identify parcels that are candidates for upzoning based on:
    - Being near transit
    - Currently zoned for low density
    
    Args:
        parcels_gdf: GeoDataFrame with zone_class and near_transit columns
    
    Returns:
        GeoDataFrame with 'upzoning_candidate' boolean and 'upzoning_reason' columns
    """
    if parcels_gdf is None:
        return None
    
    result = parcels_gdf.copy()
    
    # Initialize columns
    result["upzoning_candidate"] = False
    result["upzoning_reason"] = ""
    
    # Find zone_class column
    zone_class_col = None
    for col in ["zone_class", "ZONE_CLASS", "zoning_class"]:
        if col in result.columns:
            zone_class_col = col
            break
    
    if zone_class_col is None:
        print("WARNING: No zone_class column found")
        return result
    
    # Criterion 1: Low-density residential near transit
    if "near_transit" in result.columns:
        is_low_density = result[zone_class_col].isin(LOW_DENSITY_ZONES)
        transit_upzone = is_low_density & result["near_transit"]
        result.loc[transit_upzone, "upzoning_candidate"] = True
        result.loc[transit_upzone, "upzoning_reason"] = "Low-density near transit"
        
        print(f"Transit upzoning candidates: {transit_upzone.sum():,}")
    
    # Additional criteria can be added here (e.g., underutilized commercial)
    
    total_candidates = result["upzoning_candidate"].sum()
    print(f"Total upzoning candidates: {total_candidates:,} ({total_candidates/len(result)*100:.1f}%)")
    
    return result


# --- Summary Statistics ---

def calculate_zone_summary(parcels_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Calculate summary statistics per zone type.
    
    Returns DataFrame with:
    - parcel_count: Number of parcels
    - total_area_sqft: Total parcel area
    - avg_assessed_value: Average assessed value (if available)
    - pct_near_transit: Percent of parcels near transit
    """
    if parcels_gdf is None:
        return pd.DataFrame()
    
    result = parcels_gdf.copy()
    
    # Find zone columns
    zone_class_col = None
    for col in ["zone_class", "ZONE_CLASS", "zoning_class"]:
        if col in result.columns:
            zone_class_col = col
            break
    
    if zone_class_col is None:
        print("WARNING: No zone_class column for summary")
        return pd.DataFrame()
    
    # Calculate parcel area if not present
    if "area_sqft" not in result.columns:
        try:
            # Project to Illinois State Plane for area calculation
            projected = result.to_crs("EPSG:3435")
            result["area_sqft"] = projected.geometry.area  # Already in sq feet
        except Exception:
            result["area_sqft"] = 0
    
    # Group by zone class
    summary = result.groupby(zone_class_col).agg(
        parcel_count=(zone_class_col, "count"),
        total_area_sqft=("area_sqft", "sum"),
    ).reset_index()
    
    summary.columns = ["zone_class", "parcel_count", "total_area_sqft"]
    
    # Add assessed value if available
    value_cols = ["mailed_tot", "certified_tot", "assessed_value", "total_value"]
    for col in value_cols:
        if col in result.columns:
            avg_value = result.groupby(zone_class_col)[col].mean().reset_index()
            avg_value.columns = ["zone_class", "avg_assessed_value"]
            summary = summary.merge(avg_value, on="zone_class", how="left")
            break
    
    # Add transit proximity percentage
    if "near_transit" in result.columns:
        transit_pct = (
            result.groupby(zone_class_col)["near_transit"]
            .mean() * 100
        ).reset_index()
        transit_pct.columns = ["zone_class", "pct_near_transit"]
        summary = summary.merge(transit_pct, on="zone_class", how="left")
    
    # Add zone category
    zoning_codes = load_zoning_codes()
    if not zoning_codes.empty and "zone_type" in zoning_codes.columns:
        type_map = zoning_codes.set_index("district_type_code")["zone_type"].to_dict()
        summary["zone_type"] = summary["zone_class"].map(type_map)
        summary["zone_category"] = (
            pd.to_numeric(summary["zone_type"], errors="coerce")
            .fillna(0)
            .astype(int)
            .map(ZONE_TYPE_TO_CATEGORY)
        )
    
    # Sort by parcel count
    summary = summary.sort_values("parcel_count", ascending=False)
    
    return summary


# --- Legacy Functions (updated) ---

def classify_existing_density(parcels_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Classify parcels by existing density category based on zone_type.
    """
    if parcels_gdf is None:
        return None
    
    result = parcels_gdf.copy()
    result["existing_density_category"] = result.get("zone_category", "Unknown")
    return result


def generate_proposed_zoning(
    current_zoning_gdf: gpd.GeoDataFrame,
    proposed_rules: dict | None = None
) -> gpd.GeoDataFrame:
    """
    Create proposed zoning layer by applying plan rules to current zoning.
    """
    if current_zoning_gdf is None:
        return None
    
    proposed = current_zoning_gdf.copy()
    zone_col = "zone_class" if "zone_class" in proposed.columns else "ZONE_CLASS"
    proposed["proposed_zoning_class"] = proposed.get(zone_col, "Unknown")
    
    # Apply upzoning rules if provided
    if proposed_rules:
        for current_zone, new_zone in proposed_rules.items():
            mask = proposed[zone_col] == current_zone
            proposed.loc[mask, "proposed_zoning_class"] = new_zone
    
    return proposed


def assign_proposed_density(
    parcels_gdf: gpd.GeoDataFrame,
    proposed_zoning_gdf: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Assign proposed density categories to parcels via spatial join.
    """
    if parcels_gdf is None or proposed_zoning_gdf is None:
        return None
    
    # Perform spatial join
    assigned = spatial_join_parcels_to_zoning(parcels_gdf, proposed_zoning_gdf)
    
    if "proposed_zoning_class" in assigned.columns:
        assigned["proposed_density_category"] = assigned["proposed_zoning_class"]
    else:
        assigned["proposed_density_category"] = "Unknown"
    
    return assigned


# --- Main Pipeline ---

def run_zoning_analysis(
    parcels_path: Path | None = None,
    zoning_path: Path | None = None,
    stations_path: Path | None = None,
    output_enriched: Path | None = None,
    output_summary: Path | None = None,
) -> tuple[gpd.GeoDataFrame | None, pd.DataFrame | None]:
    """
    Run the full zoning analysis pipeline.
    
    Args:
        parcels_path: Path to parcels GeoJSON (default from config)
        zoning_path: Path to zoning GeoJSON (default from config)
        stations_path: Path to CTA stations GeoJSON (default from config)
        output_enriched: Path for enriched parcels output
        output_summary: Path for summary CSV output
    
    Returns:
        Tuple of (enriched_parcels_gdf, summary_df)
    """
    ensure_dirs()
    
    # Use defaults from config
    parcels_path = parcels_path or PARCEL_GEOJSON
    zoning_path = zoning_path or ZONING_GEOJSON
    stations_path = stations_path or CTA_STATIONS_GEOJSON
    output_enriched = output_enriched or PARCELS_ENRICHED_GEOJSON
    output_summary = output_summary or ZONING_SUMMARY_CSV
    
    # Load data
    print("Loading datasets...")
    
    if not parcels_path.exists():
        print(f"ERROR: Parcels file not found: {parcels_path}")
        return None, None
    parcels = gpd.read_file(parcels_path)
    print(f"  Loaded {len(parcels):,} parcels")
    
    if not zoning_path.exists():
        print(f"ERROR: Zoning file not found: {zoning_path}")
        return None, None
    zoning = gpd.read_file(zoning_path)
    print(f"  Loaded {len(zoning):,} zoning polygons")
    
    stations = None
    if stations_path.exists():
        stations = gpd.read_file(stations_path)
        print(f"  Loaded {len(stations):,} CTA stations")
    else:
        print(f"  WARNING: CTA stations file not found, skipping transit analysis")
    
    # Load zoning codes reference
    zoning_codes = load_zoning_codes()
    print(f"  Loaded {len(zoning_codes)} zoning code definitions")
    
    # Step 1: Spatial join parcels to zoning
    print("\nStep 1: Spatial join parcels to zoning polygons...")
    enriched = spatial_join_parcels_to_zoning(parcels, zoning)
    
    if enriched is None:
        print("ERROR: Spatial join failed")
        return None, None
    
    # Step 2: Enrich with zoning code attributes (FAR, height)
    print("\nStep 2: Enriching with zoning code attributes...")
    enriched = enrich_with_zoning_codes(enriched, zoning_codes)
    
    # Step 3: Add zone category
    print("\nStep 3: Adding zone categories...")
    enriched = add_zone_category(enriched)
    
    # Step 4: Transit proximity analysis
    if stations is not None:
        print("\nStep 4: Analyzing transit proximity...")
        enriched = identify_transit_corridor_parcels(enriched, stations)
        
        # Step 5: Identify upzoning candidates
        print("\nStep 5: Identifying upzoning candidates...")
        enriched = identify_upzoning_candidates(enriched)
    
    # Step 6: Calculate summary statistics
    print("\nStep 6: Calculating summary statistics...")
    summary = calculate_zone_summary(enriched)
    
    # Save outputs
    print("\nSaving outputs...")
    
    # Save enriched parcels
    enriched.to_file(str(output_enriched), driver="GeoJSON")
    print(f"  Saved enriched parcels to {output_enriched}")
    
    # Save summary
    summary.to_csv(output_summary, index=False)
    print(f"  Saved zoning summary to {output_summary}")
    
    # Print summary
    print("\n" + "="*50)
    print("ZONING ANALYSIS SUMMARY")
    print("="*50)
    print(f"Total parcels processed: {len(enriched):,}")
    
    if "zone_category" in enriched.columns:
        print("\nParcels by category:")
        for cat, count in enriched["zone_category"].value_counts().items():
            print(f"  {cat}: {count:,} ({count/len(enriched)*100:.1f}%)")
    
    if "upzoning_candidate" in enriched.columns:
        candidates = enriched["upzoning_candidate"].sum()
        print(f"\nUpzoning candidates: {candidates:,} ({candidates/len(enriched)*100:.1f}%)")
    
    return enriched, summary


if __name__ == "__main__":
    print("Zoning Analysis Module")
    print("="*50)
    print("\nHousing Density Categories:")
    for code, info in HOUSING_DENSITY_CATEGORIES.items():
        print(f"  {code}: {info['name']} ({info['units_per_acre_min']}-{info['units_per_acre_max']} units/acre)")
    
    print("\nZone Type Categories:")
    for code, name in ZONE_TYPE_NAMES.items():
        category = ZONE_TYPE_TO_CATEGORY.get(code, "Unknown")
        print(f"  {code}: {name} -> {category}")
    
    print("\n" + "="*50)
    print("Running zoning analysis...")
    print("="*50)
    
    enriched, summary = run_zoning_analysis()
    
    if enriched is not None:
        print("\nAnalysis complete!")
    else:
        print("\nAnalysis failed - check that data files exist.")
        print(f"Expected files:")
        print(f"  - {PARCEL_GEOJSON}")
        print(f"  - {ZONING_GEOJSON}")
        print(f"  - {CTA_STATIONS_GEOJSON} (optional)")

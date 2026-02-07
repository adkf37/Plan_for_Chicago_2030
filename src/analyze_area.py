"""
Analyze Area — Near South Side Parcel Analysis
===============================================
Loads Cook County parcel + assessment CSVs, merges on PIN, filters to a
bounding box (Near South Side), exports parcels to CSV, and generates
an interactive Folium value map.

Usage:
    python -m src.analyze_area
"""

import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from shapely.geometry import Point, Polygon
import warnings

from src.config import (
    RAW_ASSESSMENT_CSV, RAW_PARCEL_UNIVERSE_CSV,
    PARCELS_IN_AREA_CSV, AREA_VALUE_MAP,
    STUDY_AREA, PROCESSED_DIR, MAPS_DIR, ensure_dirs,
)

# --- Configuration ---
PIN_COLUMN_ASSESSMENT = "pin"
VALUE_COLUMN = "certified_tot"
CLASS_COLUMN_ASSESSMENT = "class"
PIN_COLUMN_UNIVERSE = "pin"
LATITUDE_COLUMN = "latitude"
LONGITUDE_COLUMN = "longitude"
UNIVERSE_ATTRIBUTES = ["CLS_CLASS_DESCRIPTION", "NBHD_DESC", "BLDG_SQ_FT"]


def main():
    ensure_dirs()

    # Define area of interest
    min_lon = STUDY_AREA["min_lon"]
    max_lon = STUDY_AREA["max_lon"]
    min_lat = STUDY_AREA["min_lat"]
    max_lat = STUDY_AREA["max_lat"]
    bbox = Polygon([
        (min_lon, min_lat), (min_lon, max_lat),
        (max_lon, max_lat), (max_lon, min_lat),
        (min_lon, min_lat),
    ])
    bbox_gdf = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:4326")
    print(f"Defined Bounding Box: {bbox.bounds}")

    # --- Load parcel universe ---
    print(f"Loading parcel universe data from '{RAW_PARCEL_UNIVERSE_CSV}'...")
    try:
        parcels_df = pd.read_csv(RAW_PARCEL_UNIVERSE_CSV)
        print(f"Loaded {len(parcels_df)} parcel universe records.")

        required_cols = [PIN_COLUMN_UNIVERSE, LONGITUDE_COLUMN, LATITUDE_COLUMN]
        missing_req = [c for c in required_cols if c not in parcels_df.columns]
        if missing_req:
            print(f"ERROR: Required columns missing: {missing_req}")
            return

        # Filter to available attribute columns
        global UNIVERSE_ATTRIBUTES
        UNIVERSE_ATTRIBUTES = [c for c in UNIVERSE_ATTRIBUTES if c in parcels_df.columns]

        parcels_gdf = gpd.GeoDataFrame(
            parcels_df,
            geometry=gpd.points_from_xy(parcels_df[LONGITUDE_COLUMN], parcels_df[LATITUDE_COLUMN]),
            crs="EPSG:4326",
        )
        parcels_gdf = parcels_gdf[parcels_gdf.geometry.is_valid & ~parcels_gdf.geometry.is_empty]
        print(f"Created {len(parcels_gdf)} valid point geometries.")
    except FileNotFoundError:
        print(f"ERROR: File not found: {RAW_PARCEL_UNIVERSE_CSV}")
        return
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # --- Load assessment data ---
    print(f"Loading assessment data from '{RAW_ASSESSMENT_CSV}'...")
    try:
        assessment_df = pd.read_csv(RAW_ASSESSMENT_CSV)
        print(f"Loaded {len(assessment_df)} assessment records.")
        for col in [PIN_COLUMN_ASSESSMENT, VALUE_COLUMN]:
            if col not in assessment_df.columns:
                print(f"ERROR: Column '{col}' not found.")
                return
    except FileNotFoundError:
        print(f"ERROR: File not found: {RAW_ASSESSMENT_CSV}")
        return

    # --- Clean & merge ---
    parcels_gdf[PIN_COLUMN_UNIVERSE] = parcels_gdf[PIN_COLUMN_UNIVERSE].astype(str).str.replace("-", "", regex=False)
    assessment_df[PIN_COLUMN_ASSESSMENT] = assessment_df[PIN_COLUMN_ASSESSMENT].astype(str).str.replace("-", "", regex=False)

    assessment_df[VALUE_COLUMN] = pd.to_numeric(
        assessment_df[VALUE_COLUMN].astype(str).str.replace(r"[$,]", "", regex=True),
        errors="coerce",
    )
    assessment_df = assessment_df.dropna(subset=[VALUE_COLUMN])

    merge_cols = [PIN_COLUMN_ASSESSMENT, VALUE_COLUMN, CLASS_COLUMN_ASSESSMENT]
    merged_gdf = parcels_gdf.merge(
        assessment_df[merge_cols],
        left_on=PIN_COLUMN_UNIVERSE,
        right_on=PIN_COLUMN_ASSESSMENT,
        how="left",
    )

    # Handle duplicate columns from merge
    if f"{CLASS_COLUMN_ASSESSMENT}_x" in merged_gdf.columns:
        merged_gdf = merged_gdf.drop(columns=[f"{CLASS_COLUMN_ASSESSMENT}_x"])
    if f"{CLASS_COLUMN_ASSESSMENT}_y" in merged_gdf.columns:
        merged_gdf = merged_gdf.rename(columns={f"{CLASS_COLUMN_ASSESSMENT}_y": CLASS_COLUMN_ASSESSMENT})
    if PIN_COLUMN_ASSESSMENT != PIN_COLUMN_UNIVERSE and PIN_COLUMN_ASSESSMENT in merged_gdf.columns:
        merged_gdf = merged_gdf.drop(columns=[PIN_COLUMN_ASSESSMENT])

    final_cols = [c for c in [PIN_COLUMN_UNIVERSE, "geometry", VALUE_COLUMN, CLASS_COLUMN_ASSESSMENT] + UNIVERSE_ATTRIBUTES if c in merged_gdf.columns]
    merged_gdf = merged_gdf[final_cols]
    print(f"Merged data: {len(merged_gdf)} records.")

    # --- Filter to bounding box ---
    parcels_in_area = gpd.sjoin(merged_gdf, bbox_gdf, how="inner", predicate="within")
    if len(parcels_in_area) == 0:
        print("No parcels found in the study area.")
        return
    print(f"Found {len(parcels_in_area)} parcels in the study area.")

    total_value = parcels_in_area[VALUE_COLUMN].sum()
    print(f"\nAggregate {VALUE_COLUMN}: ${total_value:,.2f}")

    # --- Export CSV ---
    export_df = parcels_in_area.copy()
    export_df["geometry_wkt"] = export_df["geometry"].apply(lambda g: g.wkt if g else None)
    export_columns = [c for c in [PIN_COLUMN_UNIVERSE, "geometry_wkt", VALUE_COLUMN, CLASS_COLUMN_ASSESSMENT] if c in export_df.columns]
    output_df = export_df[export_columns].rename(columns={
        PIN_COLUMN_UNIVERSE: "pin",
        "geometry_wkt": "geometry",
        VALUE_COLUMN: "certified_tot",
        CLASS_COLUMN_ASSESSMENT: "class",
    })
    output_df.to_csv(PARCELS_IN_AREA_CSV, index=False)
    print(f"Saved to '{PARCELS_IN_AREA_CSV}'")

    # --- Create map ---
    map_center = [bbox.centroid.y, bbox.centroid.x]
    m = folium.Map(location=map_center, zoom_start=15, tiles="CartoDB positron")

    folium.GeoJson(
        bbox_gdf.__geo_interface__,
        name="Area Boundary",
        style_function=lambda feature: {"color": "red", "weight": 3, "fillOpacity": 0},
    ).add_to(m)

    parcels_in_area = parcels_in_area.dropna(subset=[VALUE_COLUMN, "geometry"])
    if not parcels_in_area.empty:
        import numpy as np
        parcels_in_area["value_quantile"] = pd.qcut(parcels_in_area[VALUE_COLUMN], 5, labels=False, duplicates="drop")
        colors = ["#ffffcc", "#c7e9b4", "#7fcdbb", "#41b6c4", "#2c7fb8"]

        def get_color(q):
            return colors[int(q)] if pd.notna(q) else "#808080"

        points_layer = folium.FeatureGroup(name="Parcel Values (Points)")
        for _, row in parcels_in_area.iterrows():
            tooltip = f"PIN: {row[PIN_COLUMN_UNIVERSE]}<br>Value: ${row[VALUE_COLUMN]:,.0f}"
            for attr in UNIVERSE_ATTRIBUTES:
                if attr in row and pd.notna(row[attr]):
                    tooltip += f"<br>{attr.replace('_', ' ').title()}: {row[attr]}"
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=3,
                color=get_color(row["value_quantile"]),
                fill=True,
                fill_color=get_color(row["value_quantile"]),
                fill_opacity=0.7,
                tooltip=tooltip,
            ).add_to(points_layer)
        points_layer.add_to(m)

        legend_html = f'''
        <div style="position: fixed; bottom: 50px; left: 50px; width: 150px; height: 90px;
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color: white; opacity: 0.8;">
        &nbsp;<b>Value Quantile</b><br>
        &nbsp;<i class="fa fa-circle" style="color:{colors[0]}"></i>&nbsp; Lowest<br>
        &nbsp;...<br>
        &nbsp;<i class="fa fa-circle" style="color:{colors[-1]}"></i>&nbsp; Highest
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl().add_to(m)
    m.save(str(AREA_VALUE_MAP))
    print(f"Value map saved to '{AREA_VALUE_MAP}'")


if __name__ == "__main__":
    main()

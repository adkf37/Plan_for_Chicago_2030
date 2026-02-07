"""
Download Data from Cook County & Chicago Data Portals
=====================================================
Downloads parcel geometries, assessment data, and zoning data via Socrata APIs
and saves them to the data/geojson/ directory.

Usage:
    python -m src.download_data
"""

from src.config import (
    PARCEL_GEOMETRY_URL, ASSESSMENT_DATA_URL, ZONING_DATA_URL,
    PARCEL_GEOJSON, ASSESSMENT_GEOJSON, ZONING_GEOJSON,
    ensure_dirs,
)
from src.data_utils import fetch_all_socrata_data


def download_all_datasets():
    """Download all datasets and save to data/geojson/."""
    ensure_dirs()

    # Download Parcel Geometries
    print("\n--- Downloading Parcel Geometries ---")
    parcel_gdf = fetch_all_socrata_data(PARCEL_GEOMETRY_URL)
    if parcel_gdf is not None:
        parcel_gdf.to_file(str(PARCEL_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(parcel_gdf)} parcel records to {PARCEL_GEOJSON}")

    # Download Assessment Data
    print("\n--- Downloading Assessment Data ---")
    assessment_gdf = fetch_all_socrata_data(ASSESSMENT_DATA_URL)
    if assessment_gdf is not None:
        assessment_gdf.to_file(str(ASSESSMENT_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(assessment_gdf)} assessment records to {ASSESSMENT_GEOJSON}")

    # Download Zoning Data
    print("\n--- Downloading Zoning Data ---")
    zoning_gdf = fetch_all_socrata_data(ZONING_DATA_URL)
    if zoning_gdf is not None:
        zoning_gdf.to_file(str(ZONING_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(zoning_gdf)} zoning records to {ZONING_GEOJSON}")


if __name__ == "__main__":
    print("Starting data download process...")
    download_all_datasets()
    print("Download process complete.")

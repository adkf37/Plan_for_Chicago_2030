"""
Download Data from Cook County & Chicago Data Portals
=====================================================
Downloads parcel geometries, assessment data, zoning data, census tracts,
and CTA station locations via Socrata APIs and Census Bureau, saving them
to the data/geojson/ directory.

Usage:
    python -m src.download_data
"""

import geopandas as gpd
import io
import requests
import tempfile
import zipfile
from pathlib import Path

from src.config import (
    PARCEL_GEOMETRY_URL, ASSESSMENT_DATA_URL, ZONING_DATA_URL,
    PARCEL_GEOJSON, ASSESSMENT_GEOJSON, ZONING_GEOJSON,
    CTA_STATIONS_URL, CTA_STATIONS_GEOJSON,
    CTA_BUS_ROUTES_URL, CTA_BUS_ROUTES_GEOJSON,
    METRA_STATIONS_URL, METRA_STATIONS_GEOJSON,
    CENSUS_TRACTS_URL, CENSUS_TRACTS_GEOJSON,
    ensure_dirs,
)
from src.data_utils import fetch_all_socrata_data, validate_dataframe


def download_census_tracts(cook_county_fips: str = "031") -> gpd.GeoDataFrame | None:
    """
    Download Census tract boundaries from TIGER/Line shapefiles.

    Downloads Illinois tract boundaries and filters to Cook County.

    Args:
        cook_county_fips: FIPS code for Cook County (default "031")

    Returns:
        GeoDataFrame of Cook County census tracts, or None on failure.
    """
    print(f"Downloading Census tract boundaries from {CENSUS_TRACTS_URL}...")

    try:
        response = requests.get(CENSUS_TRACTS_URL, timeout=120)
        response.raise_for_status()

        # Extract shapefile from zip
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "tracts.zip"
            with open(zip_path, "wb") as f:
                f.write(response.content)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            # Find the .shp file
            shp_files = list(Path(tmpdir).glob("*.shp"))
            if not shp_files:
                print("ERROR: No shapefile found in zip archive")
                return None

            # Read shapefile
            gdf = gpd.read_file(shp_files[0])

            # Filter to Cook County (COUNTYFP == "031")
            cook_tracts = gdf[gdf["COUNTYFP"] == cook_county_fips].copy()

            # Reproject to WGS84 for consistency
            if cook_tracts.crs and cook_tracts.crs != "EPSG:4326":
                cook_tracts = cook_tracts.to_crs("EPSG:4326")

            print(f"Filtered to {len(cook_tracts)} Cook County census tracts")
            return cook_tracts

    except requests.exceptions.RequestException as e:
        print(f"ERROR downloading census tracts: {e}")
        return None
    except Exception as e:
        print(f"ERROR processing census tracts: {e}")
        return None


def download_cta_stations() -> gpd.GeoDataFrame | None:
    """
    Download CTA L station locations from Chicago Data Portal.

    Returns:
        GeoDataFrame of CTA L stations, or None on failure.
    """
    print(f"\n--- Downloading CTA L Stations ---")
    stations_gdf = fetch_all_socrata_data(CTA_STATIONS_URL)

    if stations_gdf is not None:
        # Validate
        errors = validate_dataframe(
            stations_gdf,
            "CTA Stations",
            required_columns=["geometry"],
            min_rows=100,  # Chicago has 140+ L stations
            expected_crs="EPSG:4326"
        )
        if errors:
            for err in errors:
                print(f"  WARNING: {err}")

        print(f"Downloaded {len(stations_gdf)} CTA L stations")

    return stations_gdf


def download_metra_stations() -> gpd.GeoDataFrame | None:
    """
    Download Metra commuter rail station locations from Chicago Data Portal.

    Returns:
        GeoDataFrame of Metra stations, or None on failure.
    """
    print(f"\n--- Downloading Metra Stations ---")
    stations_gdf = fetch_all_socrata_data(METRA_STATIONS_URL)

    if stations_gdf is not None:
        errors = validate_dataframe(
            stations_gdf,
            "Metra Stations",
            required_columns=["geometry"],
            min_rows=10,  # Metra has ~240 stations but some may be outside Chicago
            expected_crs="EPSG:4326",
        )
        if errors:
            for err in errors:
                print(f"  WARNING: {err}")

        print(f"Downloaded {len(stations_gdf)} Metra stations")

    return stations_gdf


def download_cta_bus_routes() -> gpd.GeoDataFrame | None:
    """
    Download CTA bus route polylines from Chicago Data Portal.

    Returns:
        GeoDataFrame of CTA bus routes, or None on failure.
    """
    print(f"\n--- Downloading CTA Bus Routes ---")
    routes_gdf = fetch_all_socrata_data(CTA_BUS_ROUTES_URL)

    if routes_gdf is not None:
        errors = validate_dataframe(
            routes_gdf,
            "CTA Bus Routes",
            required_columns=["geometry"],
            min_rows=50,
            expected_crs="EPSG:4326",
        )
        if errors:
            for err in errors:
                print(f"  WARNING: {err}")

        print(f"Downloaded {len(routes_gdf)} CTA bus routes")

    return routes_gdf


def download_all_datasets():
    """Download all datasets and save to data/geojson/."""
    ensure_dirs()
    all_errors = []

    # Download Parcel Geometries
    print("\n--- Downloading Parcel Geometries ---")
    parcel_gdf = fetch_all_socrata_data(PARCEL_GEOMETRY_URL)
    if parcel_gdf is not None:
        errors = validate_dataframe(parcel_gdf, "Parcels", min_rows=1000, expected_crs="EPSG:4326")
        all_errors.extend(errors)
        parcel_gdf.to_file(str(PARCEL_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(parcel_gdf)} parcel records to {PARCEL_GEOJSON}")

    # Download Assessment Data
    print("\n--- Downloading Assessment Data ---")
    assessment_gdf = fetch_all_socrata_data(ASSESSMENT_DATA_URL)
    if assessment_gdf is not None:
        errors = validate_dataframe(assessment_gdf, "Assessments", min_rows=1000)
        all_errors.extend(errors)
        assessment_gdf.to_file(str(ASSESSMENT_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(assessment_gdf)} assessment records to {ASSESSMENT_GEOJSON}")

    # Download Zoning Data
    print("\n--- Downloading Zoning Data ---")
    zoning_gdf = fetch_all_socrata_data(ZONING_DATA_URL)
    if zoning_gdf is not None:
        errors = validate_dataframe(zoning_gdf, "Zoning", min_rows=100, expected_crs="EPSG:4326")
        all_errors.extend(errors)
        zoning_gdf.to_file(str(ZONING_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(zoning_gdf)} zoning records to {ZONING_GEOJSON}")

    # Download Census Tracts
    print("\n--- Downloading Census Tract Boundaries ---")
    tracts_gdf = download_census_tracts()
    if tracts_gdf is not None:
        errors = validate_dataframe(
            tracts_gdf, "Census Tracts",
            required_columns=["GEOID", "geometry"],
            min_rows=1000,  # Cook County has ~1,300 tracts
            expected_crs="EPSG:4326"
        )
        all_errors.extend(errors)
        tracts_gdf.to_file(str(CENSUS_TRACTS_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(tracts_gdf)} census tracts to {CENSUS_TRACTS_GEOJSON}")

    # Download CTA Stations
    stations_gdf = download_cta_stations()
    if stations_gdf is not None:
        stations_gdf.to_file(str(CTA_STATIONS_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(stations_gdf)} CTA stations to {CTA_STATIONS_GEOJSON}")

    # Download Metra Stations
    metra_gdf = download_metra_stations()
    if metra_gdf is not None:
        metra_gdf.to_file(str(METRA_STATIONS_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(metra_gdf)} Metra stations to {METRA_STATIONS_GEOJSON}")

    # Download CTA Bus Routes
    bus_gdf = download_cta_bus_routes()
    if bus_gdf is not None:
        bus_gdf.to_file(str(CTA_BUS_ROUTES_GEOJSON), driver="GeoJSON")
        print(f"Saved {len(bus_gdf)} CTA bus routes to {CTA_BUS_ROUTES_GEOJSON}")

    # Report validation errors
    if all_errors:
        print("\n--- Validation Warnings ---")
        for err in all_errors:
            print(f"  - {err}")

    return len(all_errors) == 0


if __name__ == "__main__":
    print("Starting data download process...")
    success = download_all_datasets()
    if success:
        print("\nDownload process complete - all validations passed.")
    else:
        print("\nDownload process complete with warnings.")

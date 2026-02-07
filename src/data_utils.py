"""
Socrata API Utilities
=====================
Single source of truth for fetching data from Socrata-powered data portals
(Cook County, City of Chicago). Supports both JSON and GeoJSON endpoints
with pagination, spatial filtering, error handling, and caching.
"""

import geopandas as gpd
import hashlib
import json
import pandas as pd
import requests
import urllib.parse
import io
from pathlib import Path

from src.config import SOCRATA_APP_TOKEN, SOCRATA_LIMIT, CACHE_DIR


# --- Cache Utilities ---

def _get_cache_key(url: str) -> str:
    """Generate a cache key from URL."""
    return hashlib.md5(url.encode()).hexdigest()


def _get_cache_metadata_path(cache_key: str) -> Path:
    """Get path to cache metadata file (stores ETag, Last-Modified)."""
    return CACHE_DIR / f"{cache_key}.meta.json"


def _get_cache_data_path(cache_key: str, is_geojson: bool) -> Path:
    """Get path to cached data file."""
    ext = "geojson" if is_geojson else "json"
    return CACHE_DIR / f"{cache_key}.{ext}"


def _load_cache_metadata(cache_key: str) -> dict | None:
    """Load cache metadata (ETag, Last-Modified) if it exists."""
    meta_path = _get_cache_metadata_path(cache_key)
    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def _save_cache_metadata(cache_key: str, etag: str | None, last_modified: str | None):
    """Save cache metadata for conditional requests."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta_path = _get_cache_metadata_path(cache_key)
    metadata = {
        "etag": etag,
        "last_modified": last_modified,
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f)


def _load_cached_data(cache_key: str, is_geojson: bool):
    """Load cached data if it exists."""
    data_path = _get_cache_data_path(cache_key, is_geojson)
    if data_path.exists():
        try:
            if is_geojson:
                return gpd.read_file(data_path)
            else:
                return pd.read_json(data_path)
        except Exception:
            return None
    return None


def _save_cached_data(cache_key: str, data, is_geojson: bool):
    """Save data to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data_path = _get_cache_data_path(cache_key, is_geojson)
    if is_geojson:
        data.to_file(str(data_path), driver="GeoJSON")
    else:
        data.to_json(str(data_path))


def check_for_updates(base_url: str, app_token: str | None = None) -> tuple[bool, dict | None]:
    """
    Check if remote data has been updated using conditional HTTP headers.

    Args:
        base_url: Socrata API endpoint URL
        app_token: Socrata app token (default from config)

    Returns:
        Tuple of (needs_update: bool, cached_metadata: dict | None)
    """
    app_token = app_token or SOCRATA_APP_TOKEN
    cache_key = _get_cache_key(base_url)
    cached_meta = _load_cache_metadata(cache_key)

    if not cached_meta:
        return True, None

    headers = {"X-App-Token": app_token} if app_token else {}
    if cached_meta.get("etag"):
        headers["If-None-Match"] = cached_meta["etag"]
    if cached_meta.get("last_modified"):
        headers["If-Modified-Since"] = cached_meta["last_modified"]

    try:
        # HEAD request to check for updates without downloading data
        response = requests.head(f"{base_url}?$limit=1", headers=headers, timeout=10)
        if response.status_code == 304:
            print(f"  Data not modified since last fetch (304)")
            return False, cached_meta
        return True, cached_meta
    except requests.exceptions.RequestException:
        # On error, assume we need to update
        return True, cached_meta


# --- Data Validation ---

def validate_dataframe(df, name: str, required_columns: list[str] | None = None,
                       min_rows: int = 1, expected_crs: str | None = None) -> list[str]:
    """
    Validate a DataFrame or GeoDataFrame.

    Args:
        df: DataFrame or GeoDataFrame to validate
        name: Dataset name for error messages
        required_columns: List of columns that must be present
        min_rows: Minimum number of rows expected
        expected_crs: Expected CRS for GeoDataFrames (e.g., "EPSG:4326")

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    if df is None:
        errors.append(f"{name}: Data is None")
        return errors

    if len(df) < min_rows:
        errors.append(f"{name}: Expected at least {min_rows} rows, got {len(df)}")

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            errors.append(f"{name}: Missing required columns: {missing}")

    if expected_crs and hasattr(df, "crs"):
        if df.crs is None:
            errors.append(f"{name}: CRS is not set, expected {expected_crs}")
        elif str(df.crs) != expected_crs and df.crs.to_string() != expected_crs:
            # Allow comparison of CRS objects
            try:
                import pyproj
                if not pyproj.CRS(df.crs).equals(pyproj.CRS(expected_crs)):
                    errors.append(f"{name}: CRS mismatch - got {df.crs}, expected {expected_crs}")
            except Exception:
                pass  # If pyproj comparison fails, skip CRS validation

    return errors


# --- Data Fetching ---

def fetch_all_socrata_data(base_url, limit=None, app_token=None, where_clause=None, use_cache=True):
    """
    Fetch all records from a Socrata endpoint using pagination.

    Supports both JSON and GeoJSON endpoints. Automatically detects format
    from the URL extension. Uses ETag/Last-Modified caching to avoid
    redundant downloads.

    Args:
        base_url: Socrata API endpoint URL (ending in .json or .geojson)
        limit: Records per page (default from config)
        app_token: Socrata app token (default from config)
        where_clause: Optional SoQL WHERE clause for server-side filtering
        use_cache: Whether to use caching (default True)

    Returns:
        GeoDataFrame for GeoJSON endpoints, DataFrame for JSON, or None on failure.
    """
    limit = limit or SOCRATA_LIMIT
    app_token = app_token or SOCRATA_APP_TOKEN
    is_geojson = base_url.lower().endswith(".geojson")

    # Check cache first
    cache_key = _get_cache_key(base_url + (where_clause or ""))
    if use_cache:
        needs_update, cached_meta = check_for_updates(base_url, app_token)
        if not needs_update:
            cached_data = _load_cached_data(cache_key, is_geojson)
            if cached_data is not None:
                print(f"Using cached data for {base_url}")
                return cached_data

    headers = {"X-App-Token": app_token} if app_token else {}

    all_data = []
    offset = 0
    response_etag = None
    response_last_modified = None

    print(f"Fetching data from {base_url}...")

    while True:
        url = f"{base_url}?$limit={limit}&$offset={offset}"
        if where_clause:
            url += f"&$where={where_clause}"

        print(f"  Fetching page with offset {offset}...")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            # Capture cache headers from first response
            if offset == 0:
                response_etag = response.headers.get("ETag")
                response_last_modified = response.headers.get("Last-Modified")

            data_text = response.text

            # Check for empty / no-results responses
            if (
                not data_text
                or data_text.strip() in ("[]", "{}")
                or '"errorCode" : "query.soql.no-results"' in data_text
            ):
                print("  Received empty response — end of data.")
                break

            try:
                if is_geojson:
                    gdf = gpd.read_file(io.StringIO(data_text))
                    if gdf.empty:
                        print("  Empty GeoDataFrame — end of data.")
                        break
                    all_data.append(gdf)
                    num_records = len(gdf)
                else:
                    json_data = response.json()
                    if not isinstance(json_data, list) or not json_data:
                        print("  Empty JSON list — end of data.")
                        break
                    all_data.extend(json_data)
                    num_records = len(json_data)

                print(f"  Fetched {num_records} records.")
                if num_records < limit:
                    print("  Fewer than limit — last page.")
                    break
                offset += num_records

            except Exception as read_err:
                print(f"  ERROR reading data at offset {offset}: {read_err}")
                print(f"  Response snippet: {data_text[:200]}")
                break

        except requests.exceptions.RequestException as req_err:
            print(f"  ERROR during request at offset {offset}: {req_err}")
            break

    if not all_data:
        print("No data fetched.")
        return None

    print("Processing all fetched pages...")
    if is_geojson:
        full_gdf = pd.concat(all_data, ignore_index=True)
        crs = all_data[0].crs if all_data and all_data[0].crs else "EPSG:4326"
        full_gdf = gpd.GeoDataFrame(full_gdf, geometry="geometry", crs=crs)
        print(f"Total records fetched: {len(full_gdf)}")

        # Save to cache
        if use_cache:
            _save_cached_data(cache_key, full_gdf, is_geojson)
            _save_cache_metadata(cache_key, response_etag, response_last_modified)
            print(f"  Cached data for future use.")

        return full_gdf
    else:
        full_df = pd.DataFrame(all_data)
        print(f"Total records fetched: {len(full_df)}")

        # Save to cache
        if use_cache:
            _save_cached_data(cache_key, full_df, is_geojson)
            _save_cache_metadata(cache_key, response_etag, response_last_modified)
            print(f"  Cached data for future use.")

        return full_df


def try_spatial_filter(base_url, min_lon, max_lon, min_lat, max_lat,
                       app_token=None, limit=None):
    """
    Attempt server-side spatial filtering using Socrata's within_box function.

    Falls back gracefully — returns None if the endpoint doesn't support it,
    so callers can fall back to local filtering.

    Args:
        base_url: Socrata GeoJSON endpoint
        min_lon, max_lon, min_lat, max_lat: Bounding box coordinates
        app_token: Socrata app token (default from config)
        limit: Records per page (default from config)

    Returns:
        GeoDataFrame if successful, None if spatial filter not supported.
    """
    limit = limit or SOCRATA_LIMIT
    app_token = app_token or SOCRATA_APP_TOKEN
    headers = {"X-App-Token": app_token} if app_token else {}

    soql_where = f"within_box(geometry,{max_lat},{min_lon},{min_lat},{max_lon})"
    encoded_where = urllib.parse.quote(soql_where)
    print(f"Trying SoQL spatial filter: {soql_where}")

    url = f"{base_url}?$limit={limit}&$offset=0&$where={encoded_where}"

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 400:
            print("Server-side spatial filtering not supported (400). Will filter locally.")
            return None
        response.raise_for_status()

        data = gpd.read_file(io.StringIO(response.text))
        print(f"Server-side spatial filter succeeded — {len(data)} records on first page.")

        # Fetch all pages with the filter
        return fetch_all_socrata_data(base_url, limit, app_token, encoded_where)

    except Exception as e:
        print(f"Spatial filtering failed: {e}. Will filter locally.")
        return None

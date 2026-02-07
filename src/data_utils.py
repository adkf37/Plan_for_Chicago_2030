"""
Socrata API Utilities
=====================
Single source of truth for fetching data from Socrata-powered data portals
(Cook County, City of Chicago). Supports both JSON and GeoJSON endpoints
with pagination, spatial filtering, and error handling.
"""

import geopandas as gpd
import pandas as pd
import requests
import urllib.parse
import io

from src.config import SOCRATA_APP_TOKEN, SOCRATA_LIMIT


def fetch_all_socrata_data(base_url, limit=None, app_token=None, where_clause=None):
    """
    Fetch all records from a Socrata endpoint using pagination.

    Supports both JSON and GeoJSON endpoints. Automatically detects format
    from the URL extension.

    Args:
        base_url: Socrata API endpoint URL (ending in .json or .geojson)
        limit: Records per page (default from config)
        app_token: Socrata app token (default from config)
        where_clause: Optional SoQL WHERE clause for server-side filtering

    Returns:
        GeoDataFrame for GeoJSON endpoints, DataFrame for JSON, or None on failure.
    """
    limit = limit or SOCRATA_LIMIT
    app_token = app_token or SOCRATA_APP_TOKEN
    headers = {"X-App-Token": app_token} if app_token else {}

    all_data = []
    offset = 0
    is_geojson = base_url.lower().endswith(".geojson")

    print(f"Fetching data from {base_url}...")

    while True:
        url = f"{base_url}?$limit={limit}&$offset={offset}"
        if where_clause:
            url += f"&$where={where_clause}"

        print(f"  Fetching page with offset {offset}...")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
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
        return full_gdf
    else:
        full_df = pd.DataFrame(all_data)
        print(f"Total records fetched: {len(full_df)}")
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

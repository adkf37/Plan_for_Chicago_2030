import requests
import io
import geopandas as gpd
import pandas as pd
import urllib.parse

# --- Configuration ---
PARCEL_GEOMETRY_URL_BASE = "https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.geojson"
ASSESSMENT_DATA_URL_BASE = "https://datacatalog.cookcountyil.gov/resource/uzyt-m557.geojson"
ZONING_DATA_URL_BASE = "https://data.cityofchicago.org/resource/dj47-wfun.geojson"
APP_TOKEN = "ApE4oAonZT2D1PEE5ZY8xgs6M"  # Your Socrata App Token
LIMIT = 50000  # Records per page (adjust as needed, max is often 50000)

# Output files
PARCEL_DATA_PATH = "parcel_data.geojson"
ASSESSMENT_DATA_PATH = "assessment_data.geojson"
ZONING_DATA_PATH = "zoning_data.geojson"

def fetch_all_socrata_data(base_url, limit, app_token, where_clause=None):
    """Fetches records from a Socrata GeoJSON endpoint using pagination and optional server-side filtering."""
    all_gdfs = []
    offset = 0
    headers = {'X-App-Token': app_token}
    print(f"Fetching data from {base_url}...")
    while True:
        # Construct URL with limit, offset, and optional where clause
        url = f"{base_url}?$limit={limit}&$offset={offset}"
        if where_clause:
            url += f"&$where={where_clause}"

        print(f"  Fetching page with offset {offset}...")
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data_text = response.text
            # Check if the response is empty or just '[]' which indicates no more data
            if not data_text or data_text.strip() == '[]' or data_text.strip() == '{\n  "message" : "No results found.",\n  "errorCode" : "query.soql.no-results"\n}':
                 print("  Received empty or no results response, assuming end of data for this query.")
                 break

            # Attempt to read the GeoJSON data
            try:
                 gdf = gpd.read_file(io.StringIO(data_text))
                 if gdf.empty:
                     print("  Received empty GeoDataFrame, assuming end of data.")
                     break
                 all_gdfs.append(gdf)
                 print(f"  Fetched {len(gdf)} records.")
                 # If fewer records than the limit were returned, it's the last page
                 if len(gdf) < limit:
                     print("  Fetched fewer records than limit, assuming last page.")
                     break
                 offset += len(gdf) # Increment offset by the number of records actually received
            except Exception as read_error:
                 print(f"  ERROR reading GeoJSON from offset {offset}: {read_error}")
                 print(f"  Response text snippet: {data_text[:200]}") # Print snippet for debugging
                 break # Stop if there's an error reading the data

        except requests.exceptions.RequestException as req_error:
            print(f"  ERROR during request for offset {offset}: {req_error}")
            break # Stop if there's a request error

    if not all_gdfs:
        print("No data fetched.")
        return None
    else:
        print("Concatenating all fetched pages...")
        full_gdf = pd.concat(all_gdfs, ignore_index=True)
        # Ensure it's still a GeoDataFrame if geometry column exists
        if 'geometry' in full_gdf.columns:
             # Use the CRS from the first page fetched
             crs = all_gdfs[0].crs if all_gdfs and all_gdfs[0].crs else "EPSG:4326"
             full_gdf = gpd.GeoDataFrame(full_gdf, geometry='geometry', crs=crs)
        print(f"Total records fetched: {len(full_gdf)}")
        return full_gdf

def try_spatial_filter(base_url, min_lon, max_lon, min_lat, max_lat, app_token, limit=50000):
    """
    Attempt to use server-side spatial filtering with the within_box function.
    Returns None if it fails (API doesn't support this filter for the endpoint).
    """
    # Construct SoQL where clause for spatial filtering
    soql_where_clause = f"within_box(geometry,{max_lat},{min_lon},{min_lat},{max_lon})"
    encoded_where_clause = urllib.parse.quote(soql_where_clause)
    print(f"Trying SoQL filter: {soql_where_clause}")
    
    # Try one request with the filter
    url = f"{base_url}?$limit={limit}&$offset=0&$where={encoded_where_clause}"
    headers = {'X-App-Token': app_token}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 400:
            print("Server-side spatial filtering failed with 400 Bad Request.")
            print("Will fall back to fetching all data and filtering locally.")
            return None
        response.raise_for_status()
        
        # If we got here, the request succeeded
        data = gpd.read_file(io.StringIO(response.text))
        print(f"Server-side spatial filter succeeded! Got {len(data)} records.")
        
        # If it worked for the first page, fetch all pages with the filter
        return fetch_all_socrata_data(base_url, limit, app_token, encoded_where_clause)
        
    except Exception as e:
        print(f"Server-side spatial filtering failed: {e}")
        print("Will fall back to fetching all data and filtering locally.")
        return None

def download_all_datasets():
    """Download all datasets and save to local files."""
    # Download Parcel Geometries
    print("\n--- Downloading Parcel Geometries ---")
    parcel_gdf = fetch_all_socrata_data(PARCEL_GEOMETRY_URL_BASE, LIMIT, APP_TOKEN)
    if parcel_gdf is not None:
        parcel_gdf.to_file(PARCEL_DATA_PATH, driver="GeoJSON")
        print(f"Saved {len(parcel_gdf)} parcel records to {PARCEL_DATA_PATH}")
    
    # Download Assessment Data
    print("\n--- Downloading Assessment Data ---")
    assessment_gdf = fetch_all_socrata_data(ASSESSMENT_DATA_URL_BASE, LIMIT, APP_TOKEN)
    if assessment_gdf is not None:
        assessment_gdf.to_file(ASSESSMENT_DATA_PATH, driver="GeoJSON")
        print(f"Saved {len(assessment_gdf)} assessment records to {ASSESSMENT_DATA_PATH}")
    
    # Download Zoning Data
    print("\n--- Downloading Zoning Data ---")
    zoning_gdf = fetch_all_socrata_data(ZONING_DATA_URL_BASE, LIMIT, APP_TOKEN)
    if zoning_gdf is not None:
        zoning_gdf.to_file(ZONING_DATA_PATH, driver="GeoJSON")
        print(f"Saved {len(zoning_gdf)} zoning records to {ZONING_DATA_PATH}")

if __name__ == "__main__":
    print("Starting data download process...")
    download_all_datasets()
    print("Download process complete.")

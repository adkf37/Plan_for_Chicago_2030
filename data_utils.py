import geopandas as gpd
import pandas as pd
import requests
import io

def fetch_all_socrata_data(base_url, limit, app_token, where_clause=None):
    """Fetches records from a Socrata endpoint (JSON or GeoJSON) using pagination and optional server-side filtering."""
    all_data = [] # Store dictionaries or GeoDataFrames
    offset = 0
    headers = {'X-App-Token': app_token}
    is_geojson = base_url.lower().endswith('.geojson')
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

            # Check for empty or no results response
            if not data_text or data_text.strip() == '[]' or data_text.strip() == '{}' or '"errorCode" : "query.soql.no-results"' in data_text:
                 print("  Received empty or no results response, assuming end of data for this query.")
                 break

            # Attempt to read the data
            try:
                if is_geojson:
                    gdf = gpd.read_file(io.StringIO(data_text))
                    if gdf.empty:
                        print("  Received empty GeoDataFrame, assuming end of data.")
                        break
                    all_data.append(gdf)
                    num_records = len(gdf)
                else: # Assume JSON
                    json_data = response.json()
                    if not isinstance(json_data, list) or not json_data:
                         print("  Received empty JSON list or non-list data, assuming end of data.")
                         break
                    all_data.extend(json_data) # Append records directly
                    num_records = len(json_data)

                print(f"  Fetched {num_records} records.")
                # If fewer records than the limit were returned, it's the last page
                if num_records < limit:
                    print("  Fetched fewer records than limit, assuming last page.")
                    break
                offset += num_records # Increment offset by the number of records actually received
            except Exception as read_error:
                 print(f"  ERROR reading data from offset {offset}: {read_error}")
                 print(f"  Response text snippet: {data_text[:200]}") # Print snippet for debugging
                 break # Stop if there's an error reading the data

        except requests.exceptions.RequestException as req_error:
            print(f"  ERROR during request for offset {offset}: {req_error}")
            break # Stop if there's a request error

    if not all_data:
        print("No data fetched.")
        return None

    print("Processing all fetched pages...")
    if is_geojson:
        # Concatenate GeoDataFrames
        full_gdf = pd.concat(all_data, ignore_index=True)
        # Ensure it's still a GeoDataFrame
        crs = all_data[0].crs if all_data and all_data[0].crs else "EPSG:4326"
        full_gdf = gpd.GeoDataFrame(full_gdf, geometry='geometry', crs=crs)
        print(f"Total records fetched: {len(full_gdf)}")
        return full_gdf
    else:
        # Convert list of dictionaries to DataFrame
        full_df = pd.DataFrame(all_data)
        print(f"Total records fetched: {len(full_df)}")
        # Attempt to convert to GeoDataFrame if geometry column exists (e.g., WKT)
        if 'geometry' in full_df.columns:
             try:
                 # Example: Convert from WKT if applicable
                 # from shapely.wkt import loads
                 # full_df['geometry'] = full_df['geometry'].apply(loads)
                 # gdf = gpd.GeoDataFrame(full_df, geometry='geometry', crs="EPSG:4326") # Assuming WGS84
                 # print("Converted fetched JSON data to GeoDataFrame.")
                 # return gdf
                 print("Note: Fetched JSON data has a 'geometry' column, but conversion to GeoDataFrame is not fully implemented here.")
                 return full_df # Return as DataFrame for now
             except Exception as geo_conv_error:
                 print(f"Could not auto-convert JSON 'geometry' column to GeoDataFrame: {geo_conv_error}")
                 return full_df # Return as DataFrame
        else:
             return full_df # Return as DataFrame

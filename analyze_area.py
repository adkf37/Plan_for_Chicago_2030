import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster # Import MarkerCluster for better point display
from shapely.geometry import Point, Polygon # Import Polygon as well
import warnings

# --- Configuration ---
ASSESSMENT_DATA_PATH = "Assessor_-_Assessed_Values_20250430.csv"
PARCEL_UNIVERSE_PATH = "Assessor_-_Parcel_Universe_20250430.csv"

# Column names in the data
PIN_COLUMN_ASSESSMENT = 'pin'
VALUE_COLUMN = 'certified_tot'
CLASS_COLUMN_ASSESSMENT = 'class' # <<< Updated to lowercase based on user feedback
PIN_COLUMN_UNIVERSE = 'pin'
# Coordinate columns in Parcel Universe CSV
LATITUDE_COLUMN = 'latitude'
LONGITUDE_COLUMN = 'longitude'
# Example attribute columns to keep
UNIVERSE_ATTRIBUTES = ['CLS_CLASS_DESCRIPTION', 'NBHD_DESC', 'BLDG_SQ_FT']

OUTPUT_MAP_FILE = 'area_value_map.html'

# --- Define Area of Interest ---
# Updated longitude boundaries: Clark St (west) to S DuSable LSD (east)
min_lon, max_lon = -87.630, -87.617
min_lat, max_lat = 41.852, 41.867    # Approx Cermak to Roosevelt (remains the same)

# Create a bounding box polygon for filtering
bbox = Polygon([(min_lon, min_lat), (min_lon, max_lat), (max_lon, max_lat), (max_lon, min_lat), (min_lon, min_lat)])
bbox_gdf = gpd.GeoDataFrame([1], geometry=[bbox], crs="EPSG:4326")
print(f"Defined Bounding Box: {bbox.bounds}")

# --- Load Data from Local Files ---

# Load Parcel Universe Data using Pandas
print(f"Loading parcel universe data from '{PARCEL_UNIVERSE_PATH}'...")
try:
    parcels_df = pd.read_csv(PARCEL_UNIVERSE_PATH)
    print(f"Loaded {len(parcels_df)} parcel universe records.")

    # Check for necessary columns
    required_cols = [PIN_COLUMN_UNIVERSE, LONGITUDE_COLUMN, LATITUDE_COLUMN]
    missing_req = [col for col in required_cols if col not in parcels_df.columns]
    if missing_req:
        print(f"ERROR: Required columns missing in {PARCEL_UNIVERSE_PATH}: {missing_req}")
        print(f"Available columns: {parcels_df.columns.tolist()}")
        exit()

    # Check for attribute columns
    missing_attrs = [col for col in UNIVERSE_ATTRIBUTES if col not in parcels_df.columns]
    if missing_attrs:
        print(f"WARNING: Assumed attribute columns not found: {missing_attrs}")
        UNIVERSE_ATTRIBUTES = [col for col in UNIVERSE_ATTRIBUTES if col in parcels_df.columns]

    # Create GeoDataFrame from longitude and latitude
    print("Creating point geometries from longitude and latitude...")
    parcels_gdf = gpd.GeoDataFrame(
        parcels_df,
        geometry=gpd.points_from_xy(parcels_df[LONGITUDE_COLUMN], parcels_df[LATITUDE_COLUMN]),
        crs="EPSG:4326"  # Assuming WGS84 for lat/lon
    )
    # Drop rows with invalid geometry if any were created (e.g., from non-numeric lat/lon)
    parcels_gdf = parcels_gdf[parcels_gdf.geometry.is_valid & ~parcels_gdf.geometry.is_empty]
    print(f"Created {len(parcels_gdf)} valid point geometries.")

except FileNotFoundError:
    print(f"ERROR: Parcel Universe data file not found at {PARCEL_UNIVERSE_PATH}")
    exit()
except Exception as e:
    print(f"ERROR loading or processing parcel universe data: {e}")
    exit()

# Load Assessment Data from CSV
print(f"Loading assessment data from '{ASSESSMENT_DATA_PATH}'...")
try:
    assessment_df = pd.read_csv(ASSESSMENT_DATA_PATH)
    print(f"Loaded {len(assessment_df)} assessment records.")
    # --- Debug: Print actual column names ---
    print(f"Columns found in assessment data: {assessment_df.columns.tolist()}")
    # --- End Debug ---
    # Check if PIN column exists
    if PIN_COLUMN_ASSESSMENT not in assessment_df.columns:
        print(f"ERROR: Assumed PIN column '{PIN_COLUMN_ASSESSMENT}' not found in {ASSESSMENT_DATA_PATH}.")
        print(f"Available columns: {assessment_df.columns.tolist()}")
        exit()
    # Check if value column exists
    if VALUE_COLUMN not in assessment_df.columns:
        print(f"ERROR: Assumed value column '{VALUE_COLUMN}' not found in {ASSESSMENT_DATA_PATH}.")
        print(f"Available columns: {assessment_df.columns.tolist()}")
        exit()
    # No need to check for class column existence here anymore

except FileNotFoundError:
    print(f"ERROR: Assessment data file not found at {ASSESSMENT_DATA_PATH}")
    exit()
except Exception as e:
    print(f"ERROR loading assessment data from {ASSESSMENT_DATA_PATH}: {e}")
    exit()


# --- Clean & Prepare Data ---
# Ensure PIN columns are string and clean
parcels_gdf[PIN_COLUMN_UNIVERSE] = parcels_gdf[PIN_COLUMN_UNIVERSE].astype(str).str.replace('-', '', regex=False)
assessment_df[PIN_COLUMN_ASSESSMENT] = assessment_df[PIN_COLUMN_ASSESSMENT].astype(str).str.replace('-', '', regex=False)

# Ensure parcel data CRS is set (already done during creation)
print(f"Parcel geometries CRS: {parcels_gdf.crs}")

# Convert value column to numeric
if VALUE_COLUMN in assessment_df.columns:
    assessment_df[VALUE_COLUMN] = pd.to_numeric(
        assessment_df[VALUE_COLUMN].astype(str).str.replace(r'[$,]', '', regex=True),
        errors='coerce'
    )
    assessment_df = assessment_df.dropna(subset=[VALUE_COLUMN])


# --- Diagnostic Print: Check PIN Formats ---
# ... (diagnostic prints remain the same) ...

# --- Merge Data ---
print("Merging assessment data onto parcel universe data...")
# Select necessary columns from assessment_df, including the class column
merge_cols = [PIN_COLUMN_ASSESSMENT, VALUE_COLUMN, CLASS_COLUMN_ASSESSMENT]
assessment_to_merge = assessment_df[merge_cols]

merged_gdf = parcels_gdf.merge(
    assessment_to_merge,
    left_on=PIN_COLUMN_UNIVERSE,
    right_on=PIN_COLUMN_ASSESSMENT,
    how='left'
)

# --- Handle Duplicate Columns ---
# Drop the class column from the left dataframe (Universe) if it exists
if f'{CLASS_COLUMN_ASSESSMENT}_x' in merged_gdf.columns:
    merged_gdf = merged_gdf.drop(columns=[f'{CLASS_COLUMN_ASSESSMENT}_x'])
    print(f"Dropped '{CLASS_COLUMN_ASSESSMENT}_x' column.")

# Rename the class column from the right dataframe (Assessment)
if f'{CLASS_COLUMN_ASSESSMENT}_y' in merged_gdf.columns:
    merged_gdf = merged_gdf.rename(columns={f'{CLASS_COLUMN_ASSESSMENT}_y': CLASS_COLUMN_ASSESSMENT})
    print(f"Renamed '{CLASS_COLUMN_ASSESSMENT}_y' to '{CLASS_COLUMN_ASSESSMENT}'.")
else:
    # This case shouldn't happen if 'class' was in assessment_to_merge, but good to check
    print(f"Warning: Expected column '{CLASS_COLUMN_ASSESSMENT}_y' not found after merge.")


# --- Debug: Show columns after handling duplicates ---
print(f"Columns after handling duplicates: {merged_gdf.columns.tolist()}")
# --- End Debug ---


# Drop the duplicate PIN column from assessment data if necessary
if PIN_COLUMN_ASSESSMENT != PIN_COLUMN_UNIVERSE and PIN_COLUMN_ASSESSMENT in merged_gdf.columns:
     merged_gdf = merged_gdf.drop(columns=[PIN_COLUMN_ASSESSMENT])

# Select final columns to keep in merged_gdf
# Now we can reliably include CLASS_COLUMN_ASSESSMENT
final_keep_cols = [PIN_COLUMN_UNIVERSE, 'geometry', VALUE_COLUMN, CLASS_COLUMN_ASSESSMENT] + UNIVERSE_ATTRIBUTES

# Filter final_keep_cols to only those actually present
final_keep_cols = [col for col in final_keep_cols if col in merged_gdf.columns]

print(f"Columns selected for final merged_gdf: {final_keep_cols}")
merged_gdf = merged_gdf[final_keep_cols]


# ... (check merge results remain the same) ...
if VALUE_COLUMN in merged_gdf.columns and merged_gdf[VALUE_COLUMN].isnull().all():
    print("WARNING: Merge completed, but no assessment values matched parcel PINs. Check PIN formats.")
elif VALUE_COLUMN not in merged_gdf.columns:
    print("WARNING: Value column not found after merge.")
else:
    print(f"Successfully merged data. Result has {len(merged_gdf)} records.")
    print(f"Columns: {merged_gdf.columns.tolist()}")


# Ensure it's still a GeoDataFrame
if 'geometry' not in merged_gdf.columns or not isinstance(merged_gdf, gpd.GeoDataFrame):
     print("ERROR: Merged data is not a GeoDataFrame or lacks geometry. Cannot proceed.")
     exit()


# --- Filter Data to Area (Local Filter) ---
print("Filtering merged parcel points within the defined area...")
# Use spatial join with 'within' or 'intersects' for points
parcels_in_area = gpd.sjoin(merged_gdf, bbox_gdf, how="inner", predicate="within") # 'within' is appropriate for points in polygon

if len(parcels_in_area) == 0:
    print("No parcel points found within the specified area after merging and filtering.")
    exit()
else:
    print(f"Found {len(parcels_in_area)} parcel points within the area.")

# --- Calculate Aggregate Value ---
# ... (calculation remains the same) ...
total_value = parcels_in_area[VALUE_COLUMN].sum()
print(f"\nAggregate {VALUE_COLUMN} in the area: ${total_value:,.2f}")


# --- Export Filtered Data to CSV ---
print(f"Exporting {len(parcels_in_area)} filtered parcel points to CSV...")

# Prepare data for export
export_df = parcels_in_area.copy()

# Convert geometry to WKT *before* selecting columns for final output df
export_df['geometry_wkt'] = export_df['geometry'].apply(lambda geom: geom.wkt if geom else None)

# Define columns to export and the rename map
# Include CLASS_COLUMN_ASSESSMENT directly now
export_columns = [PIN_COLUMN_UNIVERSE, 'geometry_wkt', VALUE_COLUMN, CLASS_COLUMN_ASSESSMENT]
rename_map = {
    PIN_COLUMN_UNIVERSE: 'pin',
    'geometry_wkt': 'geometry', # Rename the WKT column back to 'geometry'
    VALUE_COLUMN: 'certified_tot',
    CLASS_COLUMN_ASSESSMENT: 'class' # Rename to lowercase 'class'
}

# Filter export_columns to only those present in export_df (handles missing UNIVERSE_ATTRIBUTES if they were kept)
export_columns = [col for col in export_columns if col in export_df.columns]

# Select only the columns we want for the final CSV
output_df = export_df[export_columns]

# Rename the columns
output_df.rename(columns=rename_map, inplace=True)

# Define output filename
output_csv_file = 'parcels_in_area.csv'

try:
    output_df.to_csv(output_csv_file, index=False)
    print(f"Filtered data saved to '{output_csv_file}'")
except Exception as e:
    print(f"ERROR saving CSV file: {e}")

# --- Create Value Map (Using CircleMarkers for Points) ---
print("Generating value map with points...")

map_center = [bbox.centroid.y, bbox.centroid.x]
m = folium.Map(location=map_center, zoom_start=15, tiles='CartoDB positron')

# Add the bounding box outline
folium.GeoJson(
    bbox_gdf.__geo_interface__,
    name='Area Boundary',
    style_function=lambda feature: {'color': 'red', 'weight': 3, 'fillOpacity': 0}
).add_to(m)


# Add points to the map, potentially colored by value
parcels_in_area = parcels_in_area.dropna(subset=[VALUE_COLUMN, 'geometry'])

if not parcels_in_area.empty:
    # Create a simple color scale (e.g., based on quantiles) - requires numpy
    try:
        import numpy as np
        # Example: Color based on 5 quantiles
        parcels_in_area['value_quantile'] = pd.qcut(parcels_in_area[VALUE_COLUMN], 5, labels=False, duplicates='drop')
        colors = ['#ffffcc','#c7e9b4','#7fcdbb','#41b6c4','#2c7fb8'] # Example YlGnBu-5

        def get_color(quantile):
            # Handle potential NaN quantiles if qcut fails for some reason
            if pd.isna(quantile):
                return '#808080' # Grey for missing quantile
            return colors[int(quantile)]

    except ImportError:
        print("Numpy not found, using single color for points.")
        parcels_in_area['value_quantile'] = 0 # Assign dummy value
        def get_color(quantile): return '#41b6c4' # Default blue

    # Add points using CircleMarker
    points_layer = folium.FeatureGroup(name="Parcel Values (Points)")
    for idx, row in parcels_in_area.iterrows():
        # Prepare tooltip text
        tooltip_text = f"PIN: {row[PIN_COLUMN_UNIVERSE]}<br>Value: ${row[VALUE_COLUMN]:,.0f}"
        for attr in UNIVERSE_ATTRIBUTES:
             if attr in row and pd.notna(row[attr]):
                  tooltip_text += f"<br>{attr.replace('_', ' ').title()}: {row[attr]}"

        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=3, # Adjust radius as needed
            color=get_color(row['value_quantile']),
            fill=True,
            fill_color=get_color(row['value_quantile']),
            fill_opacity=0.7,
            tooltip=tooltip_text
        ).add_to(points_layer)
    points_layer.add_to(m)

    # Optional: Add a simple legend (requires branca for complex legends)
    # This is a basic text legend; for a real color scale legend, use branca
    # Use an f-string to correctly embed the color values
    legend_html = f'''
     <div style="position: fixed;
     bottom: 50px; left: 50px; width: 150px; height: 90px;
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color: white; opacity: 0.8;
     ">&nbsp;<b>Value Quantile</b><br>
     &nbsp;<i class="fa fa-circle" style="color:{colors[0]}"></i>&nbsp; Lowest<br>
     &nbsp;...<br>
     &nbsp;<i class="fa fa-circle" style="color:{colors[-1]}"></i>&nbsp; Highest
      </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))


folium.LayerControl().add_to(m)

# Save map
m.save(OUTPUT_MAP_FILE)
print(f"Value map saved to '{OUTPUT_MAP_FILE}'")

import osmnx as ox
import geopandas as gpd
import folium
from folium.plugins import Draw
import pandas as pd # Added for potential CSV reading

# --- Configuration ---
PARCEL_DATA_PATH = "parcel_data.geojson"  # Local Cook County parcel GeoJSON
CENSUS_TRACT_DATA_PATH = "census_tracts.geojson"  # Local census tract GeoJSON
ZONING_DATA_PATH = "zoning_data.geojson"          # Local Chicago zoning GeoJSON
ASSESSMENT_DATA_PATH = "assessment_data.geojson"   # Local assessment GeoJSON
# GTFS_PATH = "path/to/your/cta_gtfs_data" # Folder containing GTFS .txt files

# 1. Define the city of interest
city = "Chicago, Illinois, USA"

# 2. Fetch Chicago’s boundary (city limits)
print("Fetching city boundary for Chicago...")
chicago_gdf = ox.geocode_to_gdf(city)
chicago_polygon = chicago_gdf.geometry.iloc[0]

# 3. Retrieve the street network (for driving)
print("Fetching street network for Chicago...")
G = ox.graph_from_place(city, network_type='drive')
roads = ox.graph_to_gdfs(G, nodes=False)

# 4. Retrieve building footprints using OSM tags (Keep commented out for now)
#print("Fetching building footprints for Chicago...")
#tags = {"building": True}
#buildings = ox.features_from_polygon(chicago_polygon, tags=tags)

# --- Load Local Datasets ---

# 4a. Load Parcel Data
print(f"Loading Parcel data from '{PARCEL_DATA_PATH}'...")
try:
    parcels = gpd.read_file(PARCEL_DATA_PATH)
    # Optional: Reproject to WGS84 (EPSG:4326) if not already, Folium prefers this
    parcels = parcels.to_crs(epsg=4326)
    print("Parcel data loaded.")
except Exception as e:
    print(f"Error loading Parcel data: {e}")
    parcels = None

# 4b. Load Zoning Data
print(f"Loading Zoning data from '{ZONING_DATA_PATH}'...")
try:
    zoning = gpd.read_file(ZONING_DATA_PATH)
    zoning = zoning.to_crs(epsg=4326)
    print("Zoning data loaded.")
except Exception as e:
    print(f"Error loading Zoning data: {e}")
    zoning = None

# 4c. Load Census Tract Data
print(f"Loading Census Tract data from {CENSUS_TRACT_DATA_PATH}...")
try:
    tracts = gpd.read_file(CENSUS_TRACT_DATA_PATH)
    tracts = tracts.to_crs(epsg=4326)
    print("Census Tract data loaded.")
except Exception as e:
    print(f"Error loading Census Tract data: {e}")
    tracts = None

# 4d. Load Assessment Data (Example - Non-spatial, might be joined later)
print(f"Loading Assessment data from '{ASSESSMENT_DATA_PATH}'...")
try:
    assessment_df = gpd.read_file(ASSESSMENT_DATA_PATH)
    print("Assessment data loaded.")
    # This data would typically be joined to parcels based on a common ID (e.g., PIN)
    # in the analysis scripts (property_value.py), not directly added to the map unless spatialized.
except Exception as e:
    print(f"Error loading Assessment data: {e}")
    assessment_df = None

# 4e. Load GTFS Stops (Example - basic stop locations)
# print(f"Loading GTFS stops from {GTFS_PATH}...")
# try:
#     stops_df = pd.read_csv(os.path.join(GTFS_PATH, 'stops.txt'))
#     # Convert stops DataFrame to GeoDataFrame
#     stops_gdf = gpd.GeoDataFrame(
#         stops_df, geometry=gpd.points_from_xy(stops_df.stop_lon, stops_df.stop_lat), crs="EPSG:4326"
#     )
#     print("GTFS stops loaded and converted to GeoDataFrame.")
# except Exception as e:
#     print(f"Error loading GTFS stops: {e}")
#     stops_gdf = None


# 5. Compute the center of Chicago for initial map positioning
chicago_center = [chicago_polygon.centroid.y, chicago_polygon.centroid.x]

# 6. Create a Folium map with a detailed base layer
#    Using CartoDB Positron tiles for a clear street grid and building context
m = folium.Map(location=chicago_center, zoom_start=11, tiles='CartoDB positron')

# 7. Add Chicago's boundary as an overlay
folium.GeoJson(
    chicago_gdf.__geo_interface__,
    name='Chicago Boundary',
    style_function=lambda feature: {'color': 'green', 'weight': 2, 'fillOpacity': 0}
).add_to(m)

# 8. Add the road network layer
folium.GeoJson(
    roads.__geo_interface__,
    name='Roads',
    style_function=lambda feature: {'color': 'red', 'weight': 1}
).add_to(m)

# 8a. Add Parcel Layer (Optional - Can be very slow for large datasets)
if parcels is not None:
    # Warning: Adding large parcel datasets directly can make the map very slow.
    # Consider simplification or using vector tiles for production.
    print("Adding Parcel layer to map (may be slow)...")
    folium.GeoJson(
        parcels.iloc[:1000], # Limit to first 1000 for performance in this example
        name='Parcels (Sample)',
        style_function=lambda feature: {'color': 'purple', 'weight': 0.5, 'fillOpacity': 0.1},
        tooltip=folium.features.GeoJsonTooltip(fields=['PIN'], aliases=['Parcel ID:']) # Adjust field name ('PIN') as needed
    ).add_to(m)

# 8b. Add Zoning Layer
if zoning is not None:
    print("Adding Zoning layer to map...")
    folium.GeoJson(
        zoning,
        name='Zoning Districts',
        style_function=lambda feature: {
            'fillColor': 'orange', # Placeholder: Ideally, color based on zoning type
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.4
        },
        tooltip=folium.features.GeoJsonTooltip(fields=['zone_class'], aliases=['Zoning:']) # Adjust field name ('zone_class') as needed
    ).add_to(m)

# 8c. Add Census Tract Layer
if tracts is not None:
    print("Adding Census Tract layer to map...")
    folium.GeoJson(
        tracts,
        name='Census Tracts',
        style_function=lambda feature: {'color': 'blue', 'weight': 1.5, 'fillOpacity': 0.1},
        tooltip=folium.features.GeoJsonTooltip(fields=['GEOID'], aliases=['Tract ID:']) # Adjust field name ('GEOID') as needed
    ).add_to(m)

# 8d. Add GTFS Stops Layer (Example)
# if stops_gdf is not None:
#     print("Adding GTFS Stops layer to map...")
#     # Use MarkerCluster for performance if many stops
#     from folium.plugins import MarkerCluster
#     marker_cluster = MarkerCluster(name='Transit Stops').add_to(m)
#     for idx, row in stops_gdf.iterrows():
#         folium.Marker(
#             location=[row.geometry.y, row.geometry.x],
#             popup=f"Stop: {row['stop_name']}", # Adjust field name as needed
#             icon=folium.Icon(color='green', icon='bus', prefix='fa') # Example icon
#         ).add_to(marker_cluster)


# 9. Add the building footprints layer (Keep commented out)
#folium.GeoJson(
#    buildings.__geo_interface__,
#    name='Buildings',
#    style_function=lambda feature: {
#        'color': 'blue',
#        'weight': 0.5,
#        'fillColor': 'blue',
#        'fillOpacity': 0.5
#    }
#).add_to(m)

# 10. Add interactive drawing tools (Leaflet.Draw plugin)
draw = Draw(
    export=True,  # Enable export of edited features as GeoJSON
    filename='edited_data.geojson',
    draw_options={
        'polyline': True,
        'polygon': True,
        'circle': False,     # Disable circle drawing
        'rectangle': True,
        'marker': True,
        'circlemarker': False
    },
    edit_options={'edit': True, 'remove': True}
)
draw.add_to(m)

# 11. Add a layer control panel to toggle overlays
folium.LayerControl().add_to(m)

# 12. Save the interactive map to an HTML file
m.save('chicago_interactive_map.html')
print("Interactive map saved as 'chicago_interactive_map.html'")

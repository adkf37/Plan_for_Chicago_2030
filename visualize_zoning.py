import geopandas as gpd
import pandas as pd
import folium
from folium import GeoJson
import json

# --- Configuration ---
ZONING_GEOJSON_PATH = "chicago_zoning_2025.geojson"
ZONING_CODES_CSV = "zoning_codes.csv"
OUTPUT_MAP_FILE = "chicago_zoning_map.html"

# Color scheme inspired by Second City Zoning / SimCity 2000
# Maps ZONE_TYPE values to colors
ZONE_TYPE_COLORS = {
    1: '#0000ff',    # Business (Blue)
    2: '#0000ff',    # Commercial/Mixed-Use (Blue)
    3: '#ffff00',    # Manufacturing (Yellow)
    4: '#00ff00',    # Residential (Green)
    5: '#ff0000',    # Planned Development (Red)
    6: '#ffff00',    # Planned Manufacturing District (Yellow)
    7: '#0000ff',    # Downtown Mixed-Use (Blue)
    8: '#0000ff',    # Downtown Core (Blue)
    9: '#00ff00',    # Downtown Residential (Green)
    10: '#0000ff',   # Downtown Service (Blue)
    11: '#666666',   # Transportation (Gray)
    12: '#38761d',   # Parks and Open Space (Dark Green)
}

ZONE_TYPE_NAMES = {
    1: "Business",
    2: "Commercial / Mixed-Use",
    3: "Manufacturing",
    4: "Residential",
    5: "Planned Development",
    6: "Planned Manufacturing District",
    7: "Downtown Mixed-Use",
    8: "Downtown Core",
    9: "Downtown Residential",
    10: "Downtown Service",
    11: "Transportation",
    12: "Parks and Open Space",
}

print(f"Loading zoning data from '{ZONING_GEOJSON_PATH}'...")
try:
    zoning_gdf = gpd.read_file(ZONING_GEOJSON_PATH)
    zoning_gdf = zoning_gdf.to_crs(epsg=4326)  # Ensure WGS84
    print(f"Loaded {len(zoning_gdf)} zoning parcels.")
    print(f"Columns: {zoning_gdf.columns.tolist()}")
except Exception as e:
    print(f"ERROR loading zoning data: {e}")
    exit()

# Load zoning codes metadata
print(f"\nLoading zoning code descriptions from '{ZONING_CODES_CSV}'...")
try:
    zoning_codes_df = pd.read_csv(ZONING_CODES_CSV)
    print(f"Loaded {len(zoning_codes_df)} zoning code definitions.")
    
    # Create lookup dictionary
    zoning_lookup = {}
    for idx, row in zoning_codes_df.iterrows():
        zoning_lookup[row['district_type_code']] = {
            'title': row['district_title'],
            'description': row['juan_description'],
            'far': row['floor_area_ratio'],
            'max_height': row['maximum_building_height'],
            'zone_type': row['zone_type']
        }
except Exception as e:
    print(f"WARNING: Could not load zoning codes CSV: {e}")
    zoning_lookup = {}

# Enrich zoning geodataframe with metadata
def get_zone_info(zone_class):
    """Get detailed information about a zone class"""
    if zone_class in zoning_lookup:
        return zoning_lookup[zone_class]
    return {
        'title': 'Unknown',
        'description': f'Zone class: {zone_class}',
        'far': 'N/A',
        'max_height': 'N/A',
        'zone_type': None
    }

# Add enriched data columns
print("\nEnriching zoning data with descriptions...")
zoning_gdf['zone_name'] = zoning_gdf['ZONE_CLASS'].apply(
    lambda x: get_zone_info(x)['title']
)
zoning_gdf['zone_description'] = zoning_gdf['ZONE_CLASS'].apply(
    lambda x: get_zone_info(x)['description']
)
zoning_gdf['far'] = zoning_gdf['ZONE_CLASS'].apply(
    lambda x: get_zone_info(x)['far']
)

# Calculate center of Chicago for map
print("\nCalculating map center...")
chicago_center = [zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean()]
print(f"Map center: {chicago_center}")

# Create Folium map
print("\nCreating interactive map...")
m = folium.Map(
    location=chicago_center,
    zoom_start=11,
    tiles='CartoDB positron'
)

# Style function for zoning polygons
def style_function(feature):
    zone_type = feature['properties'].get('ZONE_TYPE', 0)
    zone_class = feature['properties'].get('ZONE_CLASS', '')
    
    # Get color based on zone type
    color = ZONE_TYPE_COLORS.get(zone_type, '#808080')
    
    # Adjust opacity based on zone class (density indicator)
    # Higher density zones (with numbers) get higher opacity
    opacity = 0.35
    if '-' in str(zone_class):
        try:
            parts = str(zone_class).split('-')
            if len(parts) > 1 and parts[1].replace('.', '').isdigit():
                density = float(parts[1])
                # Scale opacity from 0.15 to 0.65
                opacity = min(0.15 + (density / 20.0), 0.65)
        except:
            pass
    
    return {
        'fillColor': color,
        'color': '#000000',
        'weight': 0.5,
        'fillOpacity': opacity
    }

# Highlight function
def highlight_function(feature):
    return {
        'fillColor': '#ffff00',
        'color': '#000000',
        'weight': 2,
        'fillOpacity': 0.7
    }

# Create tooltip and popup content
def create_popup_html(feature):
    props = feature['properties']
    zone_class = props.get('ZONE_CLASS', 'Unknown')
    zone_type_num = props.get('ZONE_TYPE', 0)
    zone_type_name = ZONE_TYPE_NAMES.get(zone_type_num, 'Unknown')
    
    zone_info = get_zone_info(zone_class)
    
    html = f"""
    <div style="font-family: Arial; font-size: 12px; width: 300px;">
        <h4 style="margin: 0 0 10px 0; color: #2c3e50;">{zone_class}</h4>
        <p style="margin: 5px 0;"><strong>District:</strong> {zone_info['title']}</p>
        <p style="margin: 5px 0;"><strong>Type:</strong> {zone_type_name}</p>
        <p style="margin: 5px 0;"><strong>Description:</strong> {zone_info['description']}</p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0;"><strong>Floor Area Ratio:</strong> {zone_info['far']}</p>
        <p style="margin: 5px 0;"><strong>Max Height:</strong> {zone_info['max_height']}</p>
        <p style="margin: 5px 0; font-size: 10px; color: #7f8c8d;">
            <strong>Ordinance:</strong> {props.get('ORDINANCE_NUM', 'N/A')}
        </p>
    </div>
    """
    return html

# Add zoning layer to map
print("Adding zoning layer to map...")
zoning_layer = GeoJson(
    zoning_gdf,
    name='Chicago Zoning',
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=['ZONE_CLASS', 'zone_name'],
        aliases=['Zone:', 'District:'],
        style='background-color: white; color: #333333; font-family: Arial; font-size: 12px; padding: 10px;'
    ),
    popup=folium.GeoJsonPopup(
        fields=['ZONE_CLASS', 'zone_name', 'zone_description', 'far'],
        aliases=['Zone Code:', 'District:', 'Description:', 'FAR:'],
        style='background-color: white;'
    )
)
zoning_layer.add_to(m)

# Add legend
print("Adding legend...")
legend_html = f'''
<div style="position: fixed; 
     bottom: 50px; right: 50px; width: 200px; 
     border:2px solid grey; z-index:9999; font-size:12px;
     background-color: white; opacity: 0.95;
     padding: 10px;
     ">
     <p style="margin: 0 0 10px 0; font-weight: bold;">Chicago Zoning Types</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[4]}"></i>&nbsp; Residential</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[1]}"></i>&nbsp; Business/Commercial</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[3]}"></i>&nbsp; Manufacturing</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[5]}"></i>&nbsp; Planned Development</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[12]}"></i>&nbsp; Parks</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[11]}"></i>&nbsp; Transportation</p>
     <hr style="margin: 10px 0;">
     <p style="margin: 3px 0; font-size: 10px; font-style: italic;">
     Opacity indicates density (FAR)<br>
     Click zones for details
     </p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add layer control
folium.LayerControl().add_to(m)

# Save map
print(f"\nSaving map to '{OUTPUT_MAP_FILE}'...")
m.save(OUTPUT_MAP_FILE)
print(f"Map saved successfully!")

# Print summary statistics
print("\n=== Zoning Summary Statistics ===")
print(f"Total parcels: {len(zoning_gdf):,}")
print(f"\nZoning by Type:")
for zone_type, name in sorted(ZONE_TYPE_NAMES.items()):
    count = len(zoning_gdf[zoning_gdf['ZONE_TYPE'] == zone_type])
    pct = (count / len(zoning_gdf)) * 100
    print(f"  {name}: {count:,} parcels ({pct:.1f}%)")

print(f"\nTop 10 Most Common Zone Classes:")
top_zones = zoning_gdf['ZONE_CLASS'].value_counts().head(10)
for zone, count in top_zones.items():
    pct = (count / len(zoning_gdf)) * 100
    zone_info = get_zone_info(zone)
    print(f"  {zone} ({zone_info['title']}): {count:,} parcels ({pct:.1f}%)")

print(f"\nDone! Open '{OUTPUT_MAP_FILE}' in a web browser to explore Chicago's zoning.")

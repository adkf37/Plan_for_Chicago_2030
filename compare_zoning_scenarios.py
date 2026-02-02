import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
import numpy as np

# --- Configuration ---
ZONING_GEOJSON_PATH = "chicago_zoning_2025.geojson"
ZONING_CODES_CSV = "zoning_codes.csv"
OUTPUT_COMPARISON_MAP = "zoning_comparison_map.html"

# Define upzoning scenarios - Rules for transforming current zoning to proposed
UPZONING_SCENARIOS = {
    "transit_oriented": {
        "description": "Upzone residential areas within 0.5 miles of rail stations",
        "rules": [
            # RS (Single Family) -> RT-4 (Townhouse/Low-Rise)
            {"from_prefix": "RS", "to_zone": "RT-4", "condition": "near_transit"},
            # RT-3.5 and RT-4 -> RM-5 (Mid-density apartments)
            {"from_zones": ["RT-3.5", "RT-4"], "to_zone": "RM-5", "condition": "near_transit"},
            # RM-4.5 and RM-5 -> RM-6 (High-rise)
            {"from_zones": ["RM-4.5", "RM-5"], "to_zone": "RM-6", "condition": "near_transit"},
        ]
    },
    "corridor_densification": {
        "description": "Upzone along major commercial corridors",
        "rules": [
            # B1 -> B2 (allow ground floor residential)
            {"from_prefix": "B1", "to_zone_transform": lambda z: z.replace("B1", "B2")},
            # B2 -> B3 (allow more business types)
            {"from_prefix": "B2", "to_zone_transform": lambda z: z.replace("B2", "B3")},
            # Increase FAR on commercial corridors
            {"from_prefix": "C1", "to_zone_transform": lambda z: increase_far(z)},
        ]
    }
}

def increase_far(zone_code):
    """Increase the FAR number in a zone code (e.g., C1-2 -> C1-3)"""
    if '-' in zone_code:
        parts = zone_code.split('-')
        if len(parts) == 2:
            try:
                current_far = float(parts[1])
                new_far = min(current_far + 1, 5)  # Cap at 5
                return f"{parts[0]}-{int(new_far) if new_far == int(new_far) else new_far}"
            except ValueError:
                pass
    return zone_code

print(f"Loading zoning data from '{ZONING_GEOJSON_PATH}'...")
zoning_gdf = gpd.read_file(ZONING_GEOJSON_PATH)
zoning_gdf = zoning_gdf.to_crs(epsg=4326)
print(f"Loaded {len(zoning_gdf)} zoning parcels.")

# Load zoning codes for FAR and density information
print(f"\nLoading zoning code information from '{ZONING_CODES_CSV}'...")
zoning_codes_df = pd.read_csv(ZONING_CODES_CSV)

# Create FAR lookup
far_lookup = {}
for idx, row in zoning_codes_df.iterrows():
    try:
        far_value = float(row['floor_area_ratio'])
        far_lookup[row['district_type_code']] = far_value
    except:
        far_lookup[row['district_type_code']] = 0

def get_far(zone_class):
    """Get FAR for a zone class"""
    return far_lookup.get(zone_class, 0)

# Add current FAR to geodataframe
zoning_gdf['current_far'] = zoning_gdf['ZONE_CLASS'].apply(get_far)

print("\n=== Current Zoning Statistics ===")
print(f"Total FAR capacity (sum): {zoning_gdf['current_far'].sum():,.0f}")
print(f"Average FAR: {zoning_gdf['current_far'].mean():.2f}")
print(f"Median FAR: {zoning_gdf['current_far'].median():.2f}")

# Apply simple upzoning scenario: Upzone all RS-3 to RT-4
print("\n=== Applying Simple Upzoning Scenario ===")
print("Scenario: Upzone all RS-3 (Single Family) to RT-4 (Townhouse/Low-Rise)")

zoning_gdf['proposed_zone'] = zoning_gdf['ZONE_CLASS'].copy()

# Count RS-3 zones
rs3_count = len(zoning_gdf[zoning_gdf['ZONE_CLASS'] == 'RS-3'])
print(f"Found {rs3_count:,} RS-3 parcels to upzone")

# Apply transformation
zoning_gdf.loc[zoning_gdf['ZONE_CLASS'] == 'RS-3', 'proposed_zone'] = 'RT-4'

# Add proposed FAR
zoning_gdf['proposed_far'] = zoning_gdf['proposed_zone'].apply(get_far)

# Calculate change
zoning_gdf['far_change'] = zoning_gdf['proposed_far'] - zoning_gdf['current_far']
zoning_gdf['far_pct_change'] = ((zoning_gdf['proposed_far'] - zoning_gdf['current_far']) / 
                                 zoning_gdf['current_far'].replace(0, np.nan)) * 100

print("\n=== Proposed Zoning Statistics ===")
print(f"Total FAR capacity (sum): {zoning_gdf['proposed_far'].sum():,.0f}")
print(f"Average FAR: {zoning_gdf['proposed_far'].mean():.2f}")
print(f"Median FAR: {zoning_gdf['proposed_far'].median():.2f}")

print("\n=== Impact Analysis ===")
far_increase = zoning_gdf['proposed_far'].sum() - zoning_gdf['current_far'].sum()
far_pct_increase = (far_increase / zoning_gdf['current_far'].sum()) * 100
print(f"Total FAR increase: {far_increase:,.0f} ({far_pct_increase:.1f}%)")

changed_parcels = len(zoning_gdf[zoning_gdf['ZONE_CLASS'] != zoning_gdf['proposed_zone']])
pct_changed = (changed_parcels / len(zoning_gdf)) * 100
print(f"Parcels changed: {changed_parcels:,} ({pct_changed:.1f}%)")

# Create comparison map
print("\n=== Creating Comparison Map ===")
chicago_center = [zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean()]

m = folium.Map(
    location=chicago_center,
    zoom_start=11,
    tiles='CartoDB positron'
)

# Style function - show changed zones in red, unchanged in gray
def style_function(feature):
    current = feature['properties'].get('ZONE_CLASS', '')
    proposed = feature['properties'].get('proposed_zone', '')
    
    if current != proposed:
        # Changed zones in red with varying opacity based on FAR increase
        far_change = feature['properties'].get('far_change', 0)
        opacity = min(0.3 + (far_change * 0.3), 0.8)
        return {
            'fillColor': '#ff4444',
            'color': '#cc0000',
            'weight': 1,
            'fillOpacity': opacity
        }
    else:
        # Unchanged zones in subtle gray
        return {
            'fillColor': '#cccccc',
            'color': '#999999',
            'weight': 0.3,
            'fillOpacity': 0.1
        }

# Add layer showing changes
changed_zones = zoning_gdf[zoning_gdf['ZONE_CLASS'] != zoning_gdf['proposed_zone']].copy()

if len(changed_zones) > 0:
    print(f"Adding {len(changed_zones):,} changed zones to map...")
    
    folium.GeoJson(
        changed_zones,
        name='Upzoned Areas',
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['ZONE_CLASS', 'proposed_zone', 'far_change'],
            aliases=['Current Zone:', 'Proposed Zone:', 'FAR Increase:'],
            style='background-color: white; color: #333333; font-family: Arial; font-size: 12px; padding: 10px;'
        ),
        popup=folium.GeoJsonPopup(
            fields=['ZONE_CLASS', 'proposed_zone', 'current_far', 'proposed_far', 'far_change'],
            aliases=['Current:', 'Proposed:', 'Current FAR:', 'Proposed FAR:', 'FAR Change:'],
        )
    ).add_to(m)

# Add legend
legend_html = f'''
<div style="position: fixed; 
     top: 80px; right: 50px; width: 250px; 
     border:2px solid grey; z-index:9999; font-size:12px;
     background-color: white; opacity: 0.95;
     padding: 15px;
     ">
     <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 14px;">Zoning Scenario: RS-3 → RT-4</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#ff4444"></i>&nbsp; Upzoned Areas</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#cccccc"></i>&nbsp; Unchanged</p>
     <hr style="margin: 10px 0;">
     <p style="margin: 5px 0; font-size: 11px;">
     <strong>Impact Summary:</strong><br>
     • {changed_parcels:,} parcels upzoned ({pct_changed:.1f}%)<br>
     • FAR increase: {far_increase:,.0f} ({far_pct_increase:.1f}%)<br>
     • From: RS-3 (Single Family)<br>
     • To: RT-4 (Townhouse/Low-Rise)
     </p>
     <hr style="margin: 10px 0;">
     <p style="margin: 3px 0; font-size: 10px; font-style: italic;">
     Opacity shows magnitude of FAR increase<br>
     Click zones for details
     </p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Add layer control
folium.LayerControl().add_to(m)

# Save map
print(f"\nSaving comparison map to '{OUTPUT_COMPARISON_MAP}'...")
m.save(OUTPUT_COMPARISON_MAP)
print(f"Comparison map saved!")

# Export changed zones to CSV for analysis
output_csv = "upzoning_scenario_changes.csv"
print(f"\nExporting changed zones to '{output_csv}'...")
changed_zones_export = changed_zones[['ZONE_CLASS', 'proposed_zone', 'current_far', 'proposed_far', 'far_change', 'far_pct_change']].copy()
changed_zones_export['geometry_wkt'] = changed_zones.geometry.apply(lambda g: g.wkt)
changed_zones_export.to_csv(output_csv, index=False)
print(f"Exported {len(changed_zones_export):,} changed parcels")

print(f"\n✓ Done! Open '{OUTPUT_COMPARISON_MAP}' to explore the upzoning scenario.")
print(f"✓ Analysis data saved to '{output_csv}'")

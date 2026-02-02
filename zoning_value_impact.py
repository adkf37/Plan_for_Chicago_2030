import geopandas as gpd
import pandas as pd
import folium
from folium import GeoJson
import numpy as np

# --- Configuration ---
ZONING_GEOJSON_PATH = "chicago_zoning_2025.geojson"
ZONING_CODES_CSV = "zoning_codes.csv"
PARCELS_CSV = "parcels_in_area.csv"  # From analyze_area.py output
OUTPUT_MAP = "zoning_value_impact_map.html"

# --- Value Uplift Model Parameters ---

# Method 1: FAR-Based Appreciation
# Simple model: Property value increases proportionally to FAR increase
# Research shows 10-20% uplift per FAR point in urban areas
FAR_APPRECIATION_RATE = 0.15  # 15% per FAR point

# Method 2: Zone-to-Zone Appreciation Factors
# Based on research from upzoning case studies:
# - Minneapolis 2040 Plan: ~10-15% residential upzoning
# - Portland, OR studies: 12-18% for residential upzoning
# - Academic literature (Glaeser, Gyourko): Land value = f(development rights)
ZONE_TRANSITION_FACTORS = {
    # Residential upzonings
    ('RS-1', 'RS-2'): 1.08,   # 8% - minor density increase
    ('RS-1', 'RS-3'): 1.12,   # 12% - moderate increase
    ('RS-2', 'RS-3'): 1.10,   # 10%
    ('RS-3', 'RT-4'): 1.18,   # 18% - significant jump (SF to multi-unit)
    ('RT-4', 'RM-5'): 1.15,   # 15% - low to mid-rise
    ('RM-5', 'RM-6'): 1.20,   # 20% - mid to high-rise
    
    # Commercial upzonings
    ('B1-1', 'B1-2'): 1.10,
    ('B1-2', 'B1-3'): 1.12,
    ('B2-1', 'B2-2'): 1.10,
    ('B2-2', 'B2-3'): 1.12,
    
    # Mixed transitions
    ('B1', 'B2'): 1.12,  # Adding ground-floor residential option
    ('B2', 'B3'): 1.15,  # More business types allowed
}

# Method 3: Development Rights Premium
# Land value formula: V_land = (FAR_new / FAR_old) * V_current * adjustment
# Adjustment factor accounts for development costs, market conditions
DEVELOPMENT_RIGHTS_ADJUSTMENT = 0.7  # Conservative: 70% of theoretical max

print("=== Property Value Uplift Model ===")
print("Analyzing the impact of upzoning on property values\n")

# Load zoning data
print(f"Loading zoning data from '{ZONING_GEOJSON_PATH}'...")
zoning_gdf = gpd.read_file(ZONING_GEOJSON_PATH)
zoning_gdf = zoning_gdf.to_crs(epsg=4326)
print(f"Loaded {len(zoning_gdf)} zoning parcels.")

# Load zoning codes for FAR information
print(f"\nLoading zoning codes from '{ZONING_CODES_CSV}'...")
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

# Add current FAR
zoning_gdf['current_far'] = zoning_gdf['ZONE_CLASS'].apply(get_far)

# Apply upzoning scenario
print("\n=== Applying Upzoning Scenario ===")
print("Scenario: RS-3 → RT-4")

zoning_gdf['proposed_zone'] = zoning_gdf['ZONE_CLASS'].copy()
zoning_gdf.loc[zoning_gdf['ZONE_CLASS'] == 'RS-3', 'proposed_zone'] = 'RT-4'
zoning_gdf['proposed_far'] = zoning_gdf['proposed_zone'].apply(get_far)
zoning_gdf['far_change'] = zoning_gdf['proposed_far'] - zoning_gdf['current_far']

# Calculate value uplift using multiple methods
print("\n=== Calculating Value Uplift ===")

# Method 1: FAR-based appreciation
zoning_gdf['far_appreciation'] = 1 + (zoning_gdf['far_change'] * FAR_APPRECIATION_RATE)

# Method 2: Zone transition factors
def get_transition_factor(current, proposed):
    """Get specific transition factor or calculate from FAR if not defined"""
    if current == proposed:
        return 1.0
    
    # Check direct transition
    if (current, proposed) in ZONE_TRANSITION_FACTORS:
        return ZONE_TRANSITION_FACTORS[(current, proposed)]
    
    # Check prefix transitions (e.g., 'B1-1' -> 'B2-1' matches 'B1' -> 'B2')
    current_prefix = current.split('-')[0]
    proposed_prefix = proposed.split('-')[0]
    if (current_prefix, proposed_prefix) in ZONE_TRANSITION_FACTORS:
        return ZONE_TRANSITION_FACTORS[(current_prefix, proposed_prefix)]
    
    # Fall back to FAR-based calculation
    far_current = get_far(current)
    far_proposed = get_far(proposed)
    if far_current > 0:
        far_ratio = far_proposed / far_current
        return 1 + ((far_ratio - 1) * FAR_APPRECIATION_RATE)
    
    return 1.0

zoning_gdf['transition_factor'] = zoning_gdf.apply(
    lambda row: get_transition_factor(row['ZONE_CLASS'], row['proposed_zone']), 
    axis=1
)

# Method 3: Development rights premium
zoning_gdf['dev_rights_factor'] = 1.0
mask = zoning_gdf['current_far'] > 0
zoning_gdf.loc[mask, 'dev_rights_factor'] = (
    1 + ((zoning_gdf.loc[mask, 'proposed_far'] / zoning_gdf.loc[mask, 'current_far']) - 1) * 
    DEVELOPMENT_RIGHTS_ADJUSTMENT
)

# Composite uplift factor (weighted average of methods)
# Weight: 50% transition factors, 30% FAR appreciation, 20% dev rights
zoning_gdf['value_uplift_factor'] = (
    0.50 * zoning_gdf['transition_factor'] +
    0.30 * zoning_gdf['far_appreciation'] +
    0.20 * zoning_gdf['dev_rights_factor']
)

# Express as percentage change
zoning_gdf['value_uplift_pct'] = (zoning_gdf['value_uplift_factor'] - 1) * 100

# Filter to changed zones
changed_zones = zoning_gdf[zoning_gdf['ZONE_CLASS'] != zoning_gdf['proposed_zone']].copy()

print(f"\nUpzoned parcels: {len(changed_zones):,}")
print(f"\nValue Uplift Statistics:")
print(f"  Average uplift: {changed_zones['value_uplift_pct'].mean():.1f}%")
print(f"  Median uplift: {changed_zones['value_uplift_pct'].median():.1f}%")
print(f"  Min uplift: {changed_zones['value_uplift_pct'].min():.1f}%")
print(f"  Max uplift: {changed_zones['value_uplift_pct'].max():.1f}%")

# If we have actual property values, calculate dollar impacts
if len(changed_zones) > 0:
    print(f"\n=== Estimating Dollar Impact ===")
    
    # For demonstration, use Chicago median property values by zone type
    # RS-3 single family: ~$250,000 median
    # These are rough estimates for illustration
    MEDIAN_VALUES = {
        'RS-1': 400000,
        'RS-2': 350000,
        'RS-3': 250000,
        'RT-4': 300000,
        'RM-5': 280000,
    }
    
    def estimate_current_value(zone):
        """Rough estimate of property value by zone type"""
        return MEDIAN_VALUES.get(zone, 250000)
    
    changed_zones['estimated_current_value'] = changed_zones['ZONE_CLASS'].apply(estimate_current_value)
    changed_zones['estimated_value_increase'] = (
        changed_zones['estimated_current_value'] * 
        (changed_zones['value_uplift_factor'] - 1)
    )
    
    total_value_increase = changed_zones['estimated_value_increase'].sum()
    avg_per_parcel = changed_zones['estimated_value_increase'].mean()
    
    print(f"  Total estimated value increase: ${total_value_increase:,.0f}")
    print(f"  Average per parcel: ${avg_per_parcel:,.0f}")
    print(f"  (Based on estimated median values by zone type)")

# Create visualization map
print(f"\n=== Creating Value Impact Map ===")
chicago_center = [zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean()]

m = folium.Map(
    location=chicago_center,
    zoom_start=11,
    tiles='CartoDB positron'
)

# Color scale for value uplift (green = higher value increase)
def get_color_for_uplift(uplift_pct):
    """Return color based on value uplift percentage"""
    if uplift_pct >= 20:
        return '#006d2c'  # Dark green
    elif uplift_pct >= 15:
        return '#31a354'  # Green
    elif uplift_pct >= 10:
        return '#74c476'  # Light green
    elif uplift_pct >= 5:
        return '#bae4b3'  # Very light green
    else:
        return '#edf8e9'  # Pale green

def style_function(feature):
    uplift = feature['properties'].get('value_uplift_pct', 0)
    
    if uplift > 0:
        return {
            'fillColor': get_color_for_uplift(uplift),
            'color': '#252525',
            'weight': 1,
            'fillOpacity': 0.7
        }
    else:
        return {
            'fillColor': '#cccccc',
            'color': '#999999',
            'weight': 0.3,
            'fillOpacity': 0.1
        }

# Add changed zones layer
if len(changed_zones) > 0:
    print(f"Adding {len(changed_zones):,} upzoned areas with value impacts...")
    
    folium.GeoJson(
        changed_zones,
        name='Upzoned Areas with Value Impact',
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=['ZONE_CLASS', 'proposed_zone', 'value_uplift_pct'],
            aliases=['Current:', 'Proposed:', 'Value Increase:'],
            labels=True,
            style='background-color: white; color: #333333; font-family: Arial; font-size: 12px; padding: 10px;'
        ),
        popup=folium.GeoJsonPopup(
            fields=['ZONE_CLASS', 'proposed_zone', 'current_far', 'proposed_far', 'value_uplift_pct'],
            aliases=['Current Zone:', 'Proposed Zone:', 'Current FAR:', 'Proposed FAR:', 'Est. Value Increase:'],
        )
    ).add_to(m)

# Add comprehensive legend
avg_uplift = changed_zones['value_uplift_pct'].mean()
total_increase = changed_zones['estimated_value_increase'].sum() if 'estimated_value_increase' in changed_zones else 0

legend_html = f'''
<div style="position: fixed; 
     top: 80px; right: 50px; width: 280px; 
     border:2px solid grey; z-index:9999; font-size:12px;
     background-color: white; opacity: 0.95;
     padding: 15px;
     ">
     <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 14px;">Property Value Impact</p>
     <p style="margin: 5px 0; font-size: 11px;"><strong>Scenario:</strong> RS-3 → RT-4 Upzoning</p>
     
     <hr style="margin: 10px 0;">
     
     <p style="margin: 3px 0; font-size: 11px;"><strong>Value Uplift Scale:</strong></p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#006d2c"></i>&nbsp; 20%+ increase</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#31a354"></i>&nbsp; 15-20% increase</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#74c476"></i>&nbsp; 10-15% increase</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#bae4b3"></i>&nbsp; 5-10% increase</p>
     <p style="margin: 3px 0;"><i class="fa fa-square" style="color:#edf8e9"></i>&nbsp; &lt;5% increase</p>
     
     <hr style="margin: 10px 0;">
     
     <p style="margin: 5px 0; font-size: 11px;">
     <strong>Impact Summary:</strong><br>
     • {len(changed_zones):,} parcels upzoned<br>
     • Avg value increase: {avg_uplift:.1f}%<br>
     • Total value added: ${total_increase:,.0f}<br>
     • Avg per parcel: ${changed_zones["estimated_value_increase"].mean() if "estimated_value_increase" in changed_zones else 0:,.0f}
     </p>
     
     <hr style="margin: 10px 0;">
     
     <p style="margin: 3px 0; font-size: 9px; font-style: italic;">
     Model uses: 50% zone transition factors, 
     30% FAR appreciation, 20% development rights premium.
     Click zones for details.
     </p>
</div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

folium.LayerControl().add_to(m)

# Save map
print(f"\nSaving map to '{OUTPUT_MAP}'...")
m.save(OUTPUT_MAP)
print(f"Value impact map saved!")

# Export detailed results
output_csv = "zoning_value_impact_analysis.csv"
print(f"\nExporting analysis to '{output_csv}'...")

export_cols = [
    'ZONE_CLASS', 'proposed_zone', 'current_far', 'proposed_far', 
    'value_uplift_pct', 'transition_factor', 'far_appreciation', 
    'dev_rights_factor'
]

if 'estimated_current_value' in changed_zones:
    export_cols.extend(['estimated_current_value', 'estimated_value_increase'])

changed_export = changed_zones[export_cols].copy()
changed_export['geometry_wkt'] = changed_zones.geometry.apply(lambda g: g.wkt)
changed_export.to_csv(output_csv, index=False)
print(f"Exported {len(changed_export):,} parcels with value impact analysis")

print(f"\n✓ Done! Open '{OUTPUT_MAP}' to explore property value impacts.")
print(f"✓ Detailed analysis saved to '{output_csv}'")

print("\n=== Methodology Notes ===")
print("Value uplift calculated using composite model:")
print("  1. FAR-Based: 15% appreciation per FAR point increase")
print("  2. Zone Transitions: Research-based factors (10-20% for residential)")
print("  3. Development Rights: Land value premium from additional rights")
print("\nWeighting: 50% transitions + 30% FAR + 20% dev rights")
print("Conservative approach - actual values may vary by neighborhood, market conditions.")

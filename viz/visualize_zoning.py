"""
Visualize Chicago Zoning Map
=============================
Creates an interactive city-wide Folium zoning map with SimCity 2000-inspired
color scheme, opacity-encoded density, and rich tooltips/popups.

Usage:
    python -m viz.visualize_zoning
"""

import geopandas as gpd
import pandas as pd
import folium
from folium import GeoJson

from src.config import (
    CHICAGO_ZONING_GEOJSON, ZONING_CODES_CSV, ZONING_MAP,
    ZONE_TYPE_COLORS, ZONE_TYPE_NAMES, ensure_dirs,
)


def main():
    ensure_dirs()

    print(f"Loading zoning data from '{CHICAGO_ZONING_GEOJSON}'...")
    zoning_gdf = gpd.read_file(CHICAGO_ZONING_GEOJSON).to_crs(epsg=4326)
    print(f"Loaded {len(zoning_gdf)} zoning parcels.")

    print(f"\nLoading zoning codes from '{ZONING_CODES_CSV}'...")
    zoning_codes_df = pd.read_csv(ZONING_CODES_CSV)

    zoning_lookup = {}
    for _, row in zoning_codes_df.iterrows():
        zoning_lookup[row["district_type_code"]] = {
            "title": row["district_title"],
            "description": row["juan_description"],
            "far": row["floor_area_ratio"],
            "max_height": row["maximum_building_height"],
            "zone_type": row["zone_type"],
        }

    def get_zone_info(zone_class):
        return zoning_lookup.get(zone_class, {
            "title": "Unknown", "description": f"Zone: {zone_class}",
            "far": "N/A", "max_height": "N/A", "zone_type": None,
        })

    # Enrich data
    zoning_gdf["zone_name"] = zoning_gdf["ZONE_CLASS"].apply(lambda x: get_zone_info(x)["title"])
    zoning_gdf["zone_description"] = zoning_gdf["ZONE_CLASS"].apply(lambda x: get_zone_info(x)["description"])
    zoning_gdf["far"] = zoning_gdf["ZONE_CLASS"].apply(lambda x: get_zone_info(x)["far"])

    # Create map
    chicago_center = [zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean()]
    m = folium.Map(location=chicago_center, zoom_start=11, tiles="CartoDB positron")

    def style_function(feature):
        zone_type = feature["properties"].get("ZONE_TYPE", 0)
        zone_class = feature["properties"].get("ZONE_CLASS", "")
        color = ZONE_TYPE_COLORS.get(zone_type, "#808080")
        opacity = 0.35
        if "-" in str(zone_class):
            try:
                parts = str(zone_class).split("-")
                if len(parts) > 1 and parts[1].replace(".", "").isdigit():
                    density = float(parts[1])
                    opacity = min(0.15 + (density / 20.0), 0.65)
            except (ValueError, IndexError):
                pass
        return {"fillColor": color, "color": "#000000", "weight": 0.5, "fillOpacity": opacity}

    def highlight_function(feature):
        return {"fillColor": "#ffff00", "color": "#000000", "weight": 2, "fillOpacity": 0.7}

    GeoJson(
        zoning_gdf,
        name="Chicago Zoning",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=["ZONE_CLASS", "zone_name"],
            aliases=["Zone:", "District:"],
        ),
        popup=folium.GeoJsonPopup(
            fields=["ZONE_CLASS", "zone_name", "zone_description", "far"],
            aliases=["Zone Code:", "District:", "Description:", "FAR:"],
        ),
    ).add_to(m)

    # Legend
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 200px;
    border:2px solid grey; z-index:9999; font-size:12px;
    background-color: white; opacity: 0.95; padding: 10px;">
    <p style="font-weight: bold;">Chicago Zoning Types</p>
    <p><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[4]}"></i> Residential</p>
    <p><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[1]}"></i> Business/Commercial</p>
    <p><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[3]}"></i> Manufacturing</p>
    <p><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[5]}"></i> Planned Development</p>
    <p><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[12]}"></i> Parks</p>
    <p><i class="fa fa-square" style="color:{ZONE_TYPE_COLORS[11]}"></i> Transportation</p>
    <hr>
    <p style="font-size: 10px; font-style: italic;">
    Opacity = density (FAR)<br>Click for details</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    folium.LayerControl().add_to(m)

    m.save(str(ZONING_MAP))
    print(f"\nSaved: {ZONING_MAP}")

    # Summary stats
    print(f"\n=== Zoning Summary ({len(zoning_gdf):,} parcels) ===")
    for zt, name in sorted(ZONE_TYPE_NAMES.items()):
        count = len(zoning_gdf[zoning_gdf["ZONE_TYPE"] == zt])
        print(f"  {name}: {count:,} ({count / len(zoning_gdf) * 100:.1f}%)")


if __name__ == "__main__":
    main()

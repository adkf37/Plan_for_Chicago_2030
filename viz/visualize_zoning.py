"""
Visualize Chicago Zoning Map
=============================
Creates an interactive city-wide PyDeck zoning map with SimCity 2000-inspired
color scheme, opacity-encoded density, and rich tooltips.

Usage:
    python -m viz.visualize_zoning
"""

import geopandas as gpd
import pandas as pd

from src.config import (
    CHICAGO_ZONING_GEOJSON, ZONING_CODES_CSV, ZONING_MAP,
    ZONE_TYPE_COLORS, ZONE_TYPE_NAMES, ensure_dirs,
)
from src.pydeck_utils import (
    create_deck, save_map, geojson_fill_layer, rgba_column,
    legend_html, hex_to_rgba,
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
    chicago_center = (zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean())

    def _color(row):
        zone_type = row.get("ZONE_TYPE", 0)
        zone_class = str(row.get("ZONE_CLASS", ""))
        base = hex_to_rgba(ZONE_TYPE_COLORS.get(zone_type, "#808080"), 90)

        # Opacity-encode density from zone class suffix
        if "-" in zone_class:
            try:
                parts = zone_class.split("-")
                if len(parts) > 1 and parts[1].replace(".", "").isdigit():
                    density = float(parts[1])
                    alpha = int(min(40 + (density / 20.0) * 255, 165))
                    base[3] = alpha
            except (ValueError, IndexError):
                pass
        return base

    zoning_gdf = rgba_column(zoning_gdf, _color)

    layer = geojson_fill_layer(
        "chicago-zoning",
        zoning_gdf,
        get_fill_color="rgba",
        get_line_color=[0, 0, 0, 80],
        line_width_min_pixels=0.5,
        auto_highlight=True,
    )

    # Legend
    legend_desc = legend_html(
        "Chicago Zoning Types",
        [
            (ZONE_TYPE_COLORS[4], "Residential"),
            (ZONE_TYPE_COLORS[1], "Business/Commercial"),
            (ZONE_TYPE_COLORS[3], "Manufacturing"),
            (ZONE_TYPE_COLORS[5], "Planned Development"),
            (ZONE_TYPE_COLORS[12], "Parks"),
            (ZONE_TYPE_COLORS[11], "Transportation"),
        ],
        footer="Opacity = density (FAR)<br>Click for details",
    )

    deck = create_deck(
        [layer],
        center=chicago_center,
        zoom=11,
        tooltip_html="<b>{ZONE_CLASS}</b><br>{zone_name}<br>{zone_description}<br>FAR: {far}",
        description=legend_desc,
    )
    save_map(deck, ZONING_MAP)

    # Summary stats
    print(f"\n=== Zoning Summary ({len(zoning_gdf):,} parcels) ===")
    for zt, name in sorted(ZONE_TYPE_NAMES.items()):
        count = len(zoning_gdf[zoning_gdf["ZONE_TYPE"] == zt])
        print(f"  {name}: {count:,} ({count / len(zoning_gdf) * 100:.1f}%)")


if __name__ == "__main__":
    main()

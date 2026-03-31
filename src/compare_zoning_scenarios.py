"""
Compare Zoning Scenarios
========================
Compares current vs. proposed upzoning (e.g., RS-3 -> RT-4), calculates
FAR changes, and creates a PyDeck comparison map.

Usage:
    python -m src.compare_zoning_scenarios
"""

import geopandas as gpd
import pandas as pd
import numpy as np

from src.config import (
    CHICAGO_ZONING_GEOJSON, ZONING_CODES_CSV,
    COMPARISON_MAP, UPZONING_CHANGES_CSV,
    MAPS_DIR, PROCESSED_DIR, ensure_dirs,
)
from src.pydeck_utils import (
    create_deck, save_map, geojson_fill_layer, rgba_column,
    legend_html, hex_to_rgba,
)


def increase_far(zone_code):
    """Increase the FAR number in a zone code (e.g., C1-2 -> C1-3)."""
    if "-" in zone_code:
        parts = zone_code.split("-")
        if len(parts) == 2:
            try:
                current_far = float(parts[1])
                new_far = min(current_far + 1, 5)
                return f"{parts[0]}-{int(new_far) if new_far == int(new_far) else new_far}"
            except ValueError:
                pass
    return zone_code


def main():
    ensure_dirs()

    print(f"Loading zoning data from '{CHICAGO_ZONING_GEOJSON}'...")
    zoning_gdf = gpd.read_file(CHICAGO_ZONING_GEOJSON).to_crs(epsg=4326)
    print(f"Loaded {len(zoning_gdf)} zoning parcels.")

    print(f"\nLoading zoning codes from '{ZONING_CODES_CSV}'...")
    zoning_codes_df = pd.read_csv(ZONING_CODES_CSV)

    far_lookup = {}
    for _, row in zoning_codes_df.iterrows():
        try:
            far_lookup[row["district_type_code"]] = float(row["floor_area_ratio"])
        except (ValueError, TypeError):
            far_lookup[row["district_type_code"]] = 0

    def get_far(zone_class):
        return far_lookup.get(zone_class, 0)

    zoning_gdf["current_far"] = zoning_gdf["ZONE_CLASS"].apply(get_far)

    print("\n=== Current Zoning Statistics ===")
    print(f"Total FAR capacity: {zoning_gdf['current_far'].sum():,.0f}")
    print(f"Average FAR: {zoning_gdf['current_far'].mean():.2f}")

    # Apply scenario: RS-3 -> RT-4
    print("\n=== Applying Scenario: RS-3 -> RT-4 ===")
    zoning_gdf["proposed_zone"] = zoning_gdf["ZONE_CLASS"].copy()
    rs3_count = len(zoning_gdf[zoning_gdf["ZONE_CLASS"] == "RS-3"])
    print(f"Found {rs3_count:,} RS-3 parcels to upzone")

    zoning_gdf.loc[zoning_gdf["ZONE_CLASS"] == "RS-3", "proposed_zone"] = "RT-4"
    zoning_gdf["proposed_far"] = zoning_gdf["proposed_zone"].apply(get_far)
    zoning_gdf["far_change"] = zoning_gdf["proposed_far"] - zoning_gdf["current_far"]
    zoning_gdf["far_pct_change"] = (
        (zoning_gdf["proposed_far"] - zoning_gdf["current_far"])
        / zoning_gdf["current_far"].replace(0, np.nan)
    ) * 100

    far_increase = zoning_gdf["proposed_far"].sum() - zoning_gdf["current_far"].sum()
    far_pct_increase = (far_increase / zoning_gdf["current_far"].sum()) * 100
    changed_parcels = len(zoning_gdf[zoning_gdf["ZONE_CLASS"] != zoning_gdf["proposed_zone"]])
    pct_changed = (changed_parcels / len(zoning_gdf)) * 100

    print(f"\nFAR increase: {far_increase:,.0f} ({far_pct_increase:.1f}%)")
    print(f"Parcels changed: {changed_parcels:,} ({pct_changed:.1f}%)")

    # Create comparison map
    chicago_center = (zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean())

    changed_zones = zoning_gdf[zoning_gdf["ZONE_CLASS"] != zoning_gdf["proposed_zone"]].copy()

    if len(changed_zones) > 0:
        # Pre-compute RGBA fill colour based on FAR change
        def _color(row):
            fc = row.get("far_change", 0)
            alpha = int(min(75 + (fc * 75), 200))
            return [255, 68, 68, alpha]

        changed_zones = rgba_column(changed_zones, _color)

        layer = geojson_fill_layer(
            "upzoned-areas",
            changed_zones,
            get_fill_color="rgba",
            get_line_color=[204, 0, 0, 180],
            line_width_min_pixels=1,
        )
    else:
        layer = geojson_fill_layer("upzoned-areas", {"type": "FeatureCollection", "features": []})

    legend = legend_html(
        f"Scenario: RS-3 → RT-4",
        [("#ff4444", "Upzoned"), ("#cccccc", "Unchanged")],
        footer=f"{changed_parcels:,} parcels ({pct_changed:.1f}%)<br>"
               f"FAR increase: {far_increase:,.0f} ({far_pct_increase:.1f}%)",
    )

    deck = create_deck(
        [layer],
        center=chicago_center,
        zoom=11,
        tooltip_html="<b>{ZONE_CLASS}</b> → {proposed_zone}<br>FAR Δ: {far_change}",
        description=legend,
    )
    save_map(deck, COMPARISON_MAP)

    # Export CSV
    export = changed_zones[["ZONE_CLASS", "proposed_zone", "current_far", "proposed_far", "far_change", "far_pct_change"]].copy()
    export["geometry_wkt"] = changed_zones.geometry.apply(lambda g: g.wkt)
    export.to_csv(UPZONING_CHANGES_CSV, index=False)
    print(f"Exported {len(export):,} changed parcels to {UPZONING_CHANGES_CSV}")


if __name__ == "__main__":
    main()

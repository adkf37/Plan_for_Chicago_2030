"""
Zoning Value Impact Analysis
=============================
Combines zoning data with value uplift models (FAR-based, zone-transition,
and development rights premium) to estimate property value impacts of upzoning.

Usage:
    python -m src.zoning_value_impact
"""

import geopandas as gpd
import pandas as pd
import numpy as np

from src.config import (
    CHICAGO_ZONING_GEOJSON, ZONING_CODES_CSV, PARCELS_IN_AREA_CSV,
    VALUE_IMPACT_MAP, VALUE_IMPACT_CSV,
    FAR_APPRECIATION_RATE, ZONE_TRANSITION_FACTORS,
    DEVELOPMENT_RIGHTS_ADJUSTMENT, MEDIAN_VALUES_BY_ZONE,
    ensure_dirs,
)
from src.pydeck_utils import (
    create_deck, save_map, geojson_fill_layer, rgba_column,
    legend_html, hex_to_rgba,
)


def main():
    ensure_dirs()

    print("=== Property Value Uplift Model ===\n")

    zoning_gdf = gpd.read_file(CHICAGO_ZONING_GEOJSON).to_crs(epsg=4326)
    print(f"Loaded {len(zoning_gdf)} zoning parcels.")

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

    # Apply scenario: RS-3 -> RT-4
    zoning_gdf["proposed_zone"] = zoning_gdf["ZONE_CLASS"].copy()
    zoning_gdf.loc[zoning_gdf["ZONE_CLASS"] == "RS-3", "proposed_zone"] = "RT-4"
    zoning_gdf["proposed_far"] = zoning_gdf["proposed_zone"].apply(get_far)
    zoning_gdf["far_change"] = zoning_gdf["proposed_far"] - zoning_gdf["current_far"]

    # Method 1: FAR-based
    zoning_gdf["far_appreciation"] = 1 + (zoning_gdf["far_change"] * FAR_APPRECIATION_RATE)

    # Method 2: Zone transition
    def get_transition_factor(current, proposed):
        if current == proposed:
            return 1.0
        key = (current, proposed)
        if key in ZONE_TRANSITION_FACTORS:
            return ZONE_TRANSITION_FACTORS[key]
        cp = current.split("-")[0]
        pp = proposed.split("-")[0]
        if (cp, pp) in ZONE_TRANSITION_FACTORS:
            return ZONE_TRANSITION_FACTORS[(cp, pp)]
        fc, fp = get_far(current), get_far(proposed)
        if fc > 0:
            return 1 + ((fp / fc - 1) * FAR_APPRECIATION_RATE)
        return 1.0

    zoning_gdf["transition_factor"] = zoning_gdf.apply(
        lambda r: get_transition_factor(r["ZONE_CLASS"], r["proposed_zone"]), axis=1
    )

    # Method 3: Development rights
    zoning_gdf["dev_rights_factor"] = 1.0
    mask = zoning_gdf["current_far"] > 0
    zoning_gdf.loc[mask, "dev_rights_factor"] = (
        1 + ((zoning_gdf.loc[mask, "proposed_far"] / zoning_gdf.loc[mask, "current_far"]) - 1)
        * DEVELOPMENT_RIGHTS_ADJUSTMENT
    )

    # Composite: 50% transition, 30% FAR, 20% dev rights
    zoning_gdf["value_uplift_factor"] = (
        0.50 * zoning_gdf["transition_factor"]
        + 0.30 * zoning_gdf["far_appreciation"]
        + 0.20 * zoning_gdf["dev_rights_factor"]
    )
    zoning_gdf["value_uplift_pct"] = (zoning_gdf["value_uplift_factor"] - 1) * 100

    changed_zones = zoning_gdf[zoning_gdf["ZONE_CLASS"] != zoning_gdf["proposed_zone"]].copy()
    print(f"\n{len(changed_zones):,} parcels upzoned")
    print(f"Average uplift: {changed_zones['value_uplift_pct'].mean():.1f}%")

    # Dollar impacts
    changed_zones["estimated_current_value"] = changed_zones["ZONE_CLASS"].map(
        lambda z: MEDIAN_VALUES_BY_ZONE.get(z, 250000)
    )
    changed_zones["estimated_value_increase"] = (
        changed_zones["estimated_current_value"] * (changed_zones["value_uplift_factor"] - 1)
    )
    total_increase = changed_zones["estimated_value_increase"].sum()
    print(f"Total estimated value increase: ${total_increase:,.0f}")

    # Map
    chicago_center = (zoning_gdf.geometry.centroid.y.mean(), zoning_gdf.geometry.centroid.x.mean())

    def get_color(pct):
        if pct >= 20:
            return [0, 109, 44, 180]
        elif pct >= 15:
            return [49, 163, 84, 180]
        elif pct >= 10:
            return [116, 196, 118, 180]
        elif pct >= 5:
            return [186, 228, 179, 180]
        return [237, 248, 233, 180]

    if len(changed_zones) > 0:
        def _color(row):
            uplift = row.get("value_uplift_pct", 0)
            if uplift > 0:
                return get_color(uplift)
            return [204, 204, 204, 25]

        changed_zones = rgba_column(changed_zones, _color)

        layer = geojson_fill_layer(
            "value-impact",
            changed_zones,
            get_fill_color="rgba",
            get_line_color=[37, 37, 37, 180],
            line_width_min_pixels=1,
        )
    else:
        layer = geojson_fill_layer("value-impact", {"type": "FeatureCollection", "features": []})

    legend_desc = legend_html(
        "Value Uplift",
        [
            ("#006d2c", "≥ 20%"),
            ("#31a354", "15–20%"),
            ("#74c476", "10–15%"),
            ("#bae4b3", "5–10%"),
            ("#edf8e9", "< 5%"),
        ],
    )

    deck = create_deck(
        [layer],
        center=chicago_center,
        zoom=11,
        tooltip_html="<b>{ZONE_CLASS}</b> → {proposed_zone}<br>Value Uplift: {value_uplift_pct}%",
        description=legend_desc,
    )
    save_map(deck, VALUE_IMPACT_MAP)

    # Export CSV
    export_cols = [
        "ZONE_CLASS", "proposed_zone", "current_far", "proposed_far",
        "value_uplift_pct", "transition_factor", "far_appreciation",
        "dev_rights_factor", "estimated_current_value", "estimated_value_increase",
    ]
    export = changed_zones[[c for c in export_cols if c in changed_zones.columns]].copy()
    export["geometry_wkt"] = changed_zones.geometry.apply(lambda g: g.wkt)
    export.to_csv(VALUE_IMPACT_CSV, index=False)
    print(f"Exported {len(export):,} parcels to {VALUE_IMPACT_CSV}")


if __name__ == "__main__":
    main()

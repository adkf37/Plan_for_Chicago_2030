"""
Zoning Classification & Density Mapping
========================================
Defines housing density categories and provides functions for classifying
parcels by existing/proposed zoning. Placeholder module — spatial join
logic needs implementation.

Usage:
    python -m src.zoning
"""

import pandas as pd

from src.config import HOUSING_DENSITY_CATEGORIES


def classify_existing_density(parcels_gdf):
    """
    Classify parcels by existing density category.

    TODO: Implement using actual parcel attributes (units, area, land use code).
    Currently returns 'Unknown' for all parcels.
    """
    if parcels_gdf is None:
        return None
    classified = parcels_gdf.copy()
    classified["existing_density_category"] = "Unknown"
    print("Placeholder: Existing density classification needs parcel attribute data.")
    return classified


def generate_proposed_zoning(current_zoning_gdf, proposed_rules):
    """
    Create proposed zoning layer by applying plan rules to current zoning.

    TODO: Implement spatial rule application (e.g., upzone near transit,
    convert industrial to mixed-use).
    """
    if current_zoning_gdf is None:
        return None
    proposed = current_zoning_gdf.copy()
    proposed["proposed_zoning_class"] = proposed.get("zoning_class", proposed.get("ZONE_CLASS", "Unknown"))
    print("Placeholder: Proposed zoning generation needs spatial rule implementation.")
    return proposed


def assign_proposed_density(parcels_gdf, proposed_zoning_gdf):
    """
    Assign proposed density categories to parcels via spatial join.

    TODO: Implement spatial join between parcels and proposed zoning.
    """
    if parcels_gdf is None or proposed_zoning_gdf is None:
        return None
    assigned = parcels_gdf.copy()
    assigned["proposed_density_category"] = "Unknown"
    print("Placeholder: Proposed density assignment needs spatial join implementation.")
    return assigned


if __name__ == "__main__":
    print("Zoning Module — Housing Density Categories:")
    for code, info in HOUSING_DENSITY_CATEGORIES.items():
        print(f"  {code}: {info['name']} ({info['units_per_acre_min']}-{info['units_per_acre_max']} units/acre)")
    print("\nNote: Classification functions are placeholders awaiting spatial join implementation.")

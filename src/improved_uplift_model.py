"""
Improved Zoning Uplift Model
============================
Uses empirical historical appreciation rates to model property value uplift
from rezoning scenarios. Combines historical rates with scenario rules.

Usage:
    python -m src.improved_uplift_model
"""

import pandas as pd
import numpy as np
from pathlib import Path

from src.config import (
    PARCELS_IN_AREA_CSV, HISTORICAL_DATA_DIR, UPLIFT_SCENARIOS_DIR,
    ASSESSMENT_RATIO, PROPERTY_TAX_RATE, ensure_dirs,
    APPRECIATION_BY_ZONING_CSV, CTA_STATIONS_GEOJSON,
)


# ---------------------------------------------------------------------------
# Cook County property class code → Chicago zoning zone-type mapping
# Zone-type strings must match keys in historical_appreciation_by_zoning.csv
# (B, C, M, RM, RS, RT, Unknown)
# ---------------------------------------------------------------------------
CLASS_TO_ZONE_TYPE: dict[str, str] = {
    # Vacant / agricultural
    "100": "RS", "190": "RS",
    # Single-family residential
    "201": "RS", "202": "RS", "203": "RS", "204": "RS",
    "205": "RS", "206": "RS", "207": "RS", "208": "RS", "209": "RS",
    "290": "RS",
    # 2–6-unit / townhouse residential
    "211": "RT", "212": "RT", "218": "RT",
    "278": "RT",
    "299": "RT",   # dominant class — general residential
    # Multi-family / apartment
    "225": "RM", "241": "RM",
    "318": "RM", "390": "RM", "391": "RM", "397": "RM",
    # Commercial / mixed-use
    "295": "B", "297": "B",
    "500": "B", "517": "B", "522": "B", "523": "B",
    "528": "B", "530": "B", "533": "B",
    # Industrial / manufacturing
    "492": "M", "580": "M",
    "590": "M", "591": "M", "592": "M", "593": "M",
    "597": "M", "599": "M",
    "748": "M", "991": "M",
    # Exempt / non-classified
    "EX": "Unknown", "RR": "Unknown",
}


def _map_class_to_zone_type(class_code) -> str:
    """Map a Cook County property class code to the Chicago zoning zone type
    used as keys in historical_appreciation_by_zoning.csv.

    Falls back to ``"Unknown"`` for unrecognised codes (which itself has a
    real appreciation rate in the CSV).
    """
    return CLASS_TO_ZONE_TYPE.get(str(class_code), "Unknown")


def _add_near_transit(parcels_df: pd.DataFrame, max_dist_m: float = 800.0) -> None:
    """Compute and add ``near_transit`` column to *parcels_df* in-place.

    Parses WKT ``geometry`` column, projects to Illinois State Plane East
    (EPSG:3435, feet), and flags parcels within *max_dist_m* metres of any
    CTA L station.  Falls back to ``False`` for all parcels if geopandas or
    the stations file is unavailable.
    """
    try:
        import geopandas as gpd
        from shapely.wkt import loads as wkt_loads
    except ImportError:
        parcels_df["near_transit"] = False
        print("  WARNING: geopandas/shapely not available; near_transit set to False.")
        return

    if not CTA_STATIONS_GEOJSON.exists():
        parcels_df["near_transit"] = False
        print(f"  WARNING: {CTA_STATIONS_GEOJSON} not found; near_transit set to False.")
        return

    try:
        geoms = parcels_df["geometry"].apply(wkt_loads)
        gdf = gpd.GeoDataFrame(parcels_df.copy(), geometry=geoms, crs="EPSG:4326").to_crs("EPSG:3435")
        stations = gpd.read_file(CTA_STATIONS_GEOJSON).to_crs("EPSG:3435")
        station_union = (
            stations.geometry.union_all()
            if hasattr(stations.geometry, "union_all")
            else stations.geometry.unary_union
        )
        max_dist_ft = max_dist_m * 3.28084  # EPSG:3435 is in feet
        distances = gdf.geometry.distance(station_union)
        parcels_df["near_transit"] = (distances <= max_dist_ft).values
        n = int(parcels_df["near_transit"].sum())
        print(f"  near_transit: {n}/{len(parcels_df)} parcels within {max_dist_m:.0f} m of CTA L stations.")
    except Exception as exc:
        parcels_df["near_transit"] = False
        print(f"  WARNING: near_transit computation failed ({exc}); set to False.")


def load_data():
    """Load parcels and appreciation rates."""
    print("=" * 80)
    print("LOADING DATA")
    print("=" * 80)

    try:
        parcels_df = pd.read_csv(PARCELS_IN_AREA_CSV)
        print(f"Loaded {len(parcels_df)} parcels")
    except FileNotFoundError:
        print(f"ERROR: {PARCELS_IN_AREA_CSV} not found. Run 'python -m src.analyze_area' first.")
        return None, None

    # Enrich with near_transit (needed by the near_transit scenario filter)
    if "near_transit" not in parcels_df.columns:
        _add_near_transit(parcels_df)

    try:
        appreciation_df = pd.read_csv(APPRECIATION_BY_ZONING_CSV)
        print(f"Loaded appreciation rates for {len(appreciation_df)} zoning types")
    except FileNotFoundError:
        print(f"ERROR: {APPRECIATION_BY_ZONING_CSV} not found. Run 'python -m src.process_historical' first.")
        return None, None

    # Normalise to expected column names and percentage scale.
    # process_historical.py writes fractions (0.06 = 6 %); the lookup and
    # apply_scenario functions expect percentage-scale values (6.0 = 6 %).
    col_map = {}
    if "avg_annual_appreciation" in appreciation_df.columns and "avg_annual_appreciation_pct" not in appreciation_df.columns:
        col_map["avg_annual_appreciation"] = "avg_annual_appreciation_pct"
    if "median_annual_appreciation" in appreciation_df.columns and "median_annual_appreciation_pct" not in appreciation_df.columns:
        col_map["median_annual_appreciation"] = "median_annual_appreciation_pct"
    if "total_observations" in appreciation_df.columns and "parcel_count" not in appreciation_df.columns:
        col_map["total_observations"] = "parcel_count"
    if col_map:
        appreciation_df = appreciation_df.rename(columns=col_map)
    if "avg_annual_appreciation_pct" in appreciation_df.columns and appreciation_df["avg_annual_appreciation_pct"].max() <= 1.0:
        appreciation_df["avg_annual_appreciation_pct"] *= 100
    if "median_annual_appreciation_pct" in appreciation_df.columns and appreciation_df["median_annual_appreciation_pct"].max() <= 1.0:
        appreciation_df["median_annual_appreciation_pct"] *= 100

    return parcels_df, appreciation_df


def prepare_parcels(parcels_df):
    """Prepare parcel data with market value estimates."""
    if "certified_tot" not in parcels_df.columns:
        print("ERROR: 'certified_tot' column not found")
        return None
    parcels_df["estimated_market_value"] = parcels_df["certified_tot"] / ASSESSMENT_RATIO
    parcels_df["current_zoning"] = parcels_df.get("class", parcels_df.get("current_zoning", "Unknown"))
    print(f"Parcels by zoning:\n{parcels_df['current_zoning'].value_counts()}")
    return parcels_df


def create_appreciation_lookup(appreciation_df):
    """Create {zoning_type: {rate info}} lookup."""
    lookup = {}
    for _, row in appreciation_df.iterrows():
        lookup[row["zoning_type"]] = {
            "annual_appreciation_pct": row["avg_annual_appreciation_pct"],
            "median_annual_appreciation_pct": row["median_annual_appreciation_pct"],
            "parcel_count": row["parcel_count"],
        }
    return lookup


def define_rezoning_scenarios():
    """Define rezoning scenarios for Plan for Chicago 2030."""
    return {
        "upzone_residential_low_to_medium": {
            "name": "Upzone Low-Density Residential to Medium-Density",
            "description": "Rezone single-family (RS) to multi-family (RM) near transit corridors",
            "rules": [
                {
                    "from_zoning": "299",
                    "to_zoning": "211",
                    "filter": None,
                    # Upzoning general residential to medium-density mixed-use unlocks
                    # commercial-corridor appreciation rates (C = 8.31 %/yr vs RT = 6.39 %/yr).
                    "to_zone_type": "C",
                },
            ],
        },
        "upzone_commercial": {
            "name": "Upzone Commercial Districts",
            "description": "Increase density in existing commercial zones",
            "rules": [
                {
                    "from_zoning": "295",
                    "to_zoning": "297",
                    "filter": None,
                    # Neighbourhood B-commercial upzoned for redevelopment accesses
                    # the higher commercial-corridor C appreciation rate.
                    "to_zone_type": "C",
                },
            ],
        },
        "transit_oriented_development": {
            "name": "Transit-Oriented Development Zones",
            "description": "Create high-density mixed-use near major transit",
            "rules": [
                {
                    "from_zoning": "299",
                    "to_zoning": "297",
                    "filter": "near_transit",
                    "to_zone_type": "C",
                },
                {
                    "from_zoning": "295",
                    "to_zoning": "297",
                    "filter": "near_transit",
                    "to_zone_type": "C",
                },
            ],
        },
    }


def apply_scenario(parcels_df, scenario, appreciation_lookup, time_horizon_years=10):
    """Apply a rezoning scenario and calculate value uplift."""
    results = parcels_df.copy()
    results["rezoned"] = False
    results["target_zoning"] = results["current_zoning"]
    # Explicit zone-type override per rule (optional ``to_zone_type`` field);
    # None means fall back to _map_class_to_zone_type(target_zoning).
    results["target_zone_type"] = None
    results["current_annual_appreciation_pct"] = 0.0
    results["target_annual_appreciation_pct"] = 0.0
    results["differential_appreciation_pct"] = 0.0

    for rule in scenario["rules"]:
        if rule["filter"] is None:
            mask = results["current_zoning"] == rule["from_zoning"]
            results.loc[mask, "rezoned"] = True
            results.loc[mask, "target_zoning"] = rule["to_zoning"]
            if rule.get("to_zone_type"):
                results.loc[mask, "target_zone_type"] = rule["to_zone_type"]
        elif rule["filter"] == "near_transit":
            if "near_transit" in results.columns:
                near_mask = results["near_transit"].fillna(False).astype(bool)
            else:
                near_mask = pd.Series(False, index=results.index)
                print("  WARNING: 'near_transit' column missing; near_transit filter returns 0 parcels.")
            mask = (results["current_zoning"] == rule["from_zoning"]) & near_mask
            results.loc[mask, "rezoned"] = True
            results.loc[mask, "target_zoning"] = rule["to_zoning"]
            if rule.get("to_zone_type"):
                results.loc[mask, "target_zone_type"] = rule["to_zone_type"]

    # Fallback rate: median of all known appreciation rates in the lookup
    _all_rates = [v["annual_appreciation_pct"] for v in appreciation_lookup.values() if v.get("annual_appreciation_pct", 0) > 0]
    fallback_rate = float(np.median(_all_rates)) if _all_rates else 0.0

    # Translate class codes → zone types, then look up appreciation rates.
    # The appreciation CSV is keyed by zone-type strings (B, C, M, RM, RS, RT,
    # Unknown) — NOT by Cook County class codes — so a direct lookup on class
    # codes would always miss and return $0 uplift.
    cur_zone_series = results["current_zoning"].apply(_map_class_to_zone_type)
    # For the target zone type: use the rule-level ``to_zone_type`` override
    # when present (policy intent), otherwise derive from the target class code.
    tgt_zone_series = results.apply(
        lambda r: r["target_zone_type"]
        if (r["target_zone_type"] is not None and r["target_zone_type"] == r["target_zone_type"])  # not None/NaN
        else _map_class_to_zone_type(r["target_zoning"]),
        axis=1,
    )

    results["current_annual_appreciation_pct"] = cur_zone_series.apply(
        lambda z: appreciation_lookup.get(z, {}).get("annual_appreciation_pct", fallback_rate)
    )
    results["target_annual_appreciation_pct"] = tgt_zone_series.apply(
        lambda z: appreciation_lookup.get(z, {}).get("annual_appreciation_pct", fallback_rate)
    )
    results["differential_appreciation_pct"] = results.apply(
        lambda r: r["target_annual_appreciation_pct"] - r["current_annual_appreciation_pct"]
        if r["rezoned"] else 0.0,
        axis=1,
    )

    results["baseline_future_value"] = (
        results["estimated_market_value"]
        * (1 + results["current_annual_appreciation_pct"] / 100) ** time_horizon_years
    )
    results["rezoned_future_value"] = results.apply(
        lambda r: (
            r["estimated_market_value"]
            * (1 + r["target_annual_appreciation_pct"] / 100) ** time_horizon_years
            if r["rezoned"]
            else r["baseline_future_value"]
        ),
        axis=1,
    )
    results["value_uplift"] = results["rezoned_future_value"] - results["baseline_future_value"]
    results["value_uplift_pct"] = (results["value_uplift"] / results["baseline_future_value"] * 100).fillna(0)
    results["baseline_annual_tax"] = results["baseline_future_value"] * PROPERTY_TAX_RATE
    results["rezoned_annual_tax"] = results["rezoned_future_value"] * PROPERTY_TAX_RATE
    results["annual_tax_increase"] = results["rezoned_annual_tax"] - results["baseline_annual_tax"]
    return results


def run_all_scenarios(parcels_df, appreciation_lookup, time_horizon=10):
    """Run all scenarios and compile results."""
    print(f"\nRUNNING SCENARIOS (horizon: {time_horizon} years)\n")
    scenarios = define_rezoning_scenarios()
    summaries = []

    for sid, scenario in scenarios.items():
        print(f"--- {scenario['name']} ---")
        results = apply_scenario(parcels_df, scenario, appreciation_lookup, time_horizon)
        rezoned = results[results["rezoned"]]
        if len(rezoned) == 0:
            print("  No parcels matched.")
            summaries.append({"scenario_name": scenario["name"], "parcels_rezoned": 0})
        else:
            uplift = rezoned["value_uplift"].sum()
            print(f"  {len(rezoned)} parcels | uplift: ${uplift:,.0f}")
            summaries.append({
                "scenario_name": scenario["name"],
                "parcels_rezoned": len(rezoned),
                "total_value_uplift": uplift,
                "avg_uplift_per_parcel": rezoned["value_uplift"].mean(),
                "total_annual_tax_increase": rezoned["annual_tax_increase"].sum(),
            })

        # Save detailed results
        ensure_dirs()
        results.to_csv(UPLIFT_SCENARIOS_DIR / f"scenario_{sid}_details.csv", index=False)

    return pd.DataFrame(summaries)


def run_uplift_analysis(time_horizon: int = 10):
    """Run the full uplift analysis and return the scenario summary DataFrame.

    Returns ``None`` if required input data is missing.
    """
    parcels_df, appreciation_df = load_data()
    if parcels_df is None:
        return None

    parcels_df = prepare_parcels(parcels_df)
    if parcels_df is None:
        return None

    lookup = create_appreciation_lookup(appreciation_df)
    summary = run_all_scenarios(parcels_df, lookup, time_horizon=time_horizon)

    ensure_dirs()
    summary.to_csv(UPLIFT_SCENARIOS_DIR / "rezoning_scenario_results.csv", index=False)
    print(f"\nResults saved to {UPLIFT_SCENARIOS_DIR}")
    return summary


def main():
    run_uplift_analysis()


if __name__ == "__main__":
    main()

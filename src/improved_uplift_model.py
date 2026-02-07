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
)


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

    appreciation_file = HISTORICAL_DATA_DIR / "appreciation_by_zoning.csv"
    try:
        appreciation_df = pd.read_csv(appreciation_file)
        print(f"Loaded appreciation rates for {len(appreciation_df)} zoning types")
    except FileNotFoundError:
        print(f"ERROR: {appreciation_file} not found. Run 'python -m src.download_historical' first.")
        return None, None

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
                {"from_zoning": "202", "to_zoning": "211", "filter": None},
                {"from_zoning": "203", "to_zoning": "211", "filter": None},
            ],
        },
        "upzone_commercial": {
            "name": "Upzone Commercial Districts",
            "description": "Increase density in existing commercial zones",
            "rules": [
                {"from_zoning": "295", "to_zoning": "297", "filter": None},
            ],
        },
        "transit_oriented_development": {
            "name": "Transit-Oriented Development Zones",
            "description": "Create high-density mixed-use near major transit",
            "rules": [
                {"from_zoning": "202", "to_zoning": "297", "filter": "near_transit"},
                {"from_zoning": "203", "to_zoning": "297", "filter": "near_transit"},
                {"from_zoning": "295", "to_zoning": "297", "filter": "near_transit"},
            ],
        },
    }


def apply_scenario(parcels_df, scenario, appreciation_lookup, time_horizon_years=10):
    """Apply a rezoning scenario and calculate value uplift."""
    results = parcels_df.copy()
    results["rezoned"] = False
    results["target_zoning"] = results["current_zoning"]
    results["current_annual_appreciation_pct"] = 0.0
    results["target_annual_appreciation_pct"] = 0.0
    results["differential_appreciation_pct"] = 0.0

    for rule in scenario["rules"]:
        if rule["filter"] is None:
            mask = results["current_zoning"] == rule["from_zoning"]
            results.loc[mask, "rezoned"] = True
            results.loc[mask, "target_zoning"] = rule["to_zoning"]

    for idx, row in results.iterrows():
        cur = row["current_zoning"]
        tgt = row["target_zoning"]
        cur_rate = appreciation_lookup.get(cur, {}).get("annual_appreciation_pct", 0)
        tgt_rate = appreciation_lookup.get(tgt, {}).get("annual_appreciation_pct", 0)
        results.at[idx, "current_annual_appreciation_pct"] = cur_rate
        results.at[idx, "target_annual_appreciation_pct"] = tgt_rate
        if row["rezoned"]:
            results.at[idx, "differential_appreciation_pct"] = tgt_rate - cur_rate

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


def main():
    parcels_df, appreciation_df = load_data()
    if parcels_df is None:
        return

    parcels_df = prepare_parcels(parcels_df)
    if parcels_df is None:
        return

    lookup = create_appreciation_lookup(appreciation_df)
    summary = run_all_scenarios(parcels_df, lookup, time_horizon=10)

    ensure_dirs()
    summary.to_csv(UPLIFT_SCENARIOS_DIR / "rezoning_scenario_results.csv", index=False)
    print(f"\nResults saved to {UPLIFT_SCENARIOS_DIR}")


if __name__ == "__main__":
    main()

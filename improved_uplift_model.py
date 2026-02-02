"""
Improved Zoning Uplift Model
============================
Uses empirical historical appreciation rates by zoning type to model
property value uplift scenarios from rezoning.

This combines:
- Option 1: Historical appreciation rates by current zoning (empirical data)
- Option 2: Current zoning analysis with rezoning scenarios

The model assumes that when a parcel is rezoned, it will appreciate at the
rate historically observed for the target zoning type.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# --- Configuration ---
PARCELS_FILE = "parcels_in_area.csv"
APPRECIATION_RATES_FILE = "historical_data/appreciation_by_zoning.csv"
CHICAGO_ZONING_FILE = "chicago_zoning_2025.geojson"  # Optional: for mapping zoning codes

OUTPUT_DIR = Path("uplift_scenarios")
SCENARIO_RESULTS_FILE = OUTPUT_DIR / "rezoning_scenario_results.csv"
SUMMARY_REPORT_FILE = OUTPUT_DIR / "rezoning_impact_summary.txt"

# Cook County assessment ratio (assessed value / market value)
# Residential properties are typically assessed at 10% of market value
ASSESSMENT_RATIO = 0.10

# Property tax rate (example: 2.5% of market value, adjust for your area)
PROPERTY_TAX_RATE = 0.025


def load_data():
    """Load parcels and appreciation rates."""
    print("=" * 80)
    print("LOADING DATA")
    print("=" * 80)
    
    # Load parcels
    try:
        parcels_df = pd.read_csv(PARCELS_FILE)
        print(f"Loaded {len(parcels_df)} parcels from {PARCELS_FILE}")
    except FileNotFoundError:
        print(f"ERROR: Could not find {PARCELS_FILE}")
        return None, None
    
    # Load appreciation rates
    try:
        appreciation_df = pd.read_csv(APPRECIATION_RATES_FILE)
        print(f"Loaded appreciation rates for {len(appreciation_df)} zoning types")
        print(f"  from {APPRECIATION_RATES_FILE}")
    except FileNotFoundError:
        print(f"\nERROR: Could not find {APPRECIATION_RATES_FILE}")
        print("Please run download_historical_assessments.py first to generate this file.")
        return None, None
    
    return parcels_df, appreciation_df


def prepare_parcels(parcels_df):
    """Prepare parcel data for analysis."""
    print("\n--- Preparing parcel data ---")
    
    # Convert assessed value to market value estimate
    if 'certified_tot' in parcels_df.columns:
        parcels_df['estimated_market_value'] = parcels_df['certified_tot'] / ASSESSMENT_RATIO
        print(f"Calculated market values (assessment ratio: {ASSESSMENT_RATIO})")
    else:
        print("ERROR: 'certified_tot' column not found")
        return None
    
    # Identify zoning column
    zoning_col = 'class'  # Default to property class
    if 'class' not in parcels_df.columns:
        print("ERROR: 'class' column not found")
        return None
    
    parcels_df['current_zoning'] = parcels_df[zoning_col]
    
    print(f"Parcels by current zoning:")
    print(parcels_df['current_zoning'].value_counts())
    
    return parcels_df


def create_appreciation_lookup(appreciation_df):
    """Create a lookup dictionary for appreciation rates by zoning type."""
    lookup = {}
    for _, row in appreciation_df.iterrows():
        lookup[row['zoning_type']] = {
            'annual_appreciation_pct': row['avg_annual_appreciation_pct'],
            'median_annual_appreciation_pct': row['median_annual_appreciation_pct'],
            'parcel_count': row['parcel_count']
        }
    return lookup


def define_rezoning_scenarios():
    """
    Define rezoning scenarios for Plan for Chicago 2030.
    
    Each scenario specifies:
    - Which current zoning types are affected
    - What they would be rezoned to
    - Optional: geographic filters
    """
    scenarios = {
        'upzone_residential_low_to_medium': {
            'name': 'Upzone Low-Density Residential to Medium-Density',
            'description': 'Rezone single-family (RS) to multi-family (RM) near transit corridors',
            'rules': [
                {'from_zoning': '202', 'to_zoning': '211', 'filter': None},  # Example: RS-1 to RM-4.5
                {'from_zoning': '203', 'to_zoning': '211', 'filter': None},
            ]
        },
        'upzone_commercial': {
            'name': 'Upzone Commercial Districts',
            'description': 'Increase density in existing commercial zones',
            'rules': [
                {'from_zoning': '295', 'to_zoning': '297', 'filter': None},  # Commercial upzone example
            ]
        },
        'transit_oriented_development': {
            'name': 'Transit-Oriented Development Zones',
            'description': 'Create high-density mixed-use near major transit',
            'rules': [
                {'from_zoning': '202', 'to_zoning': '297', 'filter': 'near_transit'},
                {'from_zoning': '203', 'to_zoning': '297', 'filter': 'near_transit'},
                {'from_zoning': '295', 'to_zoning': '297', 'filter': 'near_transit'},
            ]
        }
    }
    
    return scenarios


def apply_scenario(parcels_df, scenario, appreciation_lookup, time_horizon_years=10):
    """
    Apply a rezoning scenario to parcels and calculate value uplift.
    
    Args:
        parcels_df: DataFrame of parcels with current zoning and values
        scenario: Dictionary defining the rezoning scenario
        appreciation_lookup: Dictionary of appreciation rates by zoning type
        time_horizon_years: Number of years to project into the future
    
    Returns:
        DataFrame with scenario results
    """
    results_df = parcels_df.copy()
    results_df['rezoned'] = False
    results_df['target_zoning'] = results_df['current_zoning']
    results_df['current_annual_appreciation_pct'] = 0.0
    results_df['target_annual_appreciation_pct'] = 0.0
    results_df['differential_appreciation_pct'] = 0.0
    
    # Apply rezoning rules
    for rule in scenario['rules']:
        from_zone = rule['from_zoning']
        to_zone = rule['to_zoning']
        
        # Apply filter if specified (for now, we'll skip complex geographic filters)
        if rule['filter'] is None:
            mask = results_df['current_zoning'] == from_zone
            results_df.loc[mask, 'rezoned'] = True
            results_df.loc[mask, 'target_zoning'] = to_zone
    
    # Calculate appreciation rates
    for idx, row in results_df.iterrows():
        current_zone = row['current_zoning']
        target_zone = row['target_zoning']
        
        # Get current zone appreciation rate
        if current_zone in appreciation_lookup:
            current_rate = appreciation_lookup[current_zone]['annual_appreciation_pct']
            results_df.at[idx, 'current_annual_appreciation_pct'] = current_rate
        
        # Get target zone appreciation rate
        if target_zone in appreciation_lookup:
            target_rate = appreciation_lookup[target_zone]['annual_appreciation_pct']
            results_df.at[idx, 'target_annual_appreciation_pct'] = target_rate
        
        # Calculate differential (additional appreciation from rezoning)
        if row['rezoned']:
            diff = target_rate - current_rate if current_zone in appreciation_lookup else 0
            results_df.at[idx, 'differential_appreciation_pct'] = diff
    
    # Calculate projected values
    results_df['baseline_future_value'] = (
        results_df['estimated_market_value'] * 
        (1 + results_df['current_annual_appreciation_pct'] / 100) ** time_horizon_years
    )
    
    results_df['rezoned_future_value'] = results_df.apply(
        lambda row: (
            row['estimated_market_value'] * 
            (1 + row['target_annual_appreciation_pct'] / 100) ** time_horizon_years
            if row['rezoned']
            else row['baseline_future_value']
        ),
        axis=1
    )
    
    results_df['value_uplift'] = results_df['rezoned_future_value'] - results_df['baseline_future_value']
    results_df['value_uplift_pct'] = (
        (results_df['value_uplift'] / results_df['baseline_future_value'] * 100)
        .fillna(0)
    )
    
    # Calculate property tax impacts
    results_df['baseline_annual_tax'] = results_df['baseline_future_value'] * PROPERTY_TAX_RATE
    results_df['rezoned_annual_tax'] = results_df['rezoned_future_value'] * PROPERTY_TAX_RATE
    results_df['annual_tax_increase'] = results_df['rezoned_annual_tax'] - results_df['baseline_annual_tax']
    
    return results_df


def analyze_scenario(results_df, scenario_name):
    """Analyze and summarize a scenario's results."""
    rezoned_parcels = results_df[results_df['rezoned']]
    
    if len(rezoned_parcels) == 0:
        return {
            'scenario_name': scenario_name,
            'parcels_rezoned': 0,
            'error': 'No parcels matched rezoning rules'
        }
    
    summary = {
        'scenario_name': scenario_name,
        'parcels_rezoned': len(rezoned_parcels),
        'total_current_value': results_df['estimated_market_value'].sum(),
        'total_baseline_future_value': results_df['baseline_future_value'].sum(),
        'total_rezoned_future_value': results_df['rezoned_future_value'].sum(),
        'total_value_uplift': rezoned_parcels['value_uplift'].sum(),
        'avg_uplift_per_parcel': rezoned_parcels['value_uplift'].mean(),
        'median_uplift_per_parcel': rezoned_parcels['value_uplift'].median(),
        'total_annual_tax_increase': rezoned_parcels['annual_tax_increase'].sum(),
        'avg_differential_appreciation_pct': rezoned_parcels['differential_appreciation_pct'].mean()
    }
    
    return summary


def run_all_scenarios(parcels_df, appreciation_lookup, time_horizon=10):
    """Run all defined scenarios and compile results."""
    print("\n" + "=" * 80)
    print("RUNNING REZONING SCENARIOS")
    print("=" * 80)
    print(f"Time Horizon: {time_horizon} years\n")
    
    scenarios = define_rezoning_scenarios()
    all_results = []
    scenario_details = {}
    
    for scenario_id, scenario in scenarios.items():
        print(f"\n--- {scenario['name']} ---")
        print(f"    {scenario['description']}")
        
        results_df = apply_scenario(parcels_df, scenario, appreciation_lookup, time_horizon)
        summary = analyze_scenario(results_df, scenario['name'])
        
        if 'error' in summary:
            print(f"    ⚠ {summary['error']}")
        else:
            print(f"    Parcels affected: {summary['parcels_rezoned']}")
            print(f"    Total value uplift: ${summary['total_value_uplift']:,.0f}")
            print(f"    Avg uplift per parcel: ${summary['avg_uplift_per_parcel']:,.0f}")
            print(f"    Annual tax increase: ${summary['total_annual_tax_increase']:,.0f}")
        
        all_results.append(summary)
        scenario_details[scenario_id] = results_df
    
    return pd.DataFrame(all_results), scenario_details


def save_results(summary_df, scenario_details, time_horizon):
    """Save scenario results to files."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    print("\n" + "=" * 80)
    print("SAVING RESULTS")
    print("=" * 80)
    
    # Save summary
    summary_df.to_csv(SCENARIO_RESULTS_FILE, index=False)
    print(f"Saved scenario summary: {SCENARIO_RESULTS_FILE}")
    
    # Save detailed results for each scenario
    for scenario_id, results_df in scenario_details.items():
        filename = OUTPUT_DIR / f"scenario_{scenario_id}_details.csv"
        results_df.to_csv(filename, index=False)
        print(f"Saved detailed results: {filename}")
    
    # Create summary report
    with open(SUMMARY_REPORT_FILE, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("REZONING SCENARIO IMPACT ANALYSIS\n")
        f.write("Plan for Chicago 2030\n")
        f.write("=" * 80 + "\n")
        f.write(f"Time Horizon: {time_horizon} years\n")
        f.write(f"Property Tax Rate: {PROPERTY_TAX_RATE * 100}%\n")
        f.write(f"Assessment Ratio: {ASSESSMENT_RATIO * 100}%\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("SCENARIO RESULTS\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(summary_df.to_string(index=False))
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("KEY FINDINGS\n")
        f.write("=" * 80 + "\n\n")
        
        # Best scenario by total uplift
        best_uplift = summary_df.loc[summary_df['total_value_uplift'].idxmax()]
        f.write(f"Highest Total Value Uplift:\n")
        f.write(f"  Scenario: {best_uplift['scenario_name']}\n")
        f.write(f"  Total Uplift: ${best_uplift['total_value_uplift']:,.0f}\n")
        f.write(f"  Parcels Affected: {best_uplift['parcels_rezoned']}\n")
        f.write(f"  Annual Tax Increase: ${best_uplift['total_annual_tax_increase']:,.0f}\n")
        
        f.write("\n")
        
        # Best scenario by per-parcel uplift
        best_per_parcel = summary_df.loc[summary_df['avg_uplift_per_parcel'].idxmax()]
        f.write(f"Highest Average Per-Parcel Uplift:\n")
        f.write(f"  Scenario: {best_per_parcel['scenario_name']}\n")
        f.write(f"  Avg Uplift: ${best_per_parcel['avg_uplift_per_parcel']:,.0f}\n")
        f.write(f"  Parcels Affected: {best_per_parcel['parcels_rezoned']}\n")
    
    print(f"Saved summary report: {SUMMARY_REPORT_FILE}")


def main():
    """Main execution function."""
    # Load data
    parcels_df, appreciation_df = load_data()
    if parcels_df is None or appreciation_df is None:
        return
    
    # Prepare parcels
    parcels_df = prepare_parcels(parcels_df)
    if parcels_df is None:
        return
    
    # Create appreciation lookup
    appreciation_lookup = create_appreciation_lookup(appreciation_df)
    print(f"\nAppreciation rates loaded for {len(appreciation_lookup)} zoning types")
    
    # Run scenarios
    TIME_HORIZON = 10  # Years
    summary_df, scenario_details = run_all_scenarios(parcels_df, appreciation_lookup, TIME_HORIZON)
    
    # Save results
    save_results(summary_df, scenario_details, TIME_HORIZON)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nReview results in: {OUTPUT_DIR.absolute()}")
    print("\nNext steps:")
    print("1. Review scenario_results.csv for summary metrics")
    print("2. Examine detailed scenario files for parcel-level analysis")
    print("3. Adjust rezoning rules in define_rezoning_scenarios() as needed")
    print("4. Re-run with different time horizons or scenarios")
    print("=" * 80)


if __name__ == "__main__":
    main()

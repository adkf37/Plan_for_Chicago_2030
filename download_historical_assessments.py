"""
Download Historical Property Assessment Data
============================================
Downloads multi-year Cook County assessment data for parcels in the study area,
then analyzes property value appreciation rates by current zoning category.

This provides empirical data on how different zoning types appreciate over time,
which can improve rezoning uplift models.
"""

import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path
import time
from datetime import datetime

# --- Configuration ---
ASSESSMENT_API_URL = "https://datacatalog.cookcountyil.gov/resource/uzyt-m557.json"
APP_TOKEN = "ApE4oAonZT2D1PEE5ZY8xgs6M"
LIMIT = 50000  # Records per API call

# Years to download (adjust as needed)
YEARS_TO_DOWNLOAD = [2000, 2005, 2010, 2015, 2020, 2023, 2024, 2025]

# Input: Current parcels with zoning
PARCELS_WITH_ZONING = "parcels_in_area.csv"  # Your existing file with PIN and current zoning

# Output files
OUTPUT_DIR = Path("historical_data")
HISTORICAL_ASSESSMENTS_FILE = OUTPUT_DIR / "historical_assessments.csv"
APPRECIATION_BY_ZONING_FILE = OUTPUT_DIR / "appreciation_by_zoning.csv"
APPRECIATION_SUMMARY_FILE = OUTPUT_DIR / "appreciation_summary.txt"


def create_output_dir():
    """Create output directory if it doesn't exist."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR.absolute()}")


def load_parcel_pins():
    """Load the list of PINs from your existing parcels file."""
    try:
        df = pd.read_csv(PARCELS_WITH_ZONING)
        pins = df['pin'].unique().tolist()
        print(f"Loaded {len(pins)} unique PINs from {PARCELS_WITH_ZONING}")
        return pins, df
    except FileNotFoundError:
        print(f"ERROR: Could not find {PARCELS_WITH_ZONING}")
        print("Please ensure this file exists with a 'pin' column.")
        return None, None


def download_assessments_for_year(year, pins):
    """
    Download assessment data for a specific year for the given PINs.
    Uses batching to handle API limits.
    """
    print(f"\n--- Downloading assessment data for year {year} ---")
    
    # Convert pins to strings for API query
    pin_strings = [str(pin) for pin in pins]
    
    all_records = []
    batch_size = 100  # Number of PINs per API call
    
    for i in range(0, len(pin_strings), batch_size):
        batch = pin_strings[i:i + batch_size]
        
        # Construct SoQL WHERE clause: year = '2020' AND pin IN ('123...', '456...')
        pin_list = "','".join(batch)
        where_clause = f"year='{year}' AND pin IN ('{pin_list}')"
        
        # Make API request
        headers = {'X-App-Token': APP_TOKEN}
        params = {
            '$where': where_clause,
            '$limit': LIMIT
        }
        
        try:
            response = requests.get(ASSESSMENT_API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data:
                all_records.extend(data)
                print(f"  Batch {i//batch_size + 1}/{(len(pin_strings)-1)//batch_size + 1}: Retrieved {len(data)} records")
            
            # Be nice to the API
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            print(f"  ERROR retrieving batch {i//batch_size + 1}: {e}")
            continue
    
    if all_records:
        df = pd.DataFrame(all_records)
        print(f"Total records for {year}: {len(df)}")
        return df
    else:
        print(f"No data retrieved for year {year}")
        return None


def download_all_years(pins):
    """Download assessment data for all specified years."""
    all_data = []
    
    for year in YEARS_TO_DOWNLOAD:
        df = download_assessments_for_year(year, pins)
        if df is not None:
            all_data.append(df)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        print(f"\n=== Total records across all years: {len(combined)} ===")
        return combined
    else:
        print("\nERROR: No data downloaded for any year")
        return None


def clean_assessment_data(df):
    """Clean and prepare assessment data for analysis."""
    print("\n--- Cleaning assessment data ---")
    
    # Convert numeric columns
    numeric_cols = ['certified_tot', 'certified_bldg', 'certified_land', 'year']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop records with missing or zero assessed values
    initial_count = len(df)
    df = df[df['certified_tot'].notna() & (df['certified_tot'] > 0)]
    print(f"Dropped {initial_count - len(df)} records with missing/zero values")
    
    # Sort by PIN and year
    df = df.sort_values(['pin', 'year'])
    
    print(f"Clean records: {len(df)}")
    return df


def match_with_zoning(historical_df, parcels_df):
    """
    Match historical assessment data with current zoning information.
    Assumes parcels_df has 'pin' and zoning-related columns.
    """
    print("\n--- Matching with current zoning data ---")
    
    # Determine zoning column name
    zoning_cols = [col for col in parcels_df.columns if 'zone' in col.lower() or 'class' in col.lower()]
    if not zoning_cols:
        print("WARNING: No zoning column found. Using 'class' if available.")
        if 'class' in parcels_df.columns:
            zoning_col = 'class'
        else:
            print("ERROR: Cannot find zoning information in parcels file")
            return None
    else:
        zoning_col = zoning_cols[0]
        print(f"Using zoning column: {zoning_col}")
    
    # Create lookup of PIN -> current zoning
    zoning_lookup = parcels_df[['pin', zoning_col]].drop_duplicates()
    zoning_lookup.columns = ['pin', 'current_zoning']
    
    # Merge
    merged = historical_df.merge(zoning_lookup, on='pin', how='left')
    
    print(f"Matched {merged['current_zoning'].notna().sum()} records with zoning data")
    print(f"Unmatched records: {merged['current_zoning'].isna().sum()}")
    
    return merged


def calculate_appreciation_rates(df):
    """
    Calculate appreciation rates by current zoning category.
    
    For each zoning type:
    - Calculate average annual appreciation rate
    - Calculate total appreciation from earliest to latest year
    - Count number of parcels
    """
    print("\n--- Calculating appreciation rates by zoning ---")
    
    results = []
    
    for zoning in df['current_zoning'].dropna().unique():
        zone_data = df[df['current_zoning'] == zoning].copy()
        
        # Get earliest and latest years with data
        years = sorted(zone_data['year'].unique())
        if len(years) < 2:
            continue  # Need at least 2 years to calculate appreciation
        
        earliest_year = years[0]
        latest_year = years[-1]
        
        # Calculate appreciation for parcels with data in both years
        early_values = zone_data[zone_data['year'] == earliest_year][['pin', 'certified_tot']]
        late_values = zone_data[zone_data['year'] == latest_year][['pin', 'certified_tot']]
        
        matched = early_values.merge(late_values, on='pin', suffixes=('_early', '_late'))
        
        if len(matched) == 0:
            continue
        
        # Calculate appreciation
        matched['appreciation_pct'] = ((matched['certified_tot_late'] - matched['certified_tot_early']) 
                                       / matched['certified_tot_early'] * 100)
        matched['years_elapsed'] = latest_year - earliest_year
        matched['annual_appreciation_pct'] = matched['appreciation_pct'] / matched['years_elapsed']
        
        # Summary statistics
        avg_total_appreciation = matched['appreciation_pct'].mean()
        median_total_appreciation = matched['appreciation_pct'].median()
        avg_annual_appreciation = matched['annual_appreciation_pct'].mean()
        median_annual_appreciation = matched['annual_appreciation_pct'].median()
        parcel_count = len(matched)
        
        results.append({
            'zoning_type': zoning,
            'parcel_count': parcel_count,
            'earliest_year': earliest_year,
            'latest_year': latest_year,
            'years_elapsed': latest_year - earliest_year,
            'avg_total_appreciation_pct': avg_total_appreciation,
            'median_total_appreciation_pct': median_total_appreciation,
            'avg_annual_appreciation_pct': avg_annual_appreciation,
            'median_annual_appreciation_pct': median_annual_appreciation,
            'avg_early_value': matched['certified_tot_early'].mean(),
            'avg_late_value': matched['certified_tot_late'].mean()
        })
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('avg_annual_appreciation_pct', ascending=False)
    
    return results_df


def save_results(historical_df, appreciation_df):
    """Save results to files."""
    print("\n--- Saving results ---")
    
    # Save historical data
    historical_df.to_csv(HISTORICAL_ASSESSMENTS_FILE, index=False)
    print(f"Saved historical assessments: {HISTORICAL_ASSESSMENTS_FILE}")
    
    # Save appreciation analysis
    appreciation_df.to_csv(APPRECIATION_BY_ZONING_FILE, index=False)
    print(f"Saved appreciation by zoning: {APPRECIATION_BY_ZONING_FILE}")
    
    # Create summary report
    with open(APPRECIATION_SUMMARY_FILE, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("PROPERTY VALUE APPRECIATION BY CURRENT ZONING TYPE\n")
        f.write("=" * 80 + "\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Years Analyzed: {YEARS_TO_DOWNLOAD}\n")
        f.write(f"Total Parcels: {len(historical_df['pin'].unique())}\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("APPRECIATION RATES BY ZONING TYPE\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(appreciation_df.to_string(index=False))
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("KEY INSIGHTS\n")
        f.write("=" * 80 + "\n\n")
        
        # Top appreciating zones
        top_zones = appreciation_df.nlargest(5, 'avg_annual_appreciation_pct')
        f.write("Top 5 Highest Annual Appreciation Zones:\n")
        for _, row in top_zones.iterrows():
            f.write(f"  {row['zoning_type']}: {row['avg_annual_appreciation_pct']:.2f}% per year "
                   f"({row['parcel_count']} parcels)\n")
        
        f.write("\n")
        
        # Bottom appreciating zones
        bottom_zones = appreciation_df.nsmallest(5, 'avg_annual_appreciation_pct')
        f.write("Bottom 5 Lowest Annual Appreciation Zones:\n")
        for _, row in bottom_zones.iterrows():
            f.write(f"  {row['zoning_type']}: {row['avg_annual_appreciation_pct']:.2f}% per year "
                   f"({row['parcel_count']} parcels)\n")
    
    print(f"Saved summary report: {APPRECIATION_SUMMARY_FILE}")


def print_summary(appreciation_df):
    """Print summary to console."""
    print("\n" + "=" * 80)
    print("APPRECIATION ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nAnalyzed {len(appreciation_df)} zoning types")
    print(f"\nAverage annual appreciation across all zones: "
          f"{appreciation_df['avg_annual_appreciation_pct'].mean():.2f}%")
    print(f"\nTop 3 highest appreciating zones:")
    for _, row in appreciation_df.head(3).iterrows():
        print(f"  {row['zoning_type']}: {row['avg_annual_appreciation_pct']:.2f}% per year")
    print("\n" + "=" * 80)


def main():
    """Main execution function."""
    print("=" * 80)
    print("HISTORICAL PROPERTY ASSESSMENT DOWNLOAD & ANALYSIS")
    print("=" * 80)
    
    # Setup
    create_output_dir()
    
    # Load existing parcels
    pins, parcels_df = load_parcel_pins()
    if pins is None:
        return
    
    # Download historical data
    historical_df = download_all_years(pins)
    if historical_df is None:
        return
    
    # Clean data
    historical_df = clean_assessment_data(historical_df)
    
    # Match with zoning
    historical_df = match_with_zoning(historical_df, parcels_df)
    if historical_df is None:
        return
    
    # Calculate appreciation rates
    appreciation_df = calculate_appreciation_rates(historical_df)
    
    # Save results
    save_results(historical_df, appreciation_df)
    
    # Print summary
    print_summary(appreciation_df)
    
    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Review the appreciation rates in: historical_data/appreciation_by_zoning.csv")
    print("2. Use these rates to refine your rezoning uplift models")
    print("3. Consider running improved_uplift_model.py (to be created) for scenario analysis")
    print("=" * 80)


if __name__ == "__main__":
    main()

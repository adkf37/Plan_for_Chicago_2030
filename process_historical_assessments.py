"""
Process Historical Assessment Data for Uplift Modeling

This script processes the downloaded historical Cook County assessment data
to calculate annual appreciation rates by current zoning type.

Input:
- Historical assessment data CSV (1999-present)
- Current assessment data CSV

Output:
- historical_appreciation_by_zoning.csv: Annual appreciation rates by zoning
- parcel_appreciation_summary.csv: Per-parcel appreciation statistics
- appreciation_analysis_summary.txt: Overall statistics and insights
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
import json
from datetime import datetime

# Configuration
HISTORICAL_DATA_PATH = r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030\historical_data\Assessor_-_Assessed_Values_since_1999_20251004.csv"
CURRENT_DATA_PATH = r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030\Assessor_-_Assessed_Values_20250430.csv"
OUTPUT_DIR = Path(r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030\analysis_results")

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)

def clean_currency(value):
    """Convert currency string to float."""
    if pd.isna(value) or value == '':
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    # Remove $, commas, and convert to float
    return float(str(value).replace('$', '').replace(',', ''))

def load_historical_data(chunk_size=100000):
    """
    Load historical assessment data in chunks to handle large file.
    Focus on certified_tot as the primary valuation metric.
    """
    print(f"Loading historical data from: {HISTORICAL_DATA_PATH}")
    print("This may take several minutes due to file size (~7.8GB)...")
    
    columns_to_use = ['pin', 'tax_year', 'class', 'certified_tot']
    
    chunks = []
    total_rows = 0
    
    for i, chunk in enumerate(pd.read_csv(HISTORICAL_DATA_PATH, 
                                          usecols=columns_to_use,
                                          dtype={'pin': str},
                                          chunksize=chunk_size,
                                          low_memory=False)):
        total_rows += len(chunk)
        
        # Clean the certified_tot column
        chunk['certified_tot'] = chunk['certified_tot'].apply(clean_currency)
        
        # Remove rows with missing values
        chunk = chunk.dropna(subset=['pin', 'tax_year', 'certified_tot'])
        
        # Filter to reasonable property classes (residential, commercial, industrial)
        # Class codes: 200s = residential, 500s = commercial, 300s = industrial
        chunk = chunk[chunk['class'].astype(str).str[0].isin(['2', '3', '5'])]
        
        chunks.append(chunk)
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {total_rows:,} rows...")
    
    print(f"Total rows processed: {total_rows:,}")
    
    historical_df = pd.concat(chunks, ignore_index=True)
    
    print(f"After filtering: {len(historical_df):,} valid records")
    print(f"Years covered: {historical_df['tax_year'].min()} - {historical_df['tax_year'].max()}")
    print(f"Unique PINs: {historical_df['pin'].nunique():,}")
    
    return historical_df

def load_current_data_with_zoning():
    """Load current assessment data and assign zoning based on property class."""
    print(f"\nLoading current assessment data: {CURRENT_DATA_PATH}")
    
    current_df = pd.read_csv(CURRENT_DATA_PATH, dtype={'pin': str, 'class': str})
    
    # Clean currency columns
    for col in ['certified_bldg', 'certified_land', 'certified_tot']:
        if col in current_df.columns:
            current_df[col] = current_df[col].apply(clean_currency)
    
    print(f"Current data: {len(current_df):,} properties")
    
    # Assign zoning based on property class as a proxy
    # This is appropriate since property class strongly correlates with land use
    def assign_proxy_zoning(property_class):
        """Assign zoning based on property class code."""
        if pd.isna(property_class):
            return 'Unknown'
        
        class_str = str(property_class)
        
        # Residential classes (200s)
        if class_str.startswith('2'):
            if class_str in ['203', '204', '205', '206', '207', '208', '209']:
                return 'RS'  # Residential Single-Family
            elif class_str in ['211', '212']:
                return 'RT'  # Residential Two-Flat
            else:
                return 'RM'  # Residential Multi-Family
        
        # Commercial classes (500s)
        elif class_str.startswith('5'):
            if class_str in ['591', '592']:
                return 'C'  # Commercial
            else:
                return 'B'  # Business
        
        # Industrial classes (300s)
        elif class_str.startswith('3'):
            return 'M'  # Manufacturing
        
        return 'Unknown'
    
    current_df['zoning_type'] = current_df['class'].apply(assign_proxy_zoning)
    
    print(f"\nZoning type distribution:")
    print(current_df['zoning_type'].value_counts())
    
    return current_df[['pin', 'zoning_type', 'certified_tot']]

def calculate_appreciation_rates(historical_df, current_df):
    """
    Calculate annual appreciation rates by zoning type.
    """
    print("\n" + "="*60)
    print("CALCULATING APPRECIATION RATES BY ZONING TYPE")
    print("="*60)
    
    # Merge current zoning with historical data
    print("\nMerging historical data with current zoning...")
    merged_df = historical_df.merge(current_df[['pin', 'zoning_type']], on='pin', how='inner')
    
    print(f"Matched records: {len(merged_df):,}")
    print(f"Unique PINs with zoning: {merged_df['pin'].nunique():,}")
    
    # Calculate year-over-year changes for each parcel
    print("\nCalculating year-over-year appreciation rates...")
    
    # Sort by PIN and year
    merged_df = merged_df.sort_values(['pin', 'tax_year'])
    
    # Calculate YoY change for each parcel
    merged_df['prev_year_value'] = merged_df.groupby('pin')['certified_tot'].shift(1)
    merged_df['yoy_change'] = (merged_df['certified_tot'] - merged_df['prev_year_value']) / merged_df['prev_year_value']
    
    # Remove infinite and extreme outliers (more than 500% or less than -90%)
    merged_df = merged_df[(merged_df['yoy_change'] > -0.9) & (merged_df['yoy_change'] < 5.0)]
    
    # Calculate statistics by zoning type and year
    appreciation_by_zone_year = merged_df.groupby(['zoning_type', 'tax_year']).agg({
        'yoy_change': ['mean', 'median', 'std', 'count']
    }).reset_index()
    
    appreciation_by_zone_year.columns = ['zoning_type', 'tax_year', 'mean_appreciation', 
                                          'median_appreciation', 'std_appreciation', 'sample_size']
    
    # Calculate overall statistics by zoning type
    appreciation_by_zone = merged_df.groupby('zoning_type').agg({
        'yoy_change': ['mean', 'median', 'std', 'count']
    }).reset_index()
    
    appreciation_by_zone.columns = ['zoning_type', 'avg_annual_appreciation', 
                                     'median_annual_appreciation', 'std_appreciation', 'total_observations']
    
    # Calculate per-parcel statistics
    parcel_stats = merged_df.groupby(['pin', 'zoning_type']).agg({
        'yoy_change': ['mean', 'median', 'std', 'count'],
        'certified_tot': ['first', 'last']
    }).reset_index()
    
    parcel_stats.columns = ['pin', 'zoning_type', 'avg_appreciation', 'median_appreciation', 
                            'std_appreciation', 'years_observed', 'first_value', 'last_value']
    
    parcel_stats['total_appreciation'] = (parcel_stats['last_value'] - parcel_stats['first_value']) / parcel_stats['first_value']
    
    return appreciation_by_zone, appreciation_by_zone_year, parcel_stats

def save_results(appreciation_by_zone, appreciation_by_zone_year, parcel_stats):
    """Save analysis results to files."""
    print("\n" + "="*60)
    print("SAVING RESULTS")
    print("="*60)
    
    # Save appreciation by zone (summary)
    output_file = OUTPUT_DIR / "historical_appreciation_by_zoning.csv"
    appreciation_by_zone.to_csv(output_file, index=False)
    print(f"\n✓ Saved: {output_file}")
    
    # Save appreciation by zone and year (time series)
    output_file = OUTPUT_DIR / "appreciation_by_zone_year.csv"
    appreciation_by_zone_year.to_csv(output_file, index=False)
    print(f"✓ Saved: {output_file}")
    
    # Save parcel-level statistics
    output_file = OUTPUT_DIR / "parcel_appreciation_summary.csv"
    parcel_stats.to_csv(output_file, index=False)
    print(f"✓ Saved: {output_file}")
    
    # Create summary report
    summary_file = OUTPUT_DIR / "appreciation_analysis_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("HISTORICAL PROPERTY APPRECIATION ANALYSIS SUMMARY\n")
        f.write("="*70 + "\n\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("AVERAGE ANNUAL APPRECIATION RATES BY ZONING TYPE\n")
        f.write("-" * 70 + "\n\n")
        
        for _, row in appreciation_by_zone.sort_values('avg_annual_appreciation', ascending=False).iterrows():
            f.write(f"{row['zoning_type']:10s} | Avg: {row['avg_annual_appreciation']*100:6.2f}% | "
                   f"Median: {row['median_annual_appreciation']*100:6.2f}% | "
                   f"Observations: {row['total_observations']:,}\n")
        
        f.write("\n" + "="*70 + "\n")
        f.write("INTERPRETATION & USAGE\n")
        f.write("="*70 + "\n\n")
        f.write("These appreciation rates represent the average year-over-year change in\n")
        f.write("property assessed values for each zoning type, calculated from historical\n")
        f.write("Cook County assessment data (1999-present).\n\n")
        f.write("Use these rates in the improved_uplift_model.py script to estimate future\n")
        f.write("property values under different rezoning scenarios.\n\n")
        f.write("Note: Current zoning is used as a proxy. Parcels may have been rezoned\n")
        f.write("during the observation period, which could affect accuracy.\n")
    
    print(f"✓ Saved: {summary_file}")
    
    # Display summary
    print("\n" + "="*60)
    print("APPRECIATION RATE SUMMARY")
    print("="*60)
    print(appreciation_by_zone.to_string(index=False))

def main():
    """Main execution function."""
    print("="*70)
    print("HISTORICAL PROPERTY ASSESSMENT ANALYSIS")
    print("Processing Cook County Assessment Data (1999-Present)")
    print("="*70)
    print()
    
    try:
        # Step 1: Load historical data
        historical_df = load_historical_data()
        
        # Step 2: Load current data with zoning
        current_df = load_current_data_with_zoning()
        
        # Step 3: Calculate appreciation rates
        appreciation_by_zone, appreciation_by_zone_year, parcel_stats = calculate_appreciation_rates(
            historical_df, current_df
        )
        
        # Step 4: Save results
        save_results(appreciation_by_zone, appreciation_by_zone_year, parcel_stats)
        
        print("\n" + "="*70)
        print("✓ ANALYSIS COMPLETE!")
        print("="*70)
        print("\nNext steps:")
        print("1. Review the appreciation rates in: analysis_results/")
        print("2. Run improved_uplift_model.py to apply these rates to rezoning scenarios")
        print("3. Customize scenarios as needed for your analysis")
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())

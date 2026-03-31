"""
Process Historical Assessment Data for Uplift Modeling
======================================================
Processes the large historical Cook County assessment CSV (~7.8GB, 48.8M records)
in chunks to calculate annual appreciation rates by zoning type proxy.

Usage:
    python -m src.process_historical
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

from src.config import (
    RAW_HISTORICAL_CSV, RAW_ASSESSMENT_CSV,
    ANALYSIS_RESULTS_DIR, APPRECIATION_BY_ZONING_CSV, ensure_dirs,
)


def clean_currency(value):
    """Convert currency string to float."""
    if pd.isna(value) or value == "":
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace("$", "").replace(",", ""))


def load_historical_data(chunk_size=100000):
    """Load historical assessment data in chunks to handle the large file."""
    print(f"Loading historical data from: {RAW_HISTORICAL_CSV}")
    print("This may take several minutes due to file size (~7.8GB)...")

    columns_to_use = ["pin", "tax_year", "class", "certified_tot"]
    chunks = []
    total_rows = 0

    for i, chunk in enumerate(pd.read_csv(
        RAW_HISTORICAL_CSV,
        usecols=columns_to_use,
        dtype={"pin": str},
        chunksize=chunk_size,
        low_memory=False,
    )):
        total_rows += len(chunk)
        chunk["certified_tot"] = chunk["certified_tot"].apply(clean_currency)
        chunk = chunk.dropna(subset=["pin", "tax_year", "certified_tot"])
        # Filter to residential (2xx), industrial (3xx), commercial (5xx) classes
        chunk = chunk[chunk["class"].astype(str).str[0].isin(["2", "3", "5"])]
        chunks.append(chunk)
        if (i + 1) % 10 == 0:
            print(f"  Processed {total_rows:,} rows...")

    print(f"Total rows read: {total_rows:,}")
    historical_df = pd.concat(chunks, ignore_index=True)
    print(f"After filtering: {len(historical_df):,} valid records")
    print(f"Years: {historical_df['tax_year'].min()} - {historical_df['tax_year'].max()}")
    print(f"Unique PINs: {historical_df['pin'].nunique():,}")
    return historical_df


def load_current_data_with_zoning():
    """Load current assessment data and assign zoning proxy based on property class."""
    print(f"\nLoading current assessment data: {RAW_ASSESSMENT_CSV}")
    current_df = pd.read_csv(RAW_ASSESSMENT_CSV, dtype={"pin": str, "class": str})

    for col in ["certified_bldg", "certified_land", "certified_tot"]:
        if col in current_df.columns:
            current_df[col] = current_df[col].apply(clean_currency)

    print(f"Current data: {len(current_df):,} properties")

    def assign_proxy_zoning(property_class):
        if pd.isna(property_class):
            return "Unknown"
        cs = str(property_class)
        if cs.startswith("2"):
            if cs in ["203", "204", "205", "206", "207", "208", "209"]:
                return "RS"
            elif cs in ["211", "212"]:
                return "RT"
            return "RM"
        elif cs.startswith("5"):
            return "C" if cs in ["591", "592"] else "B"
        elif cs.startswith("3"):
            return "M"
        return "Unknown"

    current_df["zoning_type"] = current_df["class"].apply(assign_proxy_zoning)
    print(f"\nZoning type distribution:\n{current_df['zoning_type'].value_counts()}")
    return current_df[["pin", "zoning_type", "certified_tot"]]


def calculate_appreciation_rates(historical_df, current_df):
    """Calculate annual appreciation rates by zoning type."""
    print("\n" + "=" * 60)
    print("CALCULATING APPRECIATION RATES BY ZONING TYPE")
    print("=" * 60)

    merged_df = historical_df.merge(current_df[["pin", "zoning_type"]], on="pin", how="inner")
    print(f"Matched records: {len(merged_df):,}")

    merged_df = merged_df.sort_values(["pin", "tax_year"])
    merged_df["prev_year_value"] = merged_df.groupby("pin")["certified_tot"].shift(1)
    merged_df["yoy_change"] = (
        (merged_df["certified_tot"] - merged_df["prev_year_value"])
        / merged_df["prev_year_value"]
    )
    merged_df = merged_df[(merged_df["yoy_change"] > -0.9) & (merged_df["yoy_change"] < 5.0)]

    # By zone + year
    app_by_zone_year = merged_df.groupby(["zoning_type", "tax_year"]).agg(
        {"yoy_change": ["mean", "median", "std", "count"]}
    ).reset_index()
    app_by_zone_year.columns = [
        "zoning_type", "tax_year", "mean_appreciation",
        "median_appreciation", "std_appreciation", "sample_size",
    ]

    # By zone (overall)
    app_by_zone = merged_df.groupby("zoning_type").agg(
        {"yoy_change": ["mean", "median", "std", "count"]}
    ).reset_index()
    app_by_zone.columns = [
        "zoning_type", "avg_annual_appreciation",
        "median_annual_appreciation", "std_appreciation", "total_observations",
    ]

    # Per-parcel
    parcel_stats = merged_df.groupby(["pin", "zoning_type"]).agg(
        {"yoy_change": ["mean", "median", "std", "count"], "certified_tot": ["first", "last"]}
    ).reset_index()
    parcel_stats.columns = [
        "pin", "zoning_type", "avg_appreciation", "median_appreciation",
        "std_appreciation", "years_observed", "first_value", "last_value",
    ]
    parcel_stats["total_appreciation"] = (
        (parcel_stats["last_value"] - parcel_stats["first_value"])
        / parcel_stats["first_value"]
    )

    return app_by_zone, app_by_zone_year, parcel_stats


def save_results(app_by_zone, app_by_zone_year, parcel_stats):
    """Save analysis results."""
    ensure_dirs()

    (ANALYSIS_RESULTS_DIR / "historical_appreciation_by_zoning.csv").pipe(
        lambda p: app_by_zone.to_csv(p, index=False) or print(f"Saved: {p}")
    ) if False else None  # Use explicit saves:

    f1 = ANALYSIS_RESULTS_DIR / "historical_appreciation_by_zoning.csv"
    app_by_zone.to_csv(f1, index=False)
    print(f"Saved: {f1}")

    # Also save to data/processed/ for pipeline consumption
    APPRECIATION_BY_ZONING_CSV.parent.mkdir(parents=True, exist_ok=True)
    app_by_zone.to_csv(APPRECIATION_BY_ZONING_CSV, index=False)
    print(f"Saved: {APPRECIATION_BY_ZONING_CSV}")

    f2 = ANALYSIS_RESULTS_DIR / "appreciation_by_zone_year.csv"
    app_by_zone_year.to_csv(f2, index=False)
    print(f"Saved: {f2}")

    f3 = ANALYSIS_RESULTS_DIR / "parcel_appreciation_summary.csv"
    parcel_stats.to_csv(f3, index=False)
    print(f"Saved: {f3}")

    summary_file = ANALYSIS_RESULTS_DIR / "appreciation_analysis_summary.txt"
    with open(summary_file, "w") as f:
        f.write("=" * 70 + "\n")
        f.write("HISTORICAL PROPERTY APPRECIATION ANALYSIS SUMMARY\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("AVERAGE ANNUAL APPRECIATION RATES BY ZONING TYPE\n")
        f.write("-" * 70 + "\n\n")
        for _, row in app_by_zone.sort_values("avg_annual_appreciation", ascending=False).iterrows():
            f.write(
                f"{row['zoning_type']:10s} | Avg: {row['avg_annual_appreciation'] * 100:6.2f}% | "
                f"Median: {row['median_annual_appreciation'] * 100:6.2f}% | "
                f"Observations: {row['total_observations']:,}\n"
            )
    print(f"Saved: {summary_file}")


def main():
    print("=" * 70)
    print("HISTORICAL PROPERTY ASSESSMENT ANALYSIS")
    print("Processing Cook County Assessment Data (1999-Present)")
    print("=" * 70 + "\n")

    try:
        historical_df = load_historical_data()
        current_df = load_current_data_with_zoning()
        app_by_zone, app_by_zone_year, parcel_stats = calculate_appreciation_rates(
            historical_df, current_df
        )
        save_results(app_by_zone, app_by_zone_year, parcel_stats)
        print("\nANALYSIS COMPLETE — results in analysis_results/")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    exit(main())

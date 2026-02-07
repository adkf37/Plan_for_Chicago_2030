"""
Download Historical Property Assessment Data
=============================================
Downloads multi-year Cook County assessment data for parcels in the study area
via the Socrata API, then analyzes property value appreciation rates by
current zoning category.

Usage:
    python -m src.download_historical
"""

import requests
import pandas as pd
from pathlib import Path
import time
from datetime import datetime

from src.config import (
    ASSESSMENT_JSON_URL, SOCRATA_APP_TOKEN, SOCRATA_LIMIT,
    PARCELS_IN_AREA_CSV, HISTORICAL_DATA_DIR, HISTORICAL_YEARS,
    ensure_dirs,
)


def load_parcel_pins():
    """Load the list of PINs from the parcels-in-area file."""
    try:
        df = pd.read_csv(PARCELS_IN_AREA_CSV)
        pins = df["pin"].unique().tolist()
        print(f"Loaded {len(pins)} unique PINs from {PARCELS_IN_AREA_CSV}")
        return pins, df
    except FileNotFoundError:
        print(f"ERROR: Could not find {PARCELS_IN_AREA_CSV}")
        print("Run 'python -m src.analyze_area' first.")
        return None, None


def download_assessments_for_year(year, pins):
    """Download assessment data for a specific year for the given PINs."""
    print(f"\n--- Downloading assessment data for year {year} ---")
    pin_strings = [str(pin) for pin in pins]
    all_records = []
    batch_size = 100

    for i in range(0, len(pin_strings), batch_size):
        batch = pin_strings[i : i + batch_size]
        pin_list = "','".join(batch)
        where_clause = f"year='{year}' AND pin IN ('{pin_list}')"

        headers = {"X-App-Token": SOCRATA_APP_TOKEN} if SOCRATA_APP_TOKEN else {}
        params = {"$where": where_clause, "$limit": SOCRATA_LIMIT}

        try:
            response = requests.get(ASSESSMENT_JSON_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            if data:
                all_records.extend(data)
                print(f"  Batch {i // batch_size + 1}/{(len(pin_strings) - 1) // batch_size + 1}: {len(data)} records")
            time.sleep(0.1)
        except requests.exceptions.RequestException as e:
            print(f"  ERROR batch {i // batch_size + 1}: {e}")
            continue

    if all_records:
        df = pd.DataFrame(all_records)
        print(f"Total records for {year}: {len(df)}")
        return df
    print(f"No data retrieved for year {year}")
    return None


def download_all_years(pins):
    """Download assessment data for all configured years."""
    all_data = []
    for year in HISTORICAL_YEARS:
        df = download_assessments_for_year(year, pins)
        if df is not None:
            all_data.append(df)
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        print(f"\n=== Total records across all years: {len(combined)} ===")
        return combined
    print("\nERROR: No data downloaded for any year")
    return None


def clean_assessment_data(df):
    """Clean and prepare assessment data for analysis."""
    print("\n--- Cleaning assessment data ---")
    numeric_cols = ["certified_tot", "certified_bldg", "certified_land", "year"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    initial = len(df)
    df = df[df["certified_tot"].notna() & (df["certified_tot"] > 0)]
    print(f"Dropped {initial - len(df)} missing/zero records. Clean: {len(df)}")
    return df.sort_values(["pin", "year"])


def match_with_zoning(historical_df, parcels_df):
    """Match historical assessments with current zoning proxy."""
    print("\n--- Matching with current zoning data ---")
    zoning_col = "class" if "class" in parcels_df.columns else None
    if not zoning_col:
        zoning_cols = [c for c in parcels_df.columns if "zone" in c.lower() or "class" in c.lower()]
        zoning_col = zoning_cols[0] if zoning_cols else None
    if not zoning_col:
        print("ERROR: No zoning column found in parcels file")
        return None

    lookup = parcels_df[["pin", zoning_col]].drop_duplicates()
    lookup.columns = ["pin", "current_zoning"]
    merged = historical_df.merge(lookup, on="pin", how="left")
    print(f"Matched {merged['current_zoning'].notna().sum()} / {len(merged)} records")
    return merged


def calculate_appreciation_rates(df):
    """Calculate appreciation rates by current zoning category."""
    print("\n--- Calculating appreciation rates ---")
    results = []
    for zoning in df["current_zoning"].dropna().unique():
        zone_data = df[df["current_zoning"] == zoning]
        years = sorted(zone_data["year"].unique())
        if len(years) < 2:
            continue
        early = zone_data[zone_data["year"] == years[0]][["pin", "certified_tot"]]
        late = zone_data[zone_data["year"] == years[-1]][["pin", "certified_tot"]]
        matched = early.merge(late, on="pin", suffixes=("_early", "_late"))
        if len(matched) == 0:
            continue
        matched["appreciation_pct"] = (
            (matched["certified_tot_late"] - matched["certified_tot_early"])
            / matched["certified_tot_early"]
            * 100
        )
        elapsed = years[-1] - years[0]
        matched["annual_appreciation_pct"] = matched["appreciation_pct"] / elapsed
        results.append({
            "zoning_type": zoning,
            "parcel_count": len(matched),
            "earliest_year": years[0],
            "latest_year": years[-1],
            "years_elapsed": elapsed,
            "avg_total_appreciation_pct": matched["appreciation_pct"].mean(),
            "median_total_appreciation_pct": matched["appreciation_pct"].median(),
            "avg_annual_appreciation_pct": matched["annual_appreciation_pct"].mean(),
            "median_annual_appreciation_pct": matched["annual_appreciation_pct"].median(),
            "avg_early_value": matched["certified_tot_early"].mean(),
            "avg_late_value": matched["certified_tot_late"].mean(),
        })
    return pd.DataFrame(results).sort_values("avg_annual_appreciation_pct", ascending=False)


def save_results(historical_df, appreciation_df):
    """Save historical assessments and appreciation analysis."""
    ensure_dirs()
    hist_file = HISTORICAL_DATA_DIR / "historical_assessments.csv"
    historical_df.to_csv(hist_file, index=False)
    print(f"Saved: {hist_file}")

    app_file = HISTORICAL_DATA_DIR / "appreciation_by_zoning.csv"
    appreciation_df.to_csv(app_file, index=False)
    print(f"Saved: {app_file}")

    summary_file = HISTORICAL_DATA_DIR / "appreciation_summary.txt"
    with open(summary_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("PROPERTY VALUE APPRECIATION BY CURRENT ZONING TYPE\n")
        f.write("=" * 80 + "\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Years Analyzed: {HISTORICAL_YEARS}\n\n")
        f.write(appreciation_df.to_string(index=False))
    print(f"Saved: {summary_file}")


def main():
    print("=" * 80)
    print("HISTORICAL PROPERTY ASSESSMENT DOWNLOAD & ANALYSIS")
    print("=" * 80)

    ensure_dirs()
    pins, parcels_df = load_parcel_pins()
    if pins is None:
        return

    historical_df = download_all_years(pins)
    if historical_df is None:
        return

    historical_df = clean_assessment_data(historical_df)
    historical_df = match_with_zoning(historical_df, parcels_df)
    if historical_df is None:
        return

    appreciation_df = calculate_appreciation_rates(historical_df)
    save_results(historical_df, appreciation_df)

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("1. Review: data/processed/historical_data/appreciation_by_zoning.csv")
    print("2. Run: python -m src.improved_uplift_model")
    print("=" * 80)


if __name__ == "__main__":
    main()

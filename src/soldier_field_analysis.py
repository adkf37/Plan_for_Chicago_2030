"""
Soldier Field Tear-Down Analysis
=================================
Demonstrates the fiscal value of replacing Soldier Field and its south
parking lots with a mixed-use neighborhood by:

  1. Loading real Cook County parcel + assessment data.
  2. Computing aggregate property value for a reference neighborhood
     (Roosevelt / Indiana / Cermak / Clark) — an existing mixed-use area
     with a similar street-grid pattern.
  3. Deriving value-per-acre density from that reference area.
  4. Projecting what the Soldier Field footprint would generate in
     property value and annual tax revenue if developed at the same density.

The idea is simple: we are not designing a bespoke neighborhood — just
extending Chicago's street grid over the stadium and parking lots and
assuming the resulting development matches the existing reference area.

Usage:
    python -m src.soldier_field_analysis
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from src.config import (
    RAW_ASSESSMENT_CSV,
    RAW_PARCEL_UNIVERSE_CSV,
    ASSESSMENT_RATIO,
    PROPERTY_TAX_RATE,
    REFERENCE_AREA,
    SOLDIER_FIELD_AREA,
    ANALYSIS_RESULTS_DIR,
    ensure_dirs,
)

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def bbox_area_acres(bbox: dict) -> float:
    """
    Approximate area of a lat/lon bounding box in acres.

    Uses the WGS-84 approximation:
        1° latitude  ≈ 111,320 m
        1° longitude ≈ 111,320 m × cos(latitude)
    """
    mid_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    lat_m = (bbox["max_lat"] - bbox["min_lat"]) * 111_320
    lon_m = (bbox["max_lon"] - bbox["min_lon"]) * 111_320 * math.cos(math.radians(mid_lat))
    sq_m = lat_m * lon_m
    return sq_m / 4_046.86  # 1 acre = 4,046.86 m²


def filter_to_bbox(df: pd.DataFrame, bbox: dict) -> pd.DataFrame:
    """Return rows whose (latitude, longitude) falls inside *bbox*."""
    return df[
        (df["latitude"] >= bbox["min_lat"])
        & (df["latitude"] <= bbox["max_lat"])
        & (df["longitude"] >= bbox["min_lon"])
        & (df["longitude"] <= bbox["max_lon"])
    ].copy()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_parcels_and_assessments() -> pd.DataFrame:
    """
    Load parcel universe + assessment CSVs, merge on PIN, return one
    combined DataFrame with location and value columns.
    """
    print("Loading parcel universe …")
    parcels = pd.read_csv(
        RAW_PARCEL_UNIVERSE_CSV,
        usecols=["pin", "latitude", "longitude", "class"],
    )
    print(f"  {len(parcels):,} parcels")

    print("Loading assessment data …")
    assessments = pd.read_csv(
        RAW_ASSESSMENT_CSV,
        usecols=["pin", "tax_year", "certified_tot", "certified_bldg", "certified_land"],
    )
    print(f"  {len(assessments):,} assessment records")

    merged = parcels.merge(assessments, on="pin", how="left")
    print(f"  {len(merged):,} rows after merge")
    return merged


# ---------------------------------------------------------------------------
# Reference-area analysis
# ---------------------------------------------------------------------------

def analyze_reference_area(df: pd.DataFrame) -> dict:
    """
    Filter *df* to the reference neighborhood and compute aggregate
    property-value statistics.

    Returns a dict of summary metrics.
    """
    ref = filter_to_bbox(df, REFERENCE_AREA)
    ref = ref[ref["certified_tot"].notna() & (ref["certified_tot"] > 0)]

    area_acres = bbox_area_acres(REFERENCE_AREA)
    total_assessed = ref["certified_tot"].sum()
    total_market = total_assessed / ASSESSMENT_RATIO
    annual_tax = total_market * ASSESSMENT_RATIO * PROPERTY_TAX_RATE

    stats = {
        "parcels": len(ref),
        "area_acres": area_acres,
        "total_assessed_value": total_assessed,
        "total_market_value": total_market,
        "market_value_per_acre": total_market / area_acres if area_acres else 0,
        "assessed_value_per_acre": total_assessed / area_acres if area_acres else 0,
        "annual_property_tax": annual_tax,
        "annual_tax_per_acre": annual_tax / area_acres if area_acres else 0,
        "avg_market_value_per_parcel": total_market / len(ref) if len(ref) else 0,
    }
    return stats


# ---------------------------------------------------------------------------
# Soldier Field projection
# ---------------------------------------------------------------------------

def project_soldier_field(ref_stats: dict) -> dict:
    """
    Using value-per-acre from the reference neighborhood, project what
    the Soldier Field footprint would yield as a similar development.
    """
    sf_acres = bbox_area_acres(SOLDIER_FIELD_AREA)

    projected_market = ref_stats["market_value_per_acre"] * sf_acres
    projected_assessed = projected_market * ASSESSMENT_RATIO
    projected_tax = projected_market * ASSESSMENT_RATIO * PROPERTY_TAX_RATE
    estimated_parcels = int(ref_stats["parcels"] * (sf_acres / ref_stats["area_acres"]))

    return {
        "area_acres": sf_acres,
        "projected_market_value": projected_market,
        "projected_assessed_value": projected_assessed,
        "annual_property_tax": projected_tax,
        "estimated_parcels": estimated_parcels,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_report(ref: dict, sf: dict) -> None:
    """Print a human-readable summary of both areas."""

    sep = "=" * 70

    print(f"\n{sep}")
    print("SOLDIER FIELD TEAR-DOWN — PROPERTY VALUE ANALYSIS")
    print(sep)

    print("\n— REFERENCE NEIGHBORHOOD (Roosevelt / Indiana / Cermak / Clark) —")
    print(f"  Parcels with assessed value:  {ref['parcels']:>10,}")
    print(f"  Gross area:                   {ref['area_acres']:>10.1f} acres")
    print(f"  Total assessed value:       ${ref['total_assessed_value']:>14,.0f}")
    print(f"  Total market value (est.):  ${ref['total_market_value']:>14,.0f}")
    print(f"  Market value / acre:        ${ref['market_value_per_acre']:>14,.0f}")
    print(f"  Avg market value / parcel:  ${ref['avg_market_value_per_parcel']:>14,.0f}")
    print(f"  Annual property tax rev:    ${ref['annual_property_tax']:>14,.0f}")
    print(f"  Annual tax / acre:          ${ref['annual_tax_per_acre']:>14,.0f}")

    print(f"\n— SOLDIER FIELD + SOUTH PARKING (projected) —")
    print(f"  Footprint area:               {sf['area_acres']:>10.1f} acres")
    print(f"  Estimated parcels:            {sf['estimated_parcels']:>10,}")
    print(f"  Projected market value:     ${sf['projected_market_value']:>14,.0f}")
    print(f"  Projected assessed value:   ${sf['projected_assessed_value']:>14,.0f}")
    print(f"  Annual property tax rev:    ${sf['annual_property_tax']:>14,.0f}")

    print(f"\n— KEY TAKEAWAY —")
    print(f"  Replacing Soldier Field with a street-grid neighborhood at the")
    print(f"  same density as the reference area would add approximately")
    print(f"  ${sf['projected_market_value']:,.0f} in property value and generate")
    print(f"  ${sf['annual_property_tax']:,.0f} in annual property tax revenue.")
    print(sep)


def save_results(ref: dict, sf: dict) -> Path:
    """Write a small CSV summarising both areas to analysis_results/."""
    rows = [
        {"area": "Reference (Roosevelt/Indiana/Cermak/Clark)", **{k: v for k, v in ref.items()}},
        {"area": "Soldier Field + South Parking (projected)", **{k: v for k, v in sf.items()}},
    ]
    out = pd.DataFrame(rows)
    path = ANALYSIS_RESULTS_DIR / "soldier_field_value_projection.csv"
    out.to_csv(path, index=False)
    print(f"\nSaved results → {path}")
    return path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ensure_dirs()

    df = load_parcels_and_assessments()

    ref_stats = analyze_reference_area(df)
    sf_stats = project_soldier_field(ref_stats)

    print_report(ref_stats, sf_stats)
    save_results(ref_stats, sf_stats)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

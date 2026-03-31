"""
Property Value Modeling
=======================
Full property-value projection engine that:
  1. Loads real per-parcel assessed values (no flat $250K estimate)
  2. Applies zone-transition-specific uplift factors from config
  3. Adds transit-proximity distance-decay multiplier
  4. Supports an OLS / gradient-boosting regression alternative
  5. Produces per-parcel projections with confidence intervals
  6. Validates against actual 2020-2024 appreciation

Outputs:
    data/processed/value_projections.csv
    data/processed/value_model_validation.csv

Usage:
    python -m src.property_value
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import (
    ASSESSMENT_RATIO,
    PROPERTY_TAX_RATE,
    ZONE_TRANSITION_FACTORS,
    FAR_APPRECIATION_RATE,
    DEVELOPMENT_RIGHTS_ADJUSTMENT,
    MEDIAN_VALUES_BY_ZONE,
    PARCELS_ENRICHED_GEOJSON,
    PARCELS_IN_AREA_CSV,
    PROCESSED_DIR,
    ANALYSIS_RESULTS_DIR,
    ZONING_CODES_CSV,
    ensure_dirs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALUE_PROJECTIONS_CSV = PROCESSED_DIR / "value_projections.csv"
VALIDATION_CSV = PROCESSED_DIR / "value_model_validation.csv"

# Scenario definitions: (label, upzone_rules)
# Each rule: (from_zone_prefix_or_class, to_zone_class)
SCENARIOS = {
    "baseline": {
        "name": "Baseline (no rezoning)",
        "rules": [],
    },
    "moderate": {
        "name": "Moderate Upzoning",
        "description": "Upzone RS-3 → RT-4 city-wide",
        "rules": [("RS-3", "RT-4")],
    },
    "aggressive": {
        "name": "Aggressive TOD Upzoning",
        "description": "Upzone RS-3 → RM-5 near transit, RS-3 → RT-4 elsewhere",
        "rules": [
            ("RS-3", "RM-5", "near_transit"),
            ("RS-3", "RT-4", "elsewhere"),
            ("RT-4", "RM-5", "near_transit"),
        ],
    },
}

# Transit distance-decay parameters  (distance in meters → multiplier)
TRANSIT_DECAY_BANDS = [
    (0, 400, 1.15),    # ≤ 400 m  → +15 %
    (400, 800, 1.08),  # 400–800 m → +8 %
    (800, 1200, 1.03), # 800–1200 m → +3 %
]
TRANSIT_DECAY_DEFAULT = 1.00  # > 1200 m  → no uplift


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_enriched_parcels() -> pd.DataFrame | None:
    """
    Load enriched parcels (produced by ``src.zoning.run_zoning_analysis``).

    Falls back to ``PARCELS_IN_AREA_CSV`` if the enriched GeoJSON doesn't
    exist yet.
    """
    try:
        import geopandas as gpd
    except ImportError:
        gpd = None

    if PARCELS_ENRICHED_GEOJSON.exists() and gpd is not None:
        gdf = gpd.read_file(PARCELS_ENRICHED_GEOJSON)
        print(f"Loaded enriched parcels: {len(gdf):,} rows from {PARCELS_ENRICHED_GEOJSON.name}")
        return gdf

    if PARCELS_IN_AREA_CSV.exists():
        df = pd.read_csv(PARCELS_IN_AREA_CSV, dtype={"pin": str, "class": str})
        print(f"Loaded parcels-in-area CSV: {len(df):,} rows (enriched GeoJSON not found)")
        return df

    print("ERROR: No parcel data found.  Run  python -m src.zoning  or  python -m src.analyze_area  first.")
    return None


def load_appreciation_rates() -> dict:
    """Return {zoning_type: avg_annual_appreciation} from historical analysis."""
    path = PROCESSED_DIR / "historical_appreciation_by_zoning.csv"
    if not path.exists():
        path = ANALYSIS_RESULTS_DIR / "historical_appreciation_by_zoning.csv"
    if not path.exists():
        print(f"WARNING: Appreciation rates file not found ({path}).  Using 3 % default.")
        return {}
    df = pd.read_csv(path)
    col = "avg_annual_appreciation"
    if col not in df.columns:
        # Try alternate name produced by process_historical
        for alt in ["avg_annual_appreciation_pct"]:
            if alt in df.columns:
                col = alt
                break
    lookup: dict[str, float] = {}
    for _, row in df.iterrows():
        lookup[str(row["zoning_type"])] = float(row[col])
    print(f"Loaded appreciation rates for {len(lookup)} zone types")
    return lookup


def load_far_lookup() -> dict:
    """Return {zone_class: FAR} from zoning_codes.csv."""
    if not ZONING_CODES_CSV.exists():
        return {}
    codes = pd.read_csv(ZONING_CODES_CSV)
    mapping: dict[str, float] = {}
    for _, row in codes.iterrows():
        try:
            mapping[row["district_type_code"]] = float(row["floor_area_ratio"])
        except (ValueError, TypeError):
            pass
    return mapping


# ---------------------------------------------------------------------------
# Core model functions
# ---------------------------------------------------------------------------

def current_market_value(row: pd.Series) -> float:
    """
    Derive the per-parcel market value from assessment columns.

    Priority order:
      1. ``estimated_market_value`` (if already present)
      2. ``certified_tot / ASSESSMENT_RATIO``
      3. ``mailed_tot / ASSESSMENT_RATIO``
      4. Zone-median fallback from ``MEDIAN_VALUES_BY_ZONE``
    """
    for col in ("estimated_market_value", "market_value"):
        val = row.get(col)
        if pd.notna(val) and val > 0:
            return float(val)

    for col in ("certified_tot", "mailed_tot", "total_value", "assessed_value"):
        val = row.get(col)
        if pd.notna(val) and val > 0:
            return float(val) / ASSESSMENT_RATIO

    # Fallback to zone-median
    zone = _zone_class(row)
    return float(MEDIAN_VALUES_BY_ZONE.get(zone, 250_000))


def _zone_class(row: pd.Series) -> str:
    """Extract zone class from whichever column exists."""
    for col in ("zone_class", "ZONE_CLASS", "zoning_class", "current_zoning"):
        val = row.get(col)
        if pd.notna(val):
            return str(val)
    return "Unknown"


def transit_multiplier(row: pd.Series) -> float:
    """
    Distance-decay multiplier based on proximity to the nearest L station.

    Uses ``transit_dist_m`` (meters) if available, otherwise falls back to
    the boolean ``near_transit`` flag.
    """
    dist = row.get("transit_dist_m")
    if pd.notna(dist) and dist >= 0:
        for lo, hi, mult in TRANSIT_DECAY_BANDS:
            if lo <= dist < hi:
                return mult
        return TRANSIT_DECAY_DEFAULT

    # Boolean fallback (when distance is unknown)
    if row.get("near_transit") is True or row.get("near_transit") == 1:
        return TRANSIT_DECAY_BANDS[0][2]  # treat as closest band
    return TRANSIT_DECAY_DEFAULT


def zone_transition_factor(current: str, proposed: str, far_lookup: dict) -> float:
    """
    Value factor for rezoning *current* → *proposed*.

    Checks ``ZONE_TRANSITION_FACTORS`` first (exact match, then prefix match),
    then falls back to a FAR-ratio estimate.
    """
    if current == proposed:
        return 1.0

    # Exact match
    key = (current, proposed)
    if key in ZONE_TRANSITION_FACTORS:
        return ZONE_TRANSITION_FACTORS[key]

    # Prefix match  (e.g. RS → RT)
    cp = current.split("-")[0]
    pp = proposed.split("-")[0]
    if (cp, pp) in ZONE_TRANSITION_FACTORS:
        return ZONE_TRANSITION_FACTORS[(cp, pp)]

    # FAR-ratio fallback
    fc = far_lookup.get(current, 0)
    fp = far_lookup.get(proposed, 0)
    if fc > 0:
        return 1 + ((fp / fc) - 1) * FAR_APPRECIATION_RATE
    return 1.0


def composite_uplift(
    transition_f: float,
    transit_m: float,
    dev_rights_f: float,
    w_transition: float = 0.50,
    w_transit: float = 0.25,
    w_dev: float = 0.25,
) -> float:
    """Weighted composite of the three uplift components."""
    return w_transition * transition_f + w_transit * transit_m + w_dev * dev_rights_f


def confidence_bounds(
    base_value: float,
    uplift_factor: float,
    years: int,
    appreciation_std: float = 0.04,
    z: float = 1.96,
) -> tuple[float, float]:
    """
    Return (lower, upper) 95 % confidence bounds around the projected value.

    Uses a simple propagation of uncertainty from the historical standard
    deviation of annual appreciation rates.
    """
    projected = base_value * uplift_factor
    annual_se = appreciation_std / np.sqrt(max(years, 1))
    half_width = z * annual_se * base_value * years
    return (projected - half_width, projected + half_width)


# ---------------------------------------------------------------------------
# Scenario engine
# ---------------------------------------------------------------------------

def apply_scenario(
    df: pd.DataFrame,
    scenario_key: str,
    far_lookup: dict,
    appreciation_lookup: dict,
    time_horizon: int = 10,
) -> pd.DataFrame:
    """
    Project per-parcel values under one scenario.

    Returns a copy of *df* with new columns:
        current_value, proposed_zone, transition_factor, transit_mult,
        dev_rights_factor, composite_factor, projected_value,
        projected_lower, projected_upper, uplift_pct, scenario
    """
    scenario = SCENARIOS.get(scenario_key)
    if scenario is None:
        raise ValueError(f"Unknown scenario '{scenario_key}'")

    out = df.copy()
    out["scenario"] = scenario["name"]
    out["current_value"] = out.apply(current_market_value, axis=1)
    out["current_zone"] = out.apply(_zone_class, axis=1)
    out["proposed_zone"] = out["current_zone"].copy()

    # Apply rezoning rules
    for rule in scenario.get("rules", []):
        from_zone = rule[0]
        to_zone = rule[1]
        condition = rule[2] if len(rule) > 2 else None

        mask = out["current_zone"] == from_zone
        if condition == "near_transit":
            mask = mask & (out.get("near_transit", pd.Series(False, index=out.index)).fillna(False).astype(bool))
        elif condition == "elsewhere":
            mask = mask & (~out.get("near_transit", pd.Series(False, index=out.index)).fillna(False).astype(bool))

        out.loc[mask, "proposed_zone"] = to_zone

    # Factors ---
    out["transition_factor"] = out.apply(
        lambda r: zone_transition_factor(r["current_zone"], r["proposed_zone"], far_lookup),
        axis=1,
    )
    out["transit_mult"] = out.apply(transit_multiplier, axis=1)

    # Development rights factor
    out["current_far"] = out["current_zone"].map(far_lookup).fillna(0)
    out["proposed_far"] = out["proposed_zone"].map(far_lookup).fillna(0)
    out["dev_rights_factor"] = np.where(
        out["current_far"] > 0,
        1 + (out["proposed_far"] / out["current_far"] - 1) * DEVELOPMENT_RIGHTS_ADJUSTMENT,
        1.0,
    )

    out["composite_factor"] = out.apply(
        lambda r: composite_uplift(r["transition_factor"], r["transit_mult"], r["dev_rights_factor"]),
        axis=1,
    )

    # Project forward using historical appreciation + composite uplift
    def _project(row):
        zone_key = row["current_zone"]
        # Try prefix fallback (e.g. "RS-3" → "RS")
        base_rate = appreciation_lookup.get(zone_key, appreciation_lookup.get(zone_key.split("-")[0], 0.03))
        # Annualised base growth
        base_growth = (1 + base_rate) ** time_horizon
        return row["current_value"] * base_growth * row["composite_factor"]

    out["projected_value"] = out.apply(_project, axis=1)

    # Confidence intervals
    bounds = out.apply(
        lambda r: confidence_bounds(r["current_value"], r["composite_factor"], time_horizon),
        axis=1,
    )
    out["projected_lower"] = bounds.apply(lambda b: b[0])
    out["projected_upper"] = bounds.apply(lambda b: b[1])

    out["uplift_pct"] = ((out["projected_value"] / out["current_value"]) - 1) * 100
    out["annual_tax_baseline"] = out["current_value"] * ASSESSMENT_RATIO * PROPERTY_TAX_RATE
    out["annual_tax_projected"] = out["projected_value"] * ASSESSMENT_RATIO * PROPERTY_TAX_RATE
    out["annual_tax_increase"] = out["annual_tax_projected"] - out["annual_tax_baseline"]

    return out


# ---------------------------------------------------------------------------
# Regression alternative
# ---------------------------------------------------------------------------

def train_regression_model(
    df: pd.DataFrame,
    target_col: str = "projected_value",
) -> Optional[object]:
    """
    Train a gradient-boosting regressor on available features as an
    alternative to the rule-based model.

    Returns the fitted model, or *None* if sklearn is unavailable.
    """
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import cross_val_score
    except ImportError:
        print("WARNING: scikit-learn not installed — skipping regression model.")
        return None

    feature_cols = [
        c for c in [
            "current_value", "current_far", "proposed_far",
            "transition_factor", "transit_mult", "dev_rights_factor",
        ]
        if c in df.columns
    ]
    if not feature_cols or target_col not in df.columns:
        print("WARNING: Not enough columns for regression model.")
        return None

    X = df[feature_cols].fillna(0)
    y = df[target_col].fillna(0)

    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42,
    )
    scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    print(f"  GBR cross-val R²: {scores.mean():.3f} ± {scores.std():.3f}")

    model.fit(X, y)
    df["regression_projected"] = model.predict(X)
    return model


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_against_actuals(
    df: pd.DataFrame,
    appreciation_lookup: dict,
    validation_years: tuple[int, int] = (2020, 2024),
) -> pd.DataFrame | None:
    """
    Compare model-predicted 4-year appreciation to actual 2020→2024 changes
    using historical per-parcel data (if available).
    """
    hist_path = ANALYSIS_RESULTS_DIR / "parcel_appreciation_summary.csv"
    if not hist_path.exists():
        hist_path = PROCESSED_DIR / "parcel_appreciation_summary.csv"
    if not hist_path.exists():
        print("WARNING: Parcel appreciation summary not found — skipping validation.")
        return None

    actuals = pd.read_csv(hist_path, dtype={"pin": str})
    if "total_appreciation" not in actuals.columns:
        print("WARNING: total_appreciation column missing — skipping validation.")
        return None

    start, end = validation_years
    horizon = end - start

    # Predicted appreciation per parcel
    pred = df[["pin", "current_zone"]].copy() if "pin" in df.columns else None
    if pred is None:
        # Try alternative pin column names
        for col in ("PIN", "pin14", "parcel_id"):
            if col in df.columns:
                pred = df[[col, "current_zone"]].rename(columns={col: "pin"}).copy()
                break
    if pred is None:
        print("WARNING: No pin column found — skipping validation.")
        return None

    pred["predicted_annual"] = pred["current_zone"].map(
        lambda z: appreciation_lookup.get(z, appreciation_lookup.get(z.split("-")[0], 0.03))
    )
    pred["predicted_total"] = (1 + pred["predicted_annual"]) ** horizon - 1

    merged = pred.merge(actuals[["pin", "total_appreciation"]], on="pin", how="inner")
    if merged.empty:
        print("WARNING: No matching PINs for validation.")
        return None

    merged["error"] = merged["predicted_total"] - merged["total_appreciation"]
    merged["abs_error"] = merged["error"].abs()

    mae = merged["abs_error"].mean()
    mpe = merged["error"].mean() * 100
    print(f"  Validation ({start}-{end}):  MAE = {mae:.4f}  |  Mean error = {mpe:+.2f}%  |  N = {len(merged):,}")

    return merged


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_projections(time_horizon: int = 10) -> pd.DataFrame | None:
    """Run all scenarios and produce consolidated value_projections.csv."""
    ensure_dirs()

    df = load_enriched_parcels()
    if df is None:
        return None

    appreciation = load_appreciation_rates()
    far_lookup = load_far_lookup()

    all_results: list[pd.DataFrame] = []

    for key in SCENARIOS:
        print(f"\n--- Scenario: {SCENARIOS[key]['name']} ---")
        result = apply_scenario(df, key, far_lookup, appreciation, time_horizon)
        all_results.append(result)

        rezoned = result[result["current_zone"] != result["proposed_zone"]]
        print(f"  Parcels rezoned: {len(rezoned):,}")
        if len(rezoned) > 0:
            print(f"  Avg uplift: {rezoned['uplift_pct'].mean():.1f}%")
            print(f"  Total current value: ${rezoned['current_value'].sum():,.0f}")
            print(f"  Total projected value: ${rezoned['projected_value'].sum():,.0f}")

    combined = pd.concat(all_results, ignore_index=True)

    # Select output columns
    out_cols = [
        c for c in [
            "pin", "PIN", "current_zone", "proposed_zone", "current_value",
            "projected_value", "projected_lower", "projected_upper",
            "uplift_pct", "transition_factor", "transit_mult",
            "dev_rights_factor", "composite_factor",
            "annual_tax_baseline", "annual_tax_projected", "annual_tax_increase",
            "scenario",
        ]
        if c in combined.columns
    ]
    output = combined[out_cols].copy()
    output.to_csv(VALUE_PROJECTIONS_CSV, index=False)
    print(f"\nSaved {len(output):,} rows → {VALUE_PROJECTIONS_CSV}")

    # Regression alternative
    print("\n--- Regression alternative ---")
    baseline_result = all_results[0]  # baseline
    model = train_regression_model(baseline_result)

    # Validation
    print("\n--- Validation ---")
    val = validate_against_actuals(baseline_result, appreciation)
    if val is not None:
        val.to_csv(VALIDATION_CSV, index=False)
        print(f"Saved validation to {VALIDATION_CSV}")

    return output


def main():
    print("=" * 70)
    print("PROPERTY VALUE PROJECTION ENGINE")
    print("=" * 70)

    result = run_projections(time_horizon=10)

    if result is None:
        print("\nProjection failed — see errors above.")
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("PROJECTION SUMMARY")
    print("=" * 70)
    for scenario in result["scenario"].unique():
        subset = result[result["scenario"] == scenario]
        print(f"\n  [{scenario}]")
        print(f"    Parcels: {len(subset):,}")
        print(f"    Avg current value:   ${subset['current_value'].mean():>12,.0f}")
        print(f"    Avg projected value: ${subset['projected_value'].mean():>12,.0f}")
        print(f"    Avg uplift:         {subset['uplift_pct'].mean():>11.1f}%")
        rezoned = subset[subset["current_zone"] != subset["proposed_zone"]]
        if len(rezoned) > 0:
            print(f"    Rezoned parcels: {len(rezoned):,}")
            print(f"    Total tax increase: ${rezoned['annual_tax_increase'].sum():>12,.0f}/yr")

    return 0


if __name__ == "__main__":
    exit(main())

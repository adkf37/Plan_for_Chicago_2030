"""Class-aware 2023 valuation and explicitly pre-exemption tax benchmarks.

These calculations are assessment-implied values and fixed-rate illustrations,
not independent sale-price predictions, actual tax bills, or net fiscal benefits.
"""

import math

import pandas as pd


def tax_benchmark(
    assessed_value: float, equalizer: float, rate_percent: float, exemption_eav: float = 0.0
) -> float:
    """Apply deductions to EAV before a rate expressed in percentage points.

    Use parcel-level exemptions for parcel bills; an aggregate exemption amount
    is only valid if its parcel-level eligibility/caps have already been applied.
    """
    if not all(math.isfinite(v) for v in (assessed_value, equalizer, rate_percent, exemption_eav)):
        raise ValueError("Tax inputs must be finite")
    if assessed_value < 0 or equalizer <= 0 or not 0 <= rate_percent <= 100 or exemption_eav < 0:
        raise ValueError("Invalid assessed value, equalizer, rate or exemption")
    return max(0.0, assessed_value * equalizer - exemption_eav) * rate_percent / 100


def audit_valuation(df: pd.DataFrame, assumptions: dict) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Account for every PIN; unknown classes and missing amounts fail closed."""
    out = df.copy()
    year = assumptions["tax_year"]
    for column in ("tax_year", "parcel_year"):
        years = pd.to_numeric(out[column], errors="raise")
        if years.isna().any() or not years.eq(year).all():
            raise ValueError("Valuation requires aligned snapshots from the assumptions' tax year")
    if out["pin"].duplicated().any():
        raise ValueError("Duplicate PINs in valuation")
    stage = assumptions["assessment_stage"]
    values = pd.to_numeric(out[stage], errors="raise")
    if values.isna().any() or (values < 0).any() or not values.map(math.isfinite).all():
        raise ValueError(
            "Missing, negative or nonfinite assessment values; no stage fallback allowed"
        )
    if not values.gt(0).any():
        raise ValueError("No positive assessments for valuation")
    out["assessed_value"] = values
    out["class"] = out["class"].astype("string").str.strip().str.upper()
    low_levels, high_levels = [], []
    for code, value in zip(out["class"], values):
        if pd.isna(code):
            raise ValueError("Missing assessment class")
        if code in assumptions["zero_only_excluded_classes"]:
            if value != 0:
                raise ValueError(f"Positive assessment for excluded class {code}")
            levels = [1.0]  # zero tax-base contribution; not a market valuation of exempt land
        elif code in assumptions["standard_levels"]:
            levels = [assumptions["standard_levels"][code]]
        elif code in assumptions["incentive_level_options"]:
            levels = assumptions["incentive_level_options"][code]
        else:
            raise ValueError(f"No sourced assessment level for class {code}")
        if not levels or any(not math.isfinite(v) or not 0 < v <= 1 for v in levels):
            raise ValueError("Assessment levels must be finite fractions in (0, 1]")
        low_levels.append(min(levels))
        high_levels.append(max(levels))
    out["assessment_level_low"] = low_levels
    out["assessment_level_high"] = high_levels
    out["market_equivalent_low"] = values / out["assessment_level_high"]
    out["market_equivalent_high"] = values / out["assessment_level_low"]
    out["uncertain_level"] = out["assessment_level_low"] != out["assessment_level_high"]
    out["tax_code"] = out["tax_code"].astype("string")
    rates = out["tax_code"].map(assumptions["reference_tax_code_rates_percent"])
    if rates.isna().any():
        raise ValueError("Reference tax code has no verified year-specific rate")
    out["pre_exemption_tax_benchmark"] = [
        tax_benchmark(v, assumptions["equalization_factor"], rate) for v, rate in zip(values, rates)
    ]
    grouped = (
        out.groupby("class", dropna=False)
        .agg(
            pins=("pin", "size"),
            assessed_value=("assessed_value", "sum"),
            market_equivalent_low=("market_equivalent_low", "sum"),
            market_equivalent_high=("market_equivalent_high", "sum"),
            assessment_level_low=("assessment_level_low", "min"),
            assessment_level_high=("assessment_level_high", "max"),
            pre_exemption_tax_benchmark=("pre_exemption_tax_benchmark", "sum"),
        )
        .reset_index()
    )
    summary = {
        "valuation_assessment_stage": stage,
        "valuation_assessed_value": float(values.sum()),
        "market_equivalent_low": float(out["market_equivalent_low"].sum()),
        "market_equivalent_high": float(out["market_equivalent_high"].sum()),
        "uncertain_incentive_pins": int(out["uncertain_level"].sum()),
        "uncertain_incentive_assessed_value": float(values[out["uncertain_level"]].sum()),
        "reference_pre_exemption_tax_benchmark": float(out["pre_exemption_tax_benchmark"].sum()),
        "market_value_scope": "Assessment-implied taxable-property equivalent; exempt/railroad zero assessments are excluded, not valued",
        "tax_scope": "Fixed 2023 rates before exemptions; not actual bills or incremental revenue",
    }
    return out, grouped, summary

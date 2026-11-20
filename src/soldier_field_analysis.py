"""Soldier Field neighborhood analogy (exploratory, not a fiscal forecast).

Transfer observed value per gross reference acre onto sourced physical-site
scenarios. Market equivalents use class-specific assessment levels. Tax outputs
are fixed-2023-rate benchmarks before exemptions, not fiscal impact forecasts.

Prepare aligned locations, then run:
    python -m src.prepare_soldier_field_inputs
    python -m src.soldier_field_analysis --assessment-year 2023

The financial audit requires aligned 2023 snapshots. No market or revenue claim
is inferred from the superseded 274-acre rectangle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
from shapely.geometry import shape

from src.config import (
    RAW_ASSESSMENT_CSV,
    RAW_PARCEL_UNIVERSE_CSV,
    REFERENCE_AREA,
    SOLDIER_FIELD_AREA,
    ANALYSIS_RESULTS_DIR,
    SOLDIER_FIELD_BOUNDARIES,
    SOLDIER_FIELD_ASSUMPTIONS,
    SOLDIER_FIELD_SOURCE_DIR,
    SOLDIER_FIELD_COMPARATOR_AUDIT,
    SOLDIER_FIELD_REFERENCE_DIR,
)
from src.prepare_soldier_field_inputs import area_acres, rectangle
from src.soldier_field_valuation import audit_valuation, tax_benchmark


def bbox_area_acres(bbox: dict) -> float:
    """Approximate gross rectangle area; this is not developable acreage."""
    values = [bbox[k] for k in ("min_lat", "max_lat", "min_lon", "max_lon")]
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Bounding box must contain finite coordinates")
    if not (-90 < bbox["min_lat"] < bbox["max_lat"] < 90):
        raise ValueError("Invalid latitude bounds")
    if not (-180 <= bbox["min_lon"] < bbox["max_lon"] <= 180):
        raise ValueError("Invalid longitude bounds")
    mid_lat = (bbox["min_lat"] + bbox["max_lat"]) / 2
    lat_m = (bbox["max_lat"] - bbox["min_lat"]) * 111_320
    lon_m = (bbox["max_lon"] - bbox["min_lon"]) * 111_320 * math.cos(math.radians(mid_lat))
    return lat_m * lon_m / 4_046.86


def filter_to_bbox(df: pd.DataFrame, bbox: dict) -> pd.DataFrame:
    """Select PIN locations, including boundaries, without counting geometry area."""
    bbox_area_acres(bbox)
    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    return df[
        lat.between(bbox["min_lat"], bbox["max_lat"])
        & lon.between(bbox["min_lon"], bbox["max_lon"])
    ].copy()


def normalize_pins(pins: pd.Series) -> pd.Series:
    """Preserve leading zeros and reject ambiguous or invalid identifiers."""
    pins = pins.astype("string").str.strip().str.replace("-", "", regex=False)
    if not pins.str.fullmatch(r"[0-9]{1,14}").fillna(False).all():
        raise ValueError("Invalid PIN: expected up to 14 digits, optionally hyphenated")
    return pins.str.zfill(14)


def merge_snapshots(
    parcels: pd.DataFrame, assessments: pd.DataFrame, assessment_year: int, parcel_year: int
) -> pd.DataFrame:
    """Join one selected snapshot per input, using assessment-year classes."""
    selected = []
    for frame, year, label in (
        (parcels, parcel_year, "parcel"),
        (assessments, assessment_year, "assessment"),
    ):
        frame = frame[pd.to_numeric(frame["tax_year"], errors="raise") == year].copy()
        if frame.empty:
            raise ValueError(f"No {label} records for requested year {year}")
        frame["pin"] = normalize_pins(frame["pin"])
        if frame["pin"].duplicated().any():
            raise ValueError(f"Duplicate PINs in {label} snapshot for {year}")
        selected.append(frame)
    parcels, assessments = selected
    parcels = parcels.rename(columns={"tax_year": "parcel_year", "class": "parcel_class"})
    return parcels.merge(
        assessments, on="pin", how="left", validate="one_to_one", indicator="assessment_match"
    )


def load_parcels_and_assessments(
    assessment_year: int,
    parcel_year: int | None = None,
    parcel_path: Path | None = None,
    assessment_path: Path = RAW_ASSESSMENT_CSV,
    bounds: dict = REFERENCE_AREA,
) -> pd.DataFrame:
    """Read only the reference area and selected vintages from large CSVs."""
    parcel_year = assessment_year if parcel_year is None else parcel_year
    if parcel_path is None:
        aligned = SOLDIER_FIELD_SOURCE_DIR / f"parcels_{parcel_year}.csv"
        parcel_path = aligned if aligned.exists() else RAW_PARCEL_UNIVERSE_CSV
    parcel_columns = pd.read_csv(parcel_path, nrows=0).columns
    assessment_columns = pd.read_csv(assessment_path, nrows=0).columns
    extra_parcel_columns = [
        c for c in ("tax_code", "tax_district_code", "tax_tif_district_num") if c in parcel_columns
    ]
    parts = []
    for chunk in pd.read_csv(
        parcel_path,
        dtype={"pin": "string", "class": "string"},
        usecols=["pin", "tax_year", "latitude", "longitude", "class"] + extra_parcel_columns,
        chunksize=200_000,
    ):
        chunk = chunk[pd.to_numeric(chunk["tax_year"], errors="raise") == parcel_year]
        parts.append(filter_to_bbox(chunk, bounds))
    parcels = pd.concat(parts, ignore_index=True)
    if "tax_code" not in parcels and "tax_district_code" in parcels:
        parcels = parcels.rename(columns={"tax_district_code": "tax_code"})
    parcels["pin"] = normalize_pins(parcels["pin"])
    pins = set(parcels["pin"])
    parts = []
    for chunk in pd.read_csv(
        assessment_path,
        dtype={"pin": "string", "class": "string"},
        usecols=["pin", "tax_year", "class", "certified_tot"]
        + (["board_tot"] if "board_tot" in assessment_columns else []),
        chunksize=200_000,
    ):
        chunk = chunk[pd.to_numeric(chunk["tax_year"], errors="raise") == assessment_year]
        chunk["pin"] = normalize_pins(chunk["pin"])
        parts.append(chunk[chunk["pin"].isin(pins)])
    assessments = pd.concat(parts, ignore_index=True)
    return merge_snapshots(parcels, assessments, assessment_year, parcel_year)


def analyze_reference_area(df: pd.DataFrame, bounds: dict = REFERENCE_AREA) -> dict:
    """Summarize observed assessments and explicitly account for exclusions.

    This is the certified-stage reconciliation. The separate financial audit
    explicitly selects Board of Review values and adds classification bounds.
    """
    ref = filter_to_bbox(df, bounds)
    if ref.empty:
        raise ValueError("No reference-area parcels")
    if normalize_pins(ref["pin"]).duplicated().any():
        raise ValueError("Duplicate reference-area PINs would inflate totals")
    if ref["tax_year"].dropna().nunique() != 1 or ref["parcel_year"].nunique() != 1:
        raise ValueError("Exactly one assessment year and parcel year are required")
    values = pd.to_numeric(ref["certified_tot"], errors="raise")
    if values.dropna().lt(0).any() or not values.dropna().map(math.isfinite).all():
        raise ValueError("Assessments must be finite and nonnegative")
    positive = values.gt(0)
    if not positive.any():
        raise ValueError("No positive reference-area assessments")
    matched = ref["assessment_match"].eq("both")
    assessed = float(values[positive].sum())
    acres = area_acres(rectangle(bounds))
    return {
        "assessment_year": int(ref["tax_year"].dropna().iloc[0]),
        "parcel_year": int(ref["parcel_year"].iloc[0]),
        "assessment_stage": "certified_tot",
        "reference_pins": len(ref),
        "matched_pins": int(matched.sum()),
        "unmatched_pins": int((~matched).sum()),
        "matched_missing_value_pins": int((matched & values.isna()).sum()),
        "zero_value_pins": int(values.eq(0).sum()),
        "positive_value_pins": int(positive.sum()),
        "class_changed_pins": int((matched & ref["class"].ne(ref["parcel_class"])).sum()),
        "gross_area_acres": acres,
        "observed_assessed_value": assessed,
        "observed_assessed_value_per_gross_acre": assessed / acres,
        "status": "exploratory gross-acre comparison; see separate financial audit",
    }


def project_soldier_field(
    ref_stats: dict,
    area_fraction: float = 1.0,
    value_density_factor: float = 1.0,
    *,
    scenario_id: str = "stadium_and_parking",
    boundaries: dict | None = None,
    assumptions: dict | None = None,
) -> dict:
    """Transfer assessed value density; factors are assumptions, not confidence bounds.

    area_fraction selects gross neighborhood acreage within the sourced scenario.
    It is not a net lot ratio: reference gross acres already include streets.
    """
    if not math.isfinite(area_fraction) or not 0 < area_fraction <= 1:
        raise ValueError("area_fraction must be in (0, 1]")
    if not math.isfinite(value_density_factor) or value_density_factor <= 0:
        raise ValueError("value_density_factor must be finite and positive")
    if boundaries is None:
        boundaries = json.loads(SOLDIER_FIELD_BOUNDARIES.read_text(encoding="utf-8"))
    matches = [
        f
        for f in boundaries["features"]
        if f["properties"]["id"] == scenario_id and f["properties"]["role"] == "scenario"
    ]
    if len(matches) != 1:
        raise ValueError(f"Unknown or duplicated scenario: {scenario_id}")
    feature = matches[0]
    acres = area_acres(shape(feature["geometry"]))
    reference_acres = ref_stats["gross_area_acres"]
    if not math.isfinite(reference_acres) or reference_acres <= 0:
        raise ValueError("Reference gross area must be positive and finite")
    scale = acres * area_fraction * value_density_factor / reference_acres
    result = {
        "scenario": scenario_id,
        "name": feature["properties"]["name"],
        "assessment_year": ref_stats["assessment_year"],
        "parcel_year": ref_stats["parcel_year"],
        "candidate_gross_acres": acres,
        "inclusion_rule": feature["properties"]["inclusion_rule"],
        "area_fraction": area_fraction,
        "value_density_factor": value_density_factor,
        "assumed_neighborhood_gross_acres": acres * area_fraction,
        "illustrative_assessed_value": ref_stats.get(
            "valuation_assessed_value", ref_stats["observed_assessed_value"]
        )
        * scale,
        "status": "gross stabilized analogy; not incremental revenue or a 2030 forecast",
    }
    if "market_equivalent_low" in ref_stats:
        if assumptions is None or assumptions["tax_year"] != ref_stats["assessment_year"]:
            raise ValueError("Year-matched financial assumptions are required")
        result.update(
            {
                "assessment_stage": ref_stats["valuation_assessment_stage"],
                "market_equivalent_low": ref_stats["market_equivalent_low"] * scale,
                "market_equivalent_high": ref_stats["market_equivalent_high"] * scale,
                "gross_tax_benchmark_before_exemptions": tax_benchmark(
                    result["illustrative_assessed_value"],
                    assumptions["equalization_factor"],
                    assumptions["candidate_composite_rate_percent"],
                ),
                "city_corporate_component_before_exemptions": tax_benchmark(
                    result["illustrative_assessed_value"],
                    assumptions["equalization_factor"],
                    assumptions["candidate_city_corporate_rate_percent"],
                ),
                "tax_scope": assumptions["candidate_rate_note"],
            }
        )
    return result


def print_report(ref: dict, sf: dict) -> None:
    print("SOLDIER FIELD: EXPLORATORY ASSESSED-VALUE ANALOGY")
    print(f"Assessment year: {ref['assessment_year']}; parcel year: {ref['parcel_year']}")
    if ref["assessment_year"] != ref["parcel_year"]:
        print("WARNING: Different source vintages; same-year locations remain a publication gate.")
    print(f"Positive-value PINs: {ref['positive_value_pins']:,} / {ref['reference_pins']:,}")
    print(f"Unmatched PINs: {ref['unmatched_pins']:,}; zero-value PINs: {ref['zero_value_pins']:,}")
    print(f"Reference gross rectangle: {ref['gross_area_acres']:.1f} acres")
    print(f"Observed certified assessed value: ${ref['observed_assessed_value']:,.0f}")
    print(f"{sf['name']}: {sf['candidate_gross_acres']:.2f} gross acres")
    print(f"Illustrative assessed value: ${sf['illustrative_assessed_value']:,.0f}")
    if "market_equivalent_low" in sf:
        print(
            f"Assessment-implied market equivalent: ${sf['market_equivalent_low']:,.0f}"
            f" - ${sf['market_equivalent_high']:,.0f}"
        )
        print(
            f"Fixed-rate tax benchmark BEFORE exemptions: ${sf['gross_tax_benchmark_before_exemptions']:,.0f}/year"
        )
    print(
        "Physical footprints are not legal development boundaries. No net city revenue is estimated."
    )


def save_results(
    ref: dict,
    sf: dict,
    sources: tuple[Path, ...] = (),
    assumptions: dict | None = None,
    comparators: dict | None = None,
) -> Path:
    """Save summary, sensitivity grid, and reproducible input fingerprints."""
    ANALYSIS_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS_RESULTS_DIR / "soldier_field_value_projection.csv"
    boundaries = json.loads(SOLDIER_FIELD_BOUNDARIES.read_text(encoding="utf-8"))
    scenario_ids = [
        f["properties"]["id"]
        for f in boundaries["features"]
        if f["properties"]["role"] == "scenario"
    ]
    base_scenarios = [
        project_soldier_field(ref, scenario_id=key, boundaries=boundaries, assumptions=assumptions)
        for key in scenario_ids
    ]
    pd.DataFrame([{"area": "reference", **ref}] + base_scenarios).to_csv(path, index=False)
    scenarios = [
        project_soldier_field(
            ref, 1.0, density, scenario_id=key, boundaries=boundaries, assumptions=assumptions
        )
        for key in scenario_ids
        for density in (0.8, 1.0, 1.2)
    ]
    pd.DataFrame(scenarios).to_csv(
        ANALYSIS_RESULTS_DIR / "soldier_field_sensitivity.csv", index=False
    )
    inputs = []
    for source in sources:
        with source.open("rb") as stream:
            hasher = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
            digest = hasher.hexdigest()
        inputs.append({"name": source.name, "bytes": source.stat().st_size, "sha256": digest})
    manifest = {
        "inputs": inputs,
        "reference": ref,
        "candidate": sf,
        "district": {"value": None, "status": "Comparable neighborhood acres pending allocation"},
        "scenarios": base_scenarios,
        "financial_assumptions": assumptions,
        "boundaries": boundaries,
        "comparator_audit": comparators,
        "reference_bbox": dict(
            zip(
                ("min_lon", "min_lat", "max_lon", "max_lat"),
                shape(comparators["comparators"][0]["geometry"]).bounds,
            )
        )
        if comparators
        else REFERENCE_AREA,
        "legacy_candidate_bbox_not_used": SOLDIER_FIELD_AREA,
        "area_method": "EPSG:26971 projected square metres / 4046.8564224",
        "sensitivity": "three sourced-area scenarios and density factors 0.8/1.0/1.2; not probabilities",
    }
    (ANALYSIS_RESULTS_DIR / "soldier_field_run.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assessment-year", type=int, required=True)
    parser.add_argument("--parcel-year", type=int, help="Defaults to assessment year")
    args = parser.parse_args()
    try:
        from src.soldier_field_comparators import street_locations
        from shapely.geometry import Point

        feature_path = SOLDIER_FIELD_REFERENCE_DIR / "wabash_michigan.geojson"
        feature = json.loads(feature_path.read_text())
        geometry = shape(feature["geometry"])
        bounds = dict(zip(("min_lon", "min_lat", "max_lon", "max_lat"), geometry.bounds))
        parcel_source = street_locations(args.parcel_year or args.assessment_year, bounds)
        df = load_parcels_and_assessments(
            args.assessment_year, args.parcel_year, parcel_source, bounds=bounds
        )
        selected = df.loc[[geometry.covers(Point(x, y)) for x, y in zip(df.longitude, df.latitude)]]
        ref = analyze_reference_area(selected, bounds)
        assumptions = json.loads(SOLDIER_FIELD_ASSUMPTIONS.read_text(encoding="utf-8"))
        _, class_audit, financials = audit_valuation(selected, assumptions)
        acres = area_acres(geometry)
        ref.update(financials)
        ref.update(
            gross_area_acres=acres,
            comparator=feature["properties"]["id"],
            observed_assessed_value_per_gross_acre=ref["observed_assessed_value"] / acres,
            status="Board of Review values inside street centerlines",
        )
        benchmark = dict(
            id=ref["comparator"],
            name=feature["properties"]["name"],
            pins=len(selected),
            exempt_pins=int(selected["class"].eq("EX").sum()),
            zero_board_pins=int(selected.board_tot.eq(0).sum()),
            gross_acres=acres,
            assessed_value=financials["valuation_assessed_value"],
            geometry=feature["geometry"],
        )
        for side in ("low", "high"):
            value = financials["market_equivalent_" + side]
            benchmark["market_equivalent_" + side] = value
            benchmark["value_per_gross_acre_" + side] = value / acres
        comparators = dict(
            assessment_year=args.assessment_year,
            assessment_stage="board_tot",
            method=feature["properties"]["method"],
            comparators=[benchmark],
        )
        SOLDIER_FIELD_COMPARATOR_AUDIT.write_text(
            json.dumps(comparators, indent=2) + "\n", encoding="utf-8"
        )
        # The measured subsite remains available as an illustration within the larger district.
        sf = project_soldier_field(ref, scenario_id="connected_envelope", assumptions=assumptions)
        print(
            "Expanded district value pending a land budget. Measured subsite illustration follows."
        )
        print_report(ref, sf)
        path = save_results(
            ref,
            sf,
            (
                parcel_source,
                feature_path,
                RAW_ASSESSMENT_CSV,
                SOLDIER_FIELD_BOUNDARIES,
                SOLDIER_FIELD_ASSUMPTIONS,
            ),
            assumptions=assumptions,
            comparators=comparators,
        )
        class_audit.to_csv(ANALYSIS_RESULTS_DIR / "soldier_field_class_audit.csv", index=False)
        from viz.soldier_field_map import render_outputs

        render_outputs(ANALYSIS_RESULTS_DIR / "soldier_field_run.json")
        print(f"Saved: {path}")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Analysis stopped: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

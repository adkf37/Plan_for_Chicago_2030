"""Regression checks for publication-critical Soldier Field accounting."""

import json

import pandas as pd
import pytest

from src import soldier_field_analysis as sf


@pytest.fixture
def snapshots():
    parcels = pd.DataFrame(
        {
            "pin": ["01-00-000-001-0000", "01000000002000", "01000000003000"],
            "tax_year": [2024] * 3,
            "class": ["299", "299", "EX"],
            "latitude": [41.86] * 3,
            "longitude": [-87.625] * 3,
        }
    )
    assessments = pd.DataFrame(
        {
            "pin": ["01000000010000", "01000000002000", "01000000010000"],
            "tax_year": [2023, 2023, 2022],
            "class": ["299", "597", "299"],
            "certified_tot": [100_000, 200_000, 900_000],
        }
    )
    return parcels, assessments


def test_one_year_preserves_pins_and_uses_assessment_class(snapshots):
    merged = sf.merge_snapshots(*snapshots, 2023, 2024)
    assert len(merged) == 3
    assert merged.iloc[0]["pin"] == "01000000010000"
    ref = sf.analyze_reference_area(merged)
    assert ref["observed_assessed_value"] == 300_000
    assert ref["positive_value_pins"] == 2
    assert ref["unmatched_pins"] == 1
    assert ref["class_changed_pins"] == 1
    assert ref["assessment_year"] == 2023
    assert "total_market_value" not in ref
    assert "annual_property_tax" not in ref


@pytest.mark.parametrize("which", [0, 1])
def test_duplicate_keys_fail_instead_of_multiplying_values(snapshots, which):
    frames = list(snapshots)
    frames[which] = pd.concat([frames[which], frames[which].iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate PIN"):
        sf.merge_snapshots(*frames, 2023, 2024)


def test_missing_requested_year_fails(snapshots):
    with pytest.raises(ValueError, match="No parcel records"):
        sf.merge_snapshots(*snapshots, 2023, 2023)


@pytest.mark.parametrize("pin", [None, "bad", "123.0", "123456789012345"])
def test_invalid_pin_is_rejected(pin):
    with pytest.raises(ValueError, match="Invalid PIN"):
        sf.normalize_pins(pd.Series([pin]))


def test_missing_and_zero_values_are_separate(snapshots):
    merged = sf.merge_snapshots(*snapshots, 2023, 2024)
    merged.loc[1, "certified_tot"] = 0
    ref = sf.analyze_reference_area(merged)
    assert ref["zero_value_pins"] == 1
    assert ref["matched_missing_value_pins"] == 0
    merged.loc[1, "certified_tot"] = None
    assert sf.analyze_reference_area(merged)["matched_missing_value_pins"] == 1


@pytest.mark.parametrize("value", [-1, float("inf"), "bad"])
def test_invalid_values_fail(snapshots, value):
    merged = sf.merge_snapshots(*snapshots, 2023, 2024)
    merged["certified_tot"] = merged["certified_tot"].astype(object)
    merged.loc[0, "certified_tot"] = value
    with pytest.raises(ValueError):
        sf.analyze_reference_area(merged)


def test_empty_reference_fails(snapshots):
    merged = sf.merge_snapshots(*snapshots, 2023, 2024)
    merged["latitude"] = 0
    with pytest.raises(ValueError, match="No reference"):
        sf.analyze_reference_area(merged)


def test_projection_scales_gross_area_and_density(snapshots):
    ref = sf.analyze_reference_area(sf.merge_snapshots(*snapshots, 2023, 2024))
    full = sf.project_soldier_field(ref)
    low = sf.project_soldier_field(ref, 0.5, 0.8)
    assert low["illustrative_assessed_value"] == pytest.approx(
        full["illustrative_assessed_value"] * 0.4
    )
    assert full["illustrative_assessed_value"] == pytest.approx(
        300_000 * full["candidate_gross_acres"] / ref["gross_area_acres"]
    )
    assert full["candidate_gross_acres"] < 40  # must not revert to the 274-acre box
    assert "estimated_parcels" not in full
    for area, density in [(0, 1), (1.1, 1), (1, -1), (float("nan"), 1)]:
        with pytest.raises(ValueError):
            sf.project_soldier_field(ref, area, density)


def test_loader_and_output_provenance(tmp_path, monkeypatch, snapshots):
    parcels, assessments = snapshots
    pp, ap = tmp_path / "parcels.csv", tmp_path / "assessments.csv"
    parcels.to_csv(pp, index=False)
    assessments.to_csv(ap, index=False)
    df = sf.load_parcels_and_assessments(2023, 2024, pp, ap)
    ref = sf.analyze_reference_area(df)
    monkeypatch.setattr(sf, "ANALYSIS_RESULTS_DIR", tmp_path / "results")
    path = sf.save_results(ref, sf.project_soldier_field(ref), (pp, ap))
    assert path.exists()
    manifest = json.loads((path.parent / "soldier_field_run.json").read_text())
    assert manifest["reference"]["observed_assessed_value"] == 300_000
    assert len(manifest["inputs"][0]["sha256"]) == 64
    assert len(pd.read_csv(path.parent / "soldier_field_sensitivity.csv")) == 9

"""Check partition accounting, including PINs exactly on dividing lines."""

import pandas as pd
import pytest

from src.soldier_field_comparators import comparator_audit


def sample():
    return pd.DataFrame(
        {
            "longitude": [-87.63, -87.62, -87.63, -87.62, -87.625],
            "latitude": [41.865, 41.865, 41.855, 41.855, 41.86],
            "assessed_value": [10, 20, 30, 40, 50],
            "market_equivalent_low": [100, 200, 300, 400, 500],
            "market_equivalent_high": [110, 220, 330, 440, 550],
        }
    )


BOUNDS = dict(min_lon=-87.63, max_lon=-87.62, min_lat=41.855, max_lat=41.865)


def test_quadrants_partition_pins_values_and_gross_area():
    results = comparator_audit(sample(), BOUNDS)["comparators"]
    full, *quarters = results
    assert [q["pins"] for q in quarters] == [1, 2, 1, 1]
    for field in ["pins", "assessed_value", "market_equivalent_low", "market_equivalent_high"]:
        assert sum(q[field] for q in quarters) == full[field]
    # Projected straight edges differ very slightly when subdivided geographically.
    assert sum(q["gross_acres"] for q in quarters) == pytest.approx(full["gross_acres"], rel=1e-7)
    assert sum(q["value_per_gross_acre_low"] * q["gross_acres"] for q in quarters) == pytest.approx(
        1500
    )


def test_empty_quadrants_keep_their_gross_area_and_zero_value():
    results = comparator_audit(sample().iloc[:1], BOUNDS)["comparators"]
    assert results[2]["pins"] == 0
    assert results[2]["gross_acres"] > 0
    assert results[2]["value_per_gross_acre_low"] == 0


@pytest.mark.parametrize("longitude", [-90, float("nan")])
def test_reject_points_outside_reference(longitude):
    frame = sample()
    frame.loc[0, "longitude"] = longitude
    with pytest.raises(ValueError, match="inside"):
        comparator_audit(frame, BOUNDS)

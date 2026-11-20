"""Independent arithmetic and publication-gate regression checks."""

import json
import xml.etree.ElementTree as ET

import pandas as pd
import pytest
from shapely.geometry import shape
from shapely.ops import unary_union

from src.config import SOLDIER_FIELD_ASSUMPTIONS, SOLDIER_FIELD_BOUNDARIES
from src.prepare_soldier_field_inputs import area_acres, component_geometry
from src.soldier_field_valuation import audit_valuation, tax_benchmark


@pytest.fixture
def assumptions():
    return json.loads(SOLDIER_FIELD_ASSUMPTIONS.read_text(encoding="utf-8"))


@pytest.fixture
def parcels():
    return pd.DataFrame(
        {
            "pin": ["00000000000001", "00000000000002", "00000000000003", "00000000000004"],
            "tax_year": [2023] * 4,
            "parcel_year": [2023] * 4,
            "class": ["299", "597", "748", "EX"],
            "board_tot": [100_000, 100_000, 100_000, 0],
            "certified_tot": [999_999] * 4,
            "tax_code": ["76102"] * 4,
        }
    )


def test_class_rates_and_incentive_bounds_reconcile(parcels, assumptions):
    detail, grouped, summary = audit_valuation(parcels, assumptions)
    assert detail.market_equivalent_low.tolist() == [1_000_000, 400_000, 500_000, 0]
    assert detail.market_equivalent_high.tolist() == [1_000_000, 400_000, 1_000_000, 0]
    assert summary["valuation_assessed_value"] == 300_000
    assert summary["market_equivalent_low"] == 1_900_000
    assert summary["market_equivalent_high"] == 2_400_000
    assert summary["uncertain_incentive_pins"] == 1
    assert grouped.assessed_value.sum() == summary["valuation_assessed_value"]
    assert summary["reference_pre_exemption_tax_benchmark"] == pytest.approx(
        300_000 * 3.0163 * 0.07018
    )


def test_tax_deducts_exemptions_from_eav_not_market_or_av():
    # Clerk's example: $250k home, 10% AV, 2023 equalizer, $10k EAV deduction.
    # Analytical benchmark retains precision; printed bills round EAV separately.
    assert tax_benchmark(25_000, 3.0163, 6.995, 10_000) == pytest.approx(4575.254625)
    assert tax_benchmark(100, 3.0163, 6.995, 10_000) == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("tax_year", 2024),
        ("parcel_year", 2024),
        ("class", "777"),
        ("class", None),
        ("board_tot", None),
        ("board_tot", -1),
        ("board_tot", float("inf")),
        ("tax_code", "99999"),
    ],
)
def test_unverified_financial_inputs_stop_run(parcels, assumptions, field, value):
    parcels[field] = parcels[field].astype(object)
    parcels.loc[0, field] = value
    with pytest.raises(ValueError):
        audit_valuation(parcels, assumptions)


def test_positive_exempt_value_not_silently_ignored(parcels, assumptions):
    parcels.loc[3, "board_tot"] = 1
    with pytest.raises(ValueError, match="excluded class"):
        audit_valuation(parcels, assumptions)


def test_duplicate_pin_cannot_inflate_valuation(parcels, assumptions):
    with pytest.raises(ValueError, match="Duplicate PIN"):
        audit_valuation(pd.concat([parcels, parcels.iloc[[0]]]), assumptions)


def test_invalid_tax_inputs():
    for args in [(-1, 3, 7), (1, 0, 7), (1, 3, 101), (1, 3, 7, -1), (float("nan"), 3, 7)]:
        with pytest.raises(ValueError):
            tax_benchmark(*args)


def test_boundaries_partition_and_exclude_old_rectangle():
    data = json.loads(SOLDIER_FIELD_BOUNDARIES.read_text(encoding="utf-8"))
    features = {f["properties"]["id"]: f for f in data["features"]}
    geom = {k: shape(v["geometry"]) for k, v in features.items()}
    for k, g in geom.items():
        assert g.is_valid and not g.is_empty
        assert area_acres(g) == pytest.approx(features[k]["properties"]["gross_acres"])
    components = unary_union([geom["stadium"], geom["waldron"], geom["south_lot"]])
    assert components.equals(geom["stadium_and_parking"])
    assert geom["parking_only"].equals(unary_union([geom["waldron"], geom["south_lot"]]))
    assert geom["stadium"].disjoint(geom["parking_only"])
    assert 30 < area_acres(components) < 32
    assert 46 < area_acres(geom["connected_envelope"]) < 48
    assert area_acres(geom["legacy_box"]) > 270
    assert data["metadata"]["area_crs"] == "EPSG:26971"


def test_gross_parking_envelope_includes_internal_island():
    root = ET.fromstring("""<osm>
      <node id="1" lon="-87.62" lat="41.86"/><node id="2" lon="-87.61" lat="41.86"/>
      <node id="3" lon="-87.61" lat="41.87"/><node id="4" lon="-87.62" lat="41.87"/>
      <way id="10"><nd ref="1"/><nd ref="2"/><nd ref="3"/></way>
      <way id="11"><nd ref="3"/><nd ref="4"/><nd ref="1"/></way>
      <relation id="20"><member type="way" ref="10" role="outer"/>
      <member type="way" ref="11" role="outer"/><member type="way" ref="999" role="inner"/></relation>
    </osm>""")
    polygon, _ = component_geometry(root, "relation", "20")
    assert polygon.area == pytest.approx(0.0001)
    assert len(polygon.interiors) == 0
    # Removing one half of the exterior must not quietly yield an empty/smaller area.
    root.remove(root.find("way[@id='11']"))
    with pytest.raises(KeyError):
        component_geometry(root, "relation", "20")

"""
Tests for src.property_value — uplift calculation logic.
"""

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_FAR_LOOKUP = {
    "RS-1": 0.5, "RS-2": 0.65, "RS-3": 0.9,
    "RT-4": 1.2, "RM-5": 2.0, "RM-6": 4.4,
    "B1-1": 1.2, "B1-2": 2.2, "B2-3": 3.0,
}


def _make_parcel_row(**overrides):
    """Build a single-row DataFrame mimicking an enriched parcel."""
    defaults = {
        "pin": "1234567890",
        "ZONE_CLASS": "RS-3",
        "certified_tot": 25_000,   # assessed value  → market $250k
        "near_transit": False,
        "transit_dist_m": np.nan,
    }
    defaults.update(overrides)
    return pd.DataFrame([defaults])


# ---------------------------------------------------------------------------
# current_market_value
# ---------------------------------------------------------------------------

class TestCurrentMarketValue:
    """Tests for property_value.current_market_value."""

    def test_uses_certified_tot_and_ratio(self):
        from src.property_value import current_market_value
        from src.config import ASSESSMENT_RATIO

        row = _make_parcel_row(certified_tot=30_000).iloc[0]
        val = current_market_value(row)
        assert val == pytest.approx(30_000 / ASSESSMENT_RATIO)

    def test_prefers_estimated_market_value(self):
        from src.property_value import current_market_value

        row = _make_parcel_row(estimated_market_value=500_000, certified_tot=25_000).iloc[0]
        assert current_market_value(row) == pytest.approx(500_000)

    def test_falls_back_to_zone_median(self):
        from src.property_value import current_market_value
        from src.config import MEDIAN_VALUES_BY_ZONE

        row = _make_parcel_row(certified_tot=np.nan, ZONE_CLASS="RS-3").iloc[0]
        expected = MEDIAN_VALUES_BY_ZONE.get("RS-3", 250_000)
        assert current_market_value(row) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# zone_transition_factor
# ---------------------------------------------------------------------------

class TestZoneTransitionFactor:
    """Tests for property_value.zone_transition_factor."""

    def test_same_zone_returns_1(self):
        from src.property_value import zone_transition_factor
        assert zone_transition_factor("RS-3", "RS-3", SAMPLE_FAR_LOOKUP) == 1.0

    def test_exact_match_in_config(self):
        from src.property_value import zone_transition_factor
        from src.config import ZONE_TRANSITION_FACTORS

        factor = zone_transition_factor("RS-3", "RT-4", SAMPLE_FAR_LOOKUP)
        assert factor == ZONE_TRANSITION_FACTORS[("RS-3", "RT-4")]

    def test_far_ratio_fallback(self):
        from src.property_value import zone_transition_factor, FAR_APPRECIATION_RATE

        # "RS-1" → "RM-6" is not in ZONE_TRANSITION_FACTORS, should use FAR ratio
        factor = zone_transition_factor("RS-1", "RM-6", SAMPLE_FAR_LOOKUP)
        expected = 1 + ((4.4 / 0.5) - 1) * FAR_APPRECIATION_RATE
        assert factor == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# transit_multiplier
# ---------------------------------------------------------------------------

class TestTransitMultiplier:
    """Tests for property_value.transit_multiplier."""

    def test_close_distance(self):
        from src.property_value import transit_multiplier
        row = _make_parcel_row(transit_dist_m=200).iloc[0]
        assert transit_multiplier(row) == 1.15

    def test_medium_distance(self):
        from src.property_value import transit_multiplier
        row = _make_parcel_row(transit_dist_m=600).iloc[0]
        assert transit_multiplier(row) == 1.08

    def test_far_distance(self):
        from src.property_value import transit_multiplier
        row = _make_parcel_row(transit_dist_m=2000).iloc[0]
        assert transit_multiplier(row) == 1.00

    def test_boolean_fallback_true(self):
        from src.property_value import transit_multiplier
        row = _make_parcel_row(near_transit=True, transit_dist_m=np.nan).iloc[0]
        assert transit_multiplier(row) == 1.15

    def test_boolean_fallback_false(self):
        from src.property_value import transit_multiplier
        row = _make_parcel_row(near_transit=False, transit_dist_m=np.nan).iloc[0]
        assert transit_multiplier(row) == 1.00


# ---------------------------------------------------------------------------
# confidence_bounds
# ---------------------------------------------------------------------------

class TestConfidenceBounds:
    """Tests for property_value.confidence_bounds."""

    def test_bounds_bracket_projected(self):
        from src.property_value import confidence_bounds
        lo, hi = confidence_bounds(base_value=300_000, uplift_factor=1.18, years=10)
        projected = 300_000 * 1.18
        assert lo < projected < hi

    def test_wider_with_more_uncertainty(self):
        from src.property_value import confidence_bounds
        _, hi_narrow = confidence_bounds(300_000, 1.18, 10, appreciation_std=0.02)
        _, hi_wide = confidence_bounds(300_000, 1.18, 10, appreciation_std=0.10)
        # Wider std → wider interval
        assert hi_wide > hi_narrow


# ---------------------------------------------------------------------------
# composite_uplift
# ---------------------------------------------------------------------------

class TestCompositeUplift:
    """Tests for property_value.composite_uplift."""

    def test_no_change_returns_one(self):
        from src.property_value import composite_uplift
        assert composite_uplift(1.0, 1.0, 1.0) == pytest.approx(1.0)

    def test_weighted_average(self):
        from src.property_value import composite_uplift
        result = composite_uplift(1.10, 1.15, 1.20, w_transition=0.50, w_transit=0.25, w_dev=0.25)
        expected = 0.50 * 1.10 + 0.25 * 1.15 + 0.25 * 1.20
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# apply_scenario (integration-ish)
# ---------------------------------------------------------------------------

class TestApplyScenario:
    """Integration tests for apply_scenario."""

    def _run_scenario(self, key):
        from src.property_value import apply_scenario
        df = pd.DataFrame([
            {"pin": "A", "ZONE_CLASS": "RS-3", "certified_tot": 25_000, "near_transit": True},
            {"pin": "B", "ZONE_CLASS": "RS-3", "certified_tot": 20_000, "near_transit": False},
            {"pin": "C", "ZONE_CLASS": "RT-4", "certified_tot": 30_000, "near_transit": True},
        ])
        return apply_scenario(df, key, SAMPLE_FAR_LOOKUP, {"RS": 0.03, "RT": 0.035}, time_horizon=10)

    def test_baseline_no_rezoning(self):
        result = self._run_scenario("baseline")
        assert (result["current_zone"] == result["proposed_zone"]).all()

    def test_moderate_rezones_rs3(self):
        result = self._run_scenario("moderate")
        assert (result.loc[result["current_zone"] == "RS-3", "proposed_zone"] == "RT-4").all()
        assert result.loc[result["current_zone"] == "RT-4", "proposed_zone"].iloc[0] == "RT-4"

    def test_aggressive_uses_transit_flag(self):
        result = self._run_scenario("aggressive")
        near = result[(result["current_zone"] == "RS-3") & (result["near_transit"] == True)]
        far = result[(result["current_zone"] == "RS-3") & (result["near_transit"] == False)]
        # Near transit gets RM-5, elsewhere gets RT-4
        assert (near["proposed_zone"] == "RM-5").all()
        assert (far["proposed_zone"] == "RT-4").all()

    def test_output_has_required_columns(self):
        result = self._run_scenario("moderate")
        for col in ["pin", "current_value", "projected_value", "uplift_pct", "scenario",
                     "projected_lower", "projected_upper"]:
            assert col in result.columns, f"Missing column: {col}"

    def test_projected_value_exceeds_current_for_rezoned(self):
        result = self._run_scenario("moderate")
        rezoned = result[result["current_zone"] != result["proposed_zone"]]
        # With positive appreciation + upzoning, projected should be higher
        assert (rezoned["projected_value"] > rezoned["current_value"]).all()

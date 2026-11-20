# Epic 04 — Property Value Modelling

> **Status:** In Progress (scenario engines implemented; empirical validation incomplete)
> **Priority:** P1  
> **Owner:** —  

## Goal
Model current property values and project future assessed values under
upzoning scenarios using historical appreciation data and case-study-derived
uplift factors.

## Tasks

- [x] Process historical assessments → annual appreciation rates by zone (`src/process_historical.py`)
- [x] Build improved uplift model with multi-scenario support (`src/improved_uplift_model.py`)
- [x] Create zoning value impact analysis (`src/zoning_value_impact.py`)
- [ ] Complete real-value integration: `property_value.current_market_value` still falls back to zone medians / $250,000, and `zoning_value_impact.py` uses medians; quantify fallback coverage and use class-specific assessment levels
- [x] Replace 10 % blanket uplift with zone-transition-specific factors from `ZONE_TRANSITION_FACTORS`
- [x] Add provisional bounds to projections
- [ ] Correct bound centering: bounds omit appreciation included in point estimates; justify uncertainty or label as assumption sensitivity
- [x] Incorporate proximity-to-transit multiplier (distance decay from L stations)
- [x] Add optional gradient-boosting helper (requires scikit-learn, not declared)
- [ ] Train and evaluate against observed outcomes: default target is the rule-based `projected_value`, so current cross-validation is not independent empirical validation
- [x] Output per-parcel projected value to `data/processed/value_projections.csv`
- [ ] Validate on matched 2020 and 2024 values with a holdout: current helper labels the period but uses all-period `total_appreciation`, without filtering those years
- [x] Write tests for uplift calculation logic

## Acceptance Criteria
- [x] Model produces per-parcel projected values for ≥ 3 scenarios (baseline, moderate, aggressive)
- [ ] Demonstrate real-value coverage and explicitly label any imputed observations
- [ ] Define holdout evaluation metric, period, sample size and tolerance; no evidence establishes accuracy within one percentage point
- [x] `property_value.py` exports the long-format scenario schema
- [ ] Align exporters and map consumer: `prepare_map_data.py` expects wide `moderate_projected` / `moderate_uplift_pct` columns

## Dependencies
- Epic 02 (consistent assessment snapshots and complete joins)
- Epic 03 (enriched parcels with actual zoning attributes)

## Audit - 2026-11-19

Also reconcile fractional versus percent appreciation inputs, gaps between observed years, and assessor use classes versus actual zoning. Existing transit value can be counted again in the baseline. The two value engines apply PROPERTY_TAX_RATE to different bases. Historical association is not a causal rezoning effect. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

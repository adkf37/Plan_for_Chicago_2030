# Epic 04 — Property Value Modelling

> **Status:** In Progress  
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
- [ ] Fix flat \$250 K estimate — use actual per-parcel current assessed value
- [ ] Replace 10 % blanket uplift with zone-transition-specific factors from `ZONE_TRANSITION_FACTORS`
- [ ] Add confidence intervals / sensitivity bands to projections
- [ ] Incorporate proximity-to-transit multiplier (distance decay from L stations)
- [ ] Add regression model option (OLS / gradient boosting) as alternative to rule-based
- [ ] Output per-parcel projected value to `data/processed/value_projections.csv`
- [ ] Validate against actual 2020-2024 appreciation to calibrate model
- [ ] Write tests for uplift calculation logic

## Acceptance Criteria
- Model produces per-parcel projected values for ≥ 3 scenarios (baseline, moderate, aggressive)
- Projections use real current assessed values, not flat estimate
- Appreciation rates match historical data within ±1 %
- Output CSV has columns: `pin`, `current_value`, `projected_value`, `uplift_pct`, `scenario`

## Dependencies
- Epic 02 (assessment data)
- Epic 03 (enriched parcels with zone attributes)

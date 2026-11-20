# Epic 07 — Scenario Comparison Tool

> **Status:** In Progress
> **Priority:** P1  
> **Owner:** —  

## Goal
Enable side-by-side comparison of multiple upzoning / transit scenarios so
users can explore trade-offs between housing capacity, tax revenue, and
displacement risk.

## Tasks

- [x] Build initial scenario comparison script (`src/compare_zoning_scenarios.py`)
- [x] Implement RS-3 -> RT-4 rule in `src/compare_zoning_scenarios.py`
- [ ] Consolidate rules into a tracked scenario specification. `upzoning_scenario_changes.csv` contains generated polygon results, not input rules.
- [ ] Unify at least 3 named scenarios across comparison map, value engines and UI (three already exist in `property_value.SCENARIOS`)
- [ ] Generate per-scenario GeoJSON with modified zone attributes
- [x] Compute per-feature FAR differences for initial zoning comparison
- [ ] Compute housing/value deltas and area-weighted floor-area capacity; summed dimensionless FAR is not total development capacity
- [ ] Build comparison dashboard page (site/scenarios.html) with summary cards
- [ ] Implement configurable parameters (upzone radius, FAR multiplier) via UI sliders
- [ ] Add sensitivity analysis: how results change with ± 20 % appreciation assumption
- [ ] Export scenario comparison table to `data/processed/scenario_comparison.csv`
- [ ] Write tests for scenario generation logic

## Acceptance Criteria
- ≥ 3 scenarios with unique names and parameter sets
- Comparison map shows colour-coded deltas between any two scenarios
- Summary table lists total new units, avg value change, parcels affected per scenario

## Dependencies
- Epic 03 (zoning classification)
- Epic 04 (value projections)
- Epic 05 (transit scores for TOD scenarios)

## Reference (from Plan Outline § Future)
> Include scenario comparison dashboards (status quo, moderate reform, ambitious transformation)
> with configurable parameters for sensitivity testing.

## Audit - 2026-11-19

Status reflects checked-in implementation; unchecked acceptance criteria still require evidence. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

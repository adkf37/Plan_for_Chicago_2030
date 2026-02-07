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
- [x] Define upzoning rules in `data/reference/upzoning_scenario_changes.csv`
- [ ] Add ≥ 3 named scenarios (Baseline, Moderate TOD, Aggressive City-Wide)
- [ ] Generate per-scenario GeoJSON with modified zone attributes
- [ ] Compute delta metrics: Δ housing units, Δ assessed value, Δ FAR
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

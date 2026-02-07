# Epic 03 — Zoning Analysis Engine

> **Status:** In Progress  
> **Priority:** P1  
> **Owner:** —  

## Goal
Classify every parcel by zoning district, enrich with FAR / height / use data,
and produce city-wide zoning analytics ready for visualisation and modelling.

## Tasks

- [x] Create `data/reference/zoning_codes.csv` with district codes, FAR, max height, zone type
- [x] Build `src/zoning.py` — classify parcels by zoning district via spatial join
- [ ] Implement actual spatial join logic (parcel centroids → zoning polygons)
- [ ] Add computed columns: `zone_category` (Residential / Commercial / Mixed / Industrial / Parks / Transport)
- [ ] Calculate per-zone summary statistics (parcel count, total area, avg assessed value)
- [ ] Detect parcels currently zoned below transit-corridor potential (candidates for upzoning)
- [ ] Export enriched parcel dataset to `data/processed/parcels_enriched.geojson`
- [ ] Write unit tests for classification logic

## Acceptance Criteria
- Every parcel has a `zone_type`, `zone_category`, `far`, `max_height` attribute
- Summary CSV (`data/processed/zoning_summary.csv`) with aggregate stats per zone type
- ≥ 90 % join rate between parcels and zoning polygons

## Dependencies
- Epic 02 (parcel + zoning data downloaded)

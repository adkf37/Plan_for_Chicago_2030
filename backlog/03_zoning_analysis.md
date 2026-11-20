# Epic 03 — Zoning Analysis Engine

> **Status:** In Progress (engine implemented; city-wide acceptance unverified)
> **Priority:** P1  
> **Owner:** —  

## Goal
Classify every parcel by zoning district, enrich with FAR / height / use data,
and produce city-wide zoning analytics ready for visualisation and modelling.

## Tasks

- [x] Create local zoning lookup with district codes, FAR, max height, zone type
- [ ] Track `data/reference/zoning_codes.csv` so fresh clones have the lookup
- [x] Build `src/zoning.py` — classify parcels by zoning district via spatial join
- [x] Implement actual spatial join logic (parcel centroids → zoning polygons)
- [x] Add computed columns: `zone_category` (Residential / Commercial / Mixed / Industrial / Parks / Transport)
- [x] Calculate per-zone summary statistics (parcel count, total area, avg assessed value)
- [x] Detect parcels currently zoned below transit-corridor potential (candidates for upzoning)
- [x] Export enriched parcel dataset to `data/processed/parcels_enriched.geojson`
- [x] Write unit tests for classification logic

## Acceptance Criteria
- Report coverage and explicit unknown/not-applicable values for `zone_type`, `zone_category`, `far`, `max_height`; planned developments cannot all be assigned a universal numeric FAR.
- Summary CSV (`data/processed/zoning_summary.csv`) with aggregate stats per zone type
- Demonstrate at least 90% join rate on a Chicago-only denominator; county-wide parcels outside Chicago are not zoning-join failures.

## Dependencies
- Epic 02 (parcel + zoning data downloaded)

## Audit - 2026-11-19

The enrichment runner does not join the separate assessment dataset. Its area statistics can be zero when geometries are reconstructed points. Verify polygon availability, unique PINs, city filtering and assessed-value coverage. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

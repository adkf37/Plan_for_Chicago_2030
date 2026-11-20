# Epic 05 — Transit & Walkability Scoring

> **Status:** In Progress (proximity scoring implemented; network walkability deferred)
> **Priority:** P2  
> **Owner:** —  

## Goal
Score every parcel for transit accessibility and walkability to identify
the highest-impact corridors for upzoning and investment.

## Tasks

- [x] Implement CTA L station and bus route downloaders
- [ ] Verify local bus-route output and complete transit data delivery
- [x] Compute distance from each parcel centroid to nearest L station
- [x] Assign transit proximity tier (< 400 m / 400–800 m / 800 m–1.6 km / > 1.6 km)
- [x] Implement Metra station loading and integration
- [ ] Verify the configured Metra output exists and is used in the scored dataset
- [ ] Implement independent pedestrian/bicycle network accessibility. Current `compute_walk_score_proxy` is rail-distance decay; OSM analysis was removed. The master pipeline disables it and assigns a neutral score.
- [x] Implement a normalized composite TOD score
- [ ] Validate weights and avoid counting rail proximity twice as transit and walkability
- [x] Implement proposed transit extensions (subway lines from Plan_outline) as hypothetical station points
- [x] Score parcels under both current and proposed transit networks
- [x] Export `data/processed/transit_scores.csv`
- [x] Visualise transit shed buffers on map (400 m / 800 m rings)

## Acceptance Criteria
- Every parcel has `nearest_station`, `station_distance_m`, `transit_tier` attributes
- Composite TOD score is normalised 0–100
- Map shows concentric transit-shed rings around each L station

## Dependencies
- Epic 02 (parcel data)
- Epic 03 (enriched parcels)

## Reference (from Plan Outline)
> Couple transit proposals with GTFS feeds to estimate ridership, travel time savings…  
> Simulate micromobility networks and protected bike lane expansions…  
> Develop equity-focused mobility indicators.

## Audit - 2026-11-19

Distances are straight-line proximity, not walking routes, frequency, travel time, ridership or capacity. Proposed stations are illustrative points; they do not establish a feasible transport network. The old osmnx-fallback unit test no longer matches the implementation. See [current priorities](README.md) and [Soldier Field review](../docs/soldier_field_review.md).

# Epic 05 — Transit & Walkability Scoring

> **Status:** Not Started  
> **Priority:** P2  
> **Owner:** —  

## Goal
Score every parcel for transit accessibility and walkability to identify
the highest-impact corridors for upzoning and investment.

## Tasks

- [ ] Download CTA L station point layer + bus route polylines
- [ ] Compute distance from each parcel centroid to nearest L station
- [ ] Assign transit proximity tier (< 400 m / 400–800 m / 800 m–1.6 km / > 1.6 km)
- [ ] Download and integrate Metra commuter rail stations
- [ ] Add Walk Score / bike-score proxy using OSM network analysis (osmnx)
- [ ] Create composite "TOD Suitability Score" combining transit + walkability + current zoning gap
- [ ] Implement proposed transit extensions (subway lines from Plan_outline) as hypothetical station points
- [ ] Score parcels under both current and proposed transit networks
- [ ] Export `data/processed/transit_scores.csv`
- [ ] Visualise transit shed buffers on map (400 m / 800 m rings)

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

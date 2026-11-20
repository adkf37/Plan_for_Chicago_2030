# Epic 06 — Interactive Map Platform

> **Status:** In Progress (UI implemented; production acceptance unverified)
> **Priority:** P1  
> **Owner:** —  

## Goal
Deliver a production-quality interactive web map with toggleable layers,
rich tooltips, and performant rendering of city-wide data.

## Tasks

- [x] Build Folium-based city-wide zoning map (`viz/visualize_zoning.py`) — migrated to PyDeck
- [x] Build multi-layer interactive map (`viz/loading_data.py`) — migrated to PyDeck
- [x] Add SimCity 2000-inspired colour scheme and density-encoded opacity
- [x] Migrate Folium → MapLibre GL JS → Deck.gl + PMTiles (`site/map.html`, `site/js/map.js`)
- [x] Implement GeoJSON simplification/truncation and optional PMTiles generation via tippecanoe; Docker bundles tippecanoe
- [ ] Verify streaming PMTiles in browser and fix the deployed manifest; current tracked manifest points to ignored GeoJSON files
- [x] Add layer toggle panel (current zoning, proposed zoning, transit, values)
- [x] Implement before/after compare mode for current vs. proposed zoning (overlay toggle)
- [x] Implement parcel pop-up UI
- [ ] Verify value fields end to end after resolving projection-schema mismatch (Epic 04)
- [x] Implement story-map guided tours (auto-zoom to key corridors — 5 stops)
- [x] Add address search / geocoder control (Nominatim)
- [x] Optimise for mobile (touch gestures, responsive sidebar, hamburger menu)
- [x] Accessibility: keyboard nav, high-contrast mode, screen-reader descriptions, skip-link

## Acceptance Criteria
- Map loads in < 3 s on broadband with all city parcels
- Layer toggle shows/hides ≥ 4 overlays without page reload
- Pop-ups display contextual parcel data
- Record browser/mobile checks, measured load time, and accessibility review; these are acceptance targets, not verified outcomes.

## Dependencies
- Epic 02 (data)
- Epic 03 (enriched parcels)
- Epic 04 (value projections)
- Epic 05 (transit scores)

## Reference (from Plan Outline § 1)
> Deck.gl for interactive layering and toggles (migrated from MapLibre GL JS).  
> PMTiles vector tiles for large datasets (parcels). Geometry simplification and data clustering.

## Audit - 2026-11-19

Tracked PMTiles archives and UI code demonstrate implementation, not the <3 second load target or successful browser rendering. The separate Soldier Field map now regenerates from the analysis manifest, with sourced boundary alternatives and explicitly limited valuation/tax benchmarks. Its replacement does not establish acceptance of the city-wide map. See [current priorities](README.md) and the [boundary/valuation follow-up](../docs/soldier_field_boundary_and_value_update.md).

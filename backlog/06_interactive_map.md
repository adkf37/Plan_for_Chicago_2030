# Epic 06 — Interactive Map Platform

> **Status:** Done ✅  
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
- [x] Optimise GeoJSON with geometry simplification & coordinate truncation (`src/prepare_map_data.py`) — vector tiles deferred (tippecanoe requires Linux)
- [x] Add layer toggle panel (current zoning, proposed zoning, transit, values)
- [x] Implement before/after compare mode for current vs. proposed zoning (overlay toggle)
- [x] Add pop-ups with parcel details (PIN, value, zone, projected uplift)
- [x] Implement story-map guided tours (auto-zoom to key corridors — 5 stops)
- [x] Add address search / geocoder control (Nominatim)
- [x] Optimise for mobile (touch gestures, responsive sidebar, hamburger menu)
- [x] Accessibility: keyboard nav, high-contrast mode, screen-reader descriptions, skip-link

## Acceptance Criteria
- Map loads in < 3 s on broadband with all city parcels
- Layer toggle shows/hides ≥ 4 overlays without page reload
- Pop-ups display contextual parcel data
- Works on Chrome, Firefox, Safari (desktop + mobile)

## Dependencies
- Epic 02 (data)
- Epic 03 (enriched parcels)
- Epic 04 (value projections)
- Epic 05 (transit scores)

## Reference (from Plan Outline § 1)
> Deck.gl for interactive layering and toggles (migrated from MapLibre GL JS).  
> PMTiles vector tiles for large datasets (parcels). Geometry simplification and data clustering.

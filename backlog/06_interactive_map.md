# Epic 06 — Interactive Map Platform

> **Status:** In Progress  
> **Priority:** P1  
> **Owner:** —  

## Goal
Deliver a production-quality interactive web map with toggleable layers,
rich tooltips, and performant rendering of city-wide data.

## Tasks

- [x] Build Folium-based city-wide zoning map (`viz/visualize_zoning.py`)
- [x] Build multi-layer interactive map (`viz/loading_data.py`)
- [x] Add SimCity 2000-inspired colour scheme and density-encoded opacity
- [ ] Migrate from Folium → MapLibre GL JS for production performance
- [ ] Convert parcel GeoJSON to vector tiles (tippecanoe / PMTiles)
- [ ] Add layer toggle panel (current zoning, proposed zoning, transit, values)
- [ ] Implement before/after slider for current vs. proposed zoning
- [ ] Add pop-ups with parcel details (PIN, value, zone, projected uplift)
- [ ] Implement story-map guided tours (auto-zoom to key corridors)
- [ ] Add address search / geocoder control
- [ ] Optimise for mobile (touch gestures, responsive sidebar)
- [ ] Accessibility: keyboard nav, high-contrast mode, screen-reader descriptions

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
> MapLibre GL JS or Leaflet for interactive layering and toggles.  
> Vector tiles for large datasets (parcels). Geometry simplification and data clustering.

# Plan for Chicago Project Outline

## Overview

A comprehensive strategy to redesign Chicago’s land use and transportation, delivered via an interactive web map and accompanying website. The project will showcase current vs. proposed scenarios, quantify impacts (housing, property values, traffic), and provide policy context and case studies.

---

## 1. Interactive Map Features & Functionality

- **Open-Source Mapping Platform**  
  - MapLibre GL JS or Leaflet for interactive layering and toggles.
- **Base Map & Layers**  
  - OpenStreetMap basemap.  
  - Overlay layers for current/proposed zoning, transit, parcels, and property values.
- **Toggle Mechanism**  
  - Radio buttons or slider to switch between “Current” and “Proposed” layouts.
- **Zoning & Land Use Overlays**  
  - Color-coded polygons for zoning districts; separate styles for current vs. proposed.
  
- **Transportation Network Overlays**  
  - Existing roads, transit routes, bike lanes from OSM/CTA.  
  - Proposed subway lines, BRT corridors, car-free streets highlighted.
- **Population Density Overlays**  
  - Choropleths at parcel, ZIP code, and census tract levels.  
  - Dynamic switching based on zoom or user selection.
- **User Controls & UI**  
  - Sidebar or floating panel with layer toggles, legends, and info buttons.  
  - Pop-ups on feature click with contextual data (zoning, value, density).
- **Performance Optimization**  
  - Vector tiles for large datasets (parcels).  
  - Geometry simplification and data clustering.

---

## 2. Data Integration & Analysis Methods

- **Datasets & Preparation**  
  1. Cook County Parcel & Assessment Universe — parcel geometry, land use codes, assessed values.  
  2. Chicago Zoning Map — current zoning districts; create proposed zoning variant via attribute edits.  
  3. OpenStreetMap — roads, transit lines, building footprints.  
  4. Census Tracts — population data for density calculations.

- **Housing Density Categories**  
  - Define 8–10 types (e.g., Single-Family, Townhouse, Low‑Rise, Mid‑Rise, High‑Rise, Mixed‑Use).  
  - Classify parcels by existing type and assign proposed categories based on plan.

- **Property Value & Appreciation Model**  
  - Current values from assessor data.  
  - Appreciation factors from case studies (High Line, Cheonggyecheon, etc.).  
  - Rule-based or regression-based uplift model to project future assessed values.  
  - Map overlay for projected % change or absolute value increase.

- **Traffic Simulation & Analysis**  
  - Use open-source tools (A/B Street, SUMO) with OSM network.  
  - Baseline vs. proposed network simulations (car-free streets, transit-only lanes).  
  - Visualize traffic volume changes, rerouted flows, mode shifts.

- **Integration Workflow**  
  - Preprocess data with QGIS/Python (GeoPandas).  
  - Export optimized GeoJSON/vector tiles for web.  
  - Ensure consistent CRS (Web Mercator) across layers.

---

## 3. Website Structure & Policy Insights

1. **Introduction**  
   - Project goals, interactive map teaser, Burnham-era inspiration.
2. **Land Use & Zoning Reform**  
   - Why upzoning and mixed-use: benefits, Minneapolis example.
3. **Transportation & Mobility**  
   - Subway expansion, car-free streets, case studies (Times Square, Barcelona Superblocks).
4. **Housing Strategy**  
   - 8–10 housing types, density maps, affordability considerations.
5. **Economic Impact & Property Values**  
   - Value uplift modeling, tax base growth, anti‑displacement measures.
6. **Environment & Quality of Life**  
   - Emissions reduction, green infrastructure, health benefits.
7. **Case Studies Appendix**  
   - Summaries of relevant global examples (Seoul, Copenhagen, Paris).

- **Interactive Map Integration**  
  - Embed map with deep links to zoom locations, sync narrative sections with map state.
- **Technical Implementation & Hosting**  
  - Static site (HTML/CSS/JS) on GitHub Pages or Netlify.  
  - OSM tiles, self‑hosted vector tiles, MapLibre GL JS.
- **Design & UX**  
  - Responsive, accessible, use of call-outs, images, infographics.
- **Policy Justifications & Trade-Offs**  
  - Data-driven evidence, address concerns (gentrification, congestion).  
  - Transparent methodology and assumptions.
- **Maintenance & Community Involvement**  
  - Open-source code repository for updates and contributions.

---

*End of Project Outline*


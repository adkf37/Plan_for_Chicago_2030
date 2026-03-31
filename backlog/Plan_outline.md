# Plan for Chicago Project Outline

## Overview

A comprehensive strategy to redesign Chicago’s land use and transportation, delivered via an interactive web map and accompanying website. The project will showcase current vs. proposed scenarios, quantify impacts (housing, property values, traffic), and provide policy context and case studies.

---

## 1. Interactive Map Features & Functionality

- **Open-Source Mapping Platform**  
  - Deck.gl for interactive layering and toggles, PMTiles for vector tile serving.
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
  - OSM tiles, PMTiles vector tiles, Deck.gl.
- **Design & UX**  
  - Responsive, accessible, use of call-outs, images, infographics.
- **Policy Justifications & Trade-Offs**  
  - Data-driven evidence, address concerns (gentrification, congestion).  
  - Transparent methodology and assumptions.
- **Maintenance & Community Involvement**  
  - Open-source code repository for updates and contributions.

---

*End of Project Outline*

---

## Potential Enhancements and Future Improvements

- **Data & Analytical Depth**
  - Incorporate climate resilience datasets (heat islands, flood risk, tree canopy) to evaluate environmental justice outcomes alongside development proposals.
  - Add longitudinal assessor and rent registry data to track displacement pressures and calibrate anti-displacement strategies.
  - Integrate job accessibility metrics (30/45-minute transit sheds) to quantify economic opportunity gains.
  - Model greenhouse gas emissions impacts using mode share shifts and energy intensity assumptions for proposed land uses.
  - Include scenario comparison dashboards (status quo, moderate reform, ambitious transformation) with configurable parameters for sensitivity testing.

- **Transportation Modeling Enhancements**
  - Couple transit proposals with GTFS feeds to estimate ridership, travel time savings, and service frequency requirements.
  - Simulate micromobility networks (bike share, scooters) and protected bike lane expansions to assess first/last-mile connectivity.
  - Test curb management strategies (delivery zones, ride-hailing pick-up areas) to understand impacts on traffic flow and street life.
  - Develop equity-focused mobility indicators, such as transit access for low-income households and ADA-compliant infrastructure coverage.

- **Interactive Map & UI Features**
  - Provide story map tours with guided narratives that automatically adjust layer visibility and camera position.
  - Offer parcel-level comparison charts that visualize current vs. proposed density, value, and zoning allowances.
  - Enable user-submitted feedback pins or surveys directly on the map to crowdsource local knowledge.
  - Add accessibility features such as keyboard navigation, high-contrast mode, and screen-reader-friendly descriptions for map layers.
  - Implement mobile-first gestures (swipeable before/after map slider) for improved smartphone usability.

- **Website Content & Storytelling**
  - Introduce interactive calculators that let residents estimate housing affordability or tax impacts under different scenarios.
  - Expand policy sections with timelines for phased implementation and governance responsibilities.
  - Highlight community case studies through multimedia content (short videos, audio interviews) embedded alongside data visualizations.
  - Publish transparent methodology notebooks or reproducible pipelines linking code to narrative claims.

- **Community Engagement & Collaboration**
  - Create an open data portal with downloadable layers, metadata, and change logs to foster civic tech participation.
  - Schedule virtual workshops and mapathons, embedding live streaming or event information within the site.
  - Establish contribution guidelines and issue templates in the repository to streamline community feature requests and bug reports.
  - Partner with local organizations to co-develop neighborhood-specific overlays (cultural assets, social services, community plans).

- **Technical Infrastructure & Maintenance**
  - Automate data refreshes via scheduled ETL pipelines (GitHub Actions, cron jobs) that validate and deploy updated tiles.
  - Implement performance monitoring and analytics (Core Web Vitals, map interaction metrics) to guide iterative UX improvements.
  - Add comprehensive unit/integration tests for data processing scripts to ensure reproducibility across updates.
  - Containerize the development environment (Docker) to simplify onboarding and ensure consistent dependencies.
  - Explore progressive web app (PWA) capabilities for offline map exploration during community meetings without reliable internet.

---


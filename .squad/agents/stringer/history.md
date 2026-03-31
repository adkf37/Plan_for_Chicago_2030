# Stringer — Project History

## Core Context
- **Project:** Plan_for_Chicago_2030 — Python geospatial analysis for Chicago urban planning
- **User:** Aaron
- **Stack:** Python, GeoPandas, Pandas; site is static HTML/CSS/JS in `site/`
- **Mission:** Produce a public website with data-driven policy arguments for transit-oriented upzoning by 2030
- **Key constraint:** Do NOT download new external data. All data is already in the repo (data/geojson/, cache/).

## Key Paths
- `site/index.html` — main landing page
- `site/map.html` — interactive map page
- `site/css/` — stylesheets
- `site/js/` — JavaScript
- `site/assets/` — images and static assets
- `site/data/` — GeoJSON layers served to the map (parcels.geojson, zoning.geojson, transit_stations.geojson, proposed_zoning.geojson, manifest.json)

## Key Data Available for Storytelling
- 34,701 Chicago parcels with zoning classification, transit tier, TOD score, and uplift values
- Zone breakdown: Residential 82.2%, Commercial 8.6%, Mixed 7.5%, Industrial 1%
- Upzoning candidates: 10,028 parcels (28.9%)
- Transit Tier 1 (<400m from L stop): 5,896 parcels (17%)
- Uplift projections: Residential $1.32B · Commercial $269M · TOD $1.42B (10-year horizon)
- Parcel columns in site/data/parcels.geojson: zone_class, zone_category, near_transit, upzoning_candidate, transit_tier, tod_score, current_value, moderate_projected, moderate_uplift_pct

## Learnings

### Joined — 2026-03-31
First session. Reviewing site/ to understand current design state before proposing improvements.

### Full Site Audit — 2026-03-31
Completed a thorough audit of index.html, map.html, css/style.css, and js/map.js.

**Critical findings:**
- index.html is a developer dashboard, not a public policy site. Zero key stats are visible; the $1.32B uplift number and 10,028 upzoning candidates are nowhere on the page.
- The word "Backlog" appears in both the nav and as a section H2 on a supposedly public-facing page.
- `#00ff00` (neon green) is used for the Current Zoning layer swatch and legend — a prototype placeholder that never got replaced. The actual fill color is data-driven via `zone_color` field.
- "Transit Proximity — CTA L-station proximity scoring (planned)" is factually wrong: transit_tier data is in parcels.geojson with 5,896 Tier 1 parcels.
- Copyright says © 2025 (should be 2026). TOD legend endpoints say 0–100 but data range is 15–84.
- No hero copy, no CTA, no policy narrative arc. Copy is all process-focused, not outcome-focused.
- Guided tour buttons have no descriptions — just place names.

**Design system noted:** Navy #003366 / accent #cf2920 are solid civic colors. CSS vars are consistently used across both style.css and inline index.html styles. Good foundation to build on.

**Priority order:** Fix factual errors first (copyright, "planned" tag, Backlog label), then add stat callouts above the fold, then rewrite hero copy.

### Map Page UX Fixes — 2026-03-31
Applied full audit pass across map.html, style.css, and map.js:
- Replaced six neon debug legend colors (#00ff00, #0000ff, #ffff00, #ff0000) with accessible muted palette (sage green, calm blue, amber, softer red).
- Renamed "Parcel Values / TOD" → "TOD Opportunity Scores" in sidebar toggle and map.js LAYER_DEFS.
- Changed TOD score legend labels from 0/50/100 to Low/Mid/High (actual data range is 15–84).
- Added one-sentence tour descriptions below each Guided Tour button name.
- Removed non-functional Before/After Compare section from sidebar, map HTML compare-container, and JS wireUI wiring.
- Updated font stack to DM Sans with Google Fonts import.
- Fixed copyright to © 2026.

### Full index.html Redesign — 2026-03-31
Replaced the developer dashboard with a public-facing editorial policy brief. Key design decisions:

**Typography:** DM Serif Display (headings) + Libre Franklin (body). The serif display font gives editorial authority — newspaper/magazine feel without being stuffy. Libre Franklin is a workhorse sans-serif that stays out of the way. Avoided Inter/Roboto/Space Grotesk per skill guidelines.

**Layout architecture:** Seven-section narrative arc (Hero → Argument → Findings → Map → Analysis → Methodology → Footer) that tells a story from bold claim down to evidence. Each section alternates between cream/white/dark-navy backgrounds for visual rhythm and clear section boundaries.

**Hero treatment:** Oversized DM Serif headline with a highlighted `<em>` for the $3B figure in a warm coral (#ff8a82) against navy. Four-column stat bar uses 1px gap lines between cells rather than borders — more refined, less boxy. Subtle radial gradient glow (red at 8% opacity) in top-right creates atmospheric depth without being distracting.

**Color evolution:** Kept navy #003366 as primary and red #cf2920 as accent. Added navy-deep #001d3d for dark sections and header, cream #faf8f5 (warmer than the old #f9f9f9), and a warm rule color #d4cfc7 instead of gray. The warmer palette feels civic but approachable.

**Evidence cards:** Top-border accent (3px navy) instead of full border or shadow-heavy cards. Hover lift animation (translateY -3px) adds interactivity without JS. Emoji icons as a lightweight way to give visual anchoring without importing an icon library.

**Map preview:** CSS-only "map-like" visual using a grid overlay (repeating-linear-gradient at 40px intervals, barely visible) and a red radial glow. Suggests spatial data without needing an actual image or iframe.

**Content decisions:** Removed all developer language (backlog, pipeline, scrape, module, engine). Removed "planned" features and Equity Lens. Rewrote all copy in confident claim language for a non-technical audience. Explained "upzoning" and "FAR" in plain English. Used em-dashes and non-breaking spaces for typographic polish.

**Responsive:** Three breakpoints (900px, 768px, 480px). Evidence grid collapses to single column first, then stat bar to 2-up, then to single. Hero actions stack vertically on mobile. All sizes use clamp() for fluid type scaling.

**Accessibility:** Proper heading hierarchy (h1 → h2 → h3), ARIA labels on stat bar and map preview, semantic HTML5 elements throughout, aria-hidden on decorative emoji/arrows, role="banner" and role="contentinfo" on header/footer.

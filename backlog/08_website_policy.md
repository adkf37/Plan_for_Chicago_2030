# Epic 08 — Public Website & Policy Brief

> **Status:** Not Started  
> **Priority:** P2  
> **Owner:** —  

## Goal
Ship a static website (GitHub Pages / Netlify) that tells the Chicago 2030
story: embedded interactive map, narrative sections, data-driven policy
arguments, and case-study appendix.

## Sections (from Plan Outline § 3)

1. **Introduction** — project goals, Burnham-era inspiration, interactive map teaser
2. **Land Use & Zoning Reform** — upzoning benefits, Minneapolis 2040 case study
3. **Transportation & Mobility** — subway expansion, car-free streets, Barcelona Superblocks
4. **Housing Strategy** — 8–10 housing types, density maps, affordability
5. **Economic Impact & Property Values** — uplift model results, tax base growth
6. **Environment & Quality of Life** — emissions, green infrastructure, health
7. **Case Studies Appendix** — Seoul Cheonggyecheon, Copenhagen, Paris, etc.

## Tasks

- [x] Create `site/index.html` landing page skeleton
- [ ] Add responsive CSS framework (Pico CSS or Tailwind)
- [ ] Write Introduction narrative section
- [ ] Embed interactive map (iframe or MapLibre inline)
- [ ] Create section pages (land-use.html, transport.html, housing.html, …)
- [ ] Build infographics: housing type illustrations, before/after renderings
- [ ] Write case-study summaries with citations
- [ ] Add interactive calculator: "What would upzoning mean for your block?"
- [ ] Deploy to GitHub Pages with custom domain
- [ ] Add Open Graph / social sharing metadata
- [ ] Add analytics (privacy-friendly: Plausible or GoatCounter)

## Acceptance Criteria
- Site is live at a public URL
- All 7 narrative sections are populated
- Map is embedded and functional
- Lighthouse score ≥ 90 (Performance, Accessibility)

## Dependencies
- Epic 06 (interactive map)
- Epic 07 (scenario comparison)

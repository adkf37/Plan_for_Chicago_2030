# Implementation audit and current priorities

Reviewed November 19, 2026 against source, tracked files, local input snapshots,
and tests. A checked task means an implementation exists; it does not establish
that the epic's acceptance criteria or a public policy claim have been verified.
The outline is a long-term vision, not the critical path for the next article.

| Epic | What exists | What prevents completion |
|---|---|---|
| [01 Setup](01_repo_setup.md) | Central paths, environment loading, Docker, CI scaffolding | Reference CSVs ignored/untracked; test tooling absent from runtime install; lint failures |
| [02 Ingestion](02_data_ingestion.md) | Socrata, census and transit downloaders, caching, weekly workflow | Partial downloads can succeed; historical year/output/prerequisite contracts need repair |
| [03 Zoning](03_zoning_analysis.md) | Spatial joins, categories, FAR enrichment, summaries and tests | Chicago-only coverage, geometry quality, assessment join and fresh-clone reproducibility |
| [04 Values](04_property_value.md) | Multiple scenarios, rule-based projections, optional regression helper | Fallback values, classification/rate inconsistencies, invalid validation claims and output-schema mismatch |
| [05 Transit](05_transit_walkability.md) | Rail distance, tiers, proposed station points and TOD scores | Independent network walkability, accessibility validation and stale test |
| [06 Map](06_interactive_map.md) | Deck.gl UI, layers, tours, search, tile-generation code | Generated assets/manifest, value integration, browser/accessibility/performance evidence |
| [07 Scenarios](07_scenario_comparison.md) | Initial zoning/FAR comparison and separate value scenarios | Shared definitions, area-weighted capacity, dashboard and sensitivity UI |
| [08 Website](08_website_policy.md) | Substantial landing narrative and separate map | Verified claims/citations, deployment, portable asset links and remaining sections |
| [09 Quality](09_testing_cicd.md) | Tests, CI lint step, Docker and weekly ETL | Failing/stale tests, 74 lint findings, explicit dev dependencies and deployment checks |
| [10 Outreach](10_community_engagement.md) | Contributor guide linked from README | Issue templates, public methodology/data and actual outreach |

All ten epics are **In Progress**, at very different stages. This corrects both
the premature “Done” labels and the outdated “Not Started” labels. Zoning,
property-value and transportation modules are no longer placeholders. Existing
project guidance still describing them as placeholders should not be used as a
progress report.

## November 20 scope update

The [tracks-to-lake proposal](../docs/tracks_to_lake.md) supersedes the earlier footprint as the primary study. Price a deck over the existing rail alignment, allocate filled harbor and island land, and compare 100/150/200-foot shore sections. The blocks between Wabash, Michigan, Roosevelt and 14th supply the property benchmark. The public map presents one fixed proposal. McCormick Place is a later phase.

## Current milestone: Soldier Field article by November 26

Use the [analysis review](../docs/soldier_field_review.md) as the publication
gate. Finish one reproducible neighborhood comparison before expanding the
city-wide model. A defensible exploratory article can ship without a new transit
model, interactive scenario dashboard or full website redesign.

The [boundary/valuation follow-up](../docs/soldier_field_boundary_and_value_update.md)
now supplies sourced physical footprints, matching 2023 inputs, class-adjusted
market equivalents and fixed-rate tax benchmarks before exemptions. Net revenue
and legal development feasibility remain outside the result.

The [valuation recheck and map update](../docs/soldier_field_recheck.md) tests all
four reference quarters, adds an offline boundary explorer with drawing/export,
and introduces two labeled neighborhood concept images. The physical footprints
are not an agreed redevelopment boundary. Agree on that polygon before selecting
a publication headline or building a measured massing plan.

The user has since selected the **connected district**, with **40-story towers,
walkable blocks and public beaches**. Version-2 visuals follow that brief. Next:
draw the precise development and separate waterfront polygons, then model tower
count, floorplates, podium area and public-space allocation. Existing-neighborhood
value-per-acre figures do not yet value this building program.

| Date | Deliverable | Acceptance gate |
|---|---|---|
| Nov 19–20 | Freeze question, inputs and boundary alternatives | Same-year locations/assessments, named assessment stage, retained source manifest; explicitly disclose any justified vintage exception |
| Nov 20–21 | Review mapped reference and redevelopment boundaries | Include/exclude stadium, parking, roads, parkland and other uses explicitly; report gross acres and rationale |
| Nov 21–22 | Audit value conversion and comparator robustness | Class-level totals reconcile; incentive/exempt records resolved; compare at least one additional plausible reference area |
| Nov 22–23 | Generate tables, sensitivity and figure from the same run | Area/density assumptions labeled; no PIN-to-housing-unit conversion; no hand-entered financial map numbers |
| Nov 23–24 | Draft article and methods appendix | Separate observed values, assumed buildout and unmodeled effects; cite primary sources |
| Nov 24–25 | Reproduce and challenge headline | Clean run, test evidence, totals checked independently, objections and alternatives addressed |
| Nov 26 | Final editorial review | Publish as an exploratory land-use argument; omit any market-value or revenue headline that has not cleared its gate |

### Completed during this audit

- [x] Reconcile epic status and major checklist errors against implementation.
- [x] Inspect both local Soldier Field source snapshots and reconcile PIN/value totals.
- [x] Require explicit analysis year, preserve PINs and enforce one-to-one snapshot joins.
- [x] Report missing/zero values and classification/vintage differences.
- [x] Withdraw unsupported market/tax outputs and projected PIN counts from the script and archived map.
- [x] Add nine illustrative sensitivity cases, input fingerprints and 15 regression test cases.
- [x] Write publication critique, source notes and a dated delivery plan.
- [x] Replace candidate rectangle with sourced stadium/parking polygons and an explicitly broader envelope.
- [x] Align reference locations and assessments to 2023; reconcile all PINs and classes.
- [x] Audit assessment stage, class-specific levels, incentive uncertainty, equalizer and tax-rate basis.
- [x] Generate map/figure from the analysis manifest; pass 30 Soldier Field regression cases.
- [x] Recheck source assessments and area arithmetic; quantify all four reference quarters.
- [x] Bundle the Soldier Field map dependencies and imagery; add boundary drawing and export.
- [x] Add two AI-generated concept illustrations, with prompts and geographic limitations retained.

### Keep outside the article's critical path

City-wide regression, transit ridership simulation, deployment automation,
community feedback pins, climate modeling and a polished comparison dashboard.
Those remain worthwhile work, but none is a prerequisite for explaining this
specific neighborhood analogy honestly.

## Verification recorded during review

- The revised Soldier Field script ran successfully on the available local CSVs.
- All 34 Soldier Field regression cases pass after the comparator follow-up;
  scoped Ruff checks pass. The aligned 2023 real-data run regenerates the map.
  Separate browser checks cover offline operation, drawing/export and mobile layout.
- The initial review's suite excluding heavyweight local-data completeness tests had **94 passed,
  1 failed**. The failure is the existing `test_walk_score_fallback_without_osmnx`,
  which assumes the removed OSM implementation and depends on local CTA data.
- Repository-wide Ruff reports **74 findings**. Black is not installed in this
  environment, so its formatting check was not run.
- The full suite was interrupted during lengthy local-data checks after showing
  failures; no complete result or failure diagnosis was obtained for that run.
  Local-data acceptance and public deployment are not certified by this audit.

Do not replace these distinctions with a single completion percentage.

# Soldier Field analysis: publication review

Reviewed November 19, 2026. Target article date: November 26, 2026.

**Follow-up completed:** the first two findings and the source-vintage mismatch
are addressed by [the boundary and valuation update](soldier_field_boundary_and_value_update.md).
It replaces the broad rectangle with sourced scenarios and adds class-aware
market equivalents plus explicitly pre-exemption tax benchmarks. The initial
review below is retained as history; use the update for current results.

## Recommendation

Keep the central question: **what scale of taxable property might an ordinary
Chicago neighborhood represent on land currently devoted to a stadium and
parking?** Using an existing nearby neighborhood makes the assumption concrete
and understandable. The simple acreage calculation is easy to audit.

The existing implementation does not establish that redevelopment would create
$4.37 billion of additional wealth or $10.9 million of annual city revenue.
Those saved figures should not be the article's headline. An exploratory article
is achievable in a week if its scope stays with the neighborhood analogy and
its assumptions. A reliable net fiscal impact study is a separate deliverable.

## Findings that affect publication

### 1. Market value and tax revenue were not validly established — blocking

The original script divided every `certified_tot` by `ASSESSMENT_RATIO = 0.10`.
The reference area includes residential, commercial, industrial, vacant,
incentive and exempt/railroad classifications. A universal residential ratio
overstates market value for ordinary commercial/industrial property: dividing
the same assessed value by 10% instead of 25% produces 2.5 times the value.
This is a parcel-level error, not a claim that the aggregate is overstated by
2.5 times. The appropriate conversion must be established for each class and
assessment year, including special classifications and incentive phases.
[Assessor glossary](https://www.cookcountyassessoril.gov/glossary),
[classification guidance](https://www.cookcountyassessoril.gov/classifications-real-property).

The old tax formula simplified to `certified_tot * 0.025`. If 2.5% meant an
effective rate on market value, the extra assessment ratio was incorrect. If it
meant a statutory rate, the script lacked equalization, exemptions and the
applicable tax-code rate. Actual tax calculations apply rates to taxable
equalized assessed value. `certified_tot` also differs from the available
`board_tot` stage, so the assessment stage must be selected and justified.
[Assessor explanation of the tax system](https://www.cookcountyassessoril.gov/cook-county-property-tax-system),
[assessment and tax-bill FAQ](https://www.cookcountyassessoril.gov/frequently-asked-questions).

Even a valid estimate of gross property-tax payments would not automatically
equal additional City of Chicago revenue. Establish taxing-district allocation,
levy/rate effects, exemptions and any applicable TIF treatment before making
that claim. A larger tax base is not by itself a forecast of higher collections.
[Cook County property-tax process](https://propertytaxreform.cookcountyil.gov/how-it-works/property-tax-process).

**Change made:** the script now reports observed assessed values and a labeled
assessed-value analogy. It withholds market-value and tax outputs until a
class/stage-specific conversion and fiscal model are supported. No substitute
tax rate was guessed. This intentionally changes the CSV schema.

### 2. The redevelopment footprint is a rectangle, not a site plan — blocking

`SOLDIER_FIELD_AREA` covers approximately **273.68 gross acres**, while the
reference rectangle covers **304.46 acres**. The code has no polygon delineating
stadium/parking land and no exclusions for other uses or constraints. Therefore
“Soldier Field + south parking footprint” is stronger than the spatial method
supports. The configured edges and street annotations need visual review.

Draw and retain at least a stadium/parking boundary and a broader alternative,
with explicit treatment of roads, public space, existing facilities and other
land. Calculate area in a suitable projected CRS. The rectangle-area
approximation is a smaller concern than selecting the correct land in the first
place.

Keep denominators consistent. Reference value per **gross neighborhood acre**
already reflects streets and open space within that neighborhood. Do not apply
an additional generic street deduction as if it were net lot density. First
identify the gross area that would actually become the new neighborhood; then
vary development intensity separately.

Soldier Field is owned by the Chicago Park District. Lakefront development is
subject to a specific protection framework. Treat ownership, public access,
parkland and necessary approvals as feasibility questions requiring review;
this analysis does not establish that private redevelopment is permitted.
[Soldier Field ownership](https://www.soldierfield.com/about),
[Chicago lakefront ordinance](https://codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2680206),
[parks/open-space zoning provisions](https://codelibrary.amlegal.com/codes/chicago/latest/chicago_il/0-0-0-2681833).

### 3. The inputs have different years — material, now explicit

Both filenames end in `20250430`, but their `tax_year` columns differ:

| Input | Rows in local file | Tax year |
|---|---:|---:|
| Parcel Universe | 1,864,107 | 2024 |
| Assessed Values | 1,864,161 | 2023 |

The original merge ignored parcel year and did not restrict assessment year.
Inspection found **no duplicate PIN/year records in these snapshots**, so there
is no evidence that duplicate joins inflated this particular saved result.
Nevertheless, a future multi-year input could silently multiply values.

Within the reference rectangle, all 13,590 parcel PINs matched assessments,
and **15 classifications differ** between the two snapshots. The revised loader
requires explicit years, preserves leading zeros, rejects duplicate snapshot
keys, validates a one-to-one merge, and retains both years and classifications.
Its default requires same-year locations. The existing mismatched files can be
used only by explicitly selecting both years, with a prominent output warning.

Before publication, obtain aligned snapshots or explain why the mismatch is
acceptable after examining changed/split/retired PINs. A successful join alone
does not prove same-year geographic completeness.

### 4. PINs are not homes; assessed value is not density — blocking for housing claims

The old projection scaled the number of positive-value tax accounts to produce
11,993 estimated “parcels.” The reference parcel snapshot contains 12,020 records
classified as 299 (condominiums), but a tax account is not uniformly a dwelling,
a building or a land lot. Condominiums can include parking/storage/common-area
records; rental buildings can contain many dwellings under one PIN.
[Assessor condo dataset documentation](https://catalog.data.gov/dataset/assessor-residential-condominium-unit-characteristics).

The code also never measures dwelling units/acre, floor area or FAR for this
comparison. “Matches the reference neighborhood's observed assessed value per
gross acre” describes its operation accurately. “Same housing density” is an
additional assumption needing unit/building data. Projected PIN counts have
been removed; do not relabel them as homes.

### 5. Gross stabilized value is not net benefit or a 2030 forecast — blocking

The calculation transfers a stock of assessed property value to another area.
It does not model demolition, construction, infrastructure, remediation,
financing, operations, stadium income, existing obligations, public amenities,
lost uses, demand, development timing or displaced investment elsewhere.
There is no current-site counterfactual subtraction. Assessed value of future
buildings also includes capital that somebody must spend to build them.

Use “illustrative value at a comparable completed buildout,” with the assessment
year stated. Avoid “would add,” “pays for itself,” “annual city windfall” and
“by 2030.” Compare redevelopment with at least retaining/reusing the stadium or
preserving/improving public open space in the discussion. A recommendation
requires weighing those alternatives, not just identifying a taxable use.

### 6. One comparator and hand-entered map figures are fragile — material

The nearby comparator is a reasonable starting point, but location, building
age/type, lake access, amenities, development history and land mix differ.
Repeating one neighborhood's assessed value density is an assumption, not an
estimated causal effect of extending streets. Add at least one alternative
reference geography and explain the choice before selecting a headline.

The tracked `maps/soldier_field_analysis_map.html` embedded the previous numbers
by hand. The analysis has no map-generation step. The map now visibly identifies
itself as an archived boundary illustration and withholds financial and
projected-PIN estimates. A publication figure should be generated from the same
run manifest as the article table; the static map is not yet that artifact.

## Reconciled local result

These are diagnostics from the existing rectangles and mismatched vintages,
not publication-ready redevelopment forecasts:

| Metric | Result |
|---|---:|
| Reference PINs / matched assessments | 13,590 / 13,590 |
| Positive-value / zero-value / missing-value PINs | 13,343 / 247 / 0 |
| Reference certified assessed value | $485,664,537 |
| Reference Board of Review total (separate diagnostic) | $476,676,835 |
| Reference certified assessed value per gross acre | $1,595,143 |
| Candidate rectangle / reference rectangle | 273.68 / 304.46 acres |
| Full-rectangle assessed-value analogy | $436,558,537 |

The previous $4,365,585,368 market-value estimate and $10,913,963 annual tax
estimate are withdrawn. The $436.6 million figure is **assessed value**, with
all the footprint/comparator limitations above; it is not a corrected market
value estimate or net new tax base.

For robustness, the code exports a 3-by-3 grid of gross neighborhood area shares
(50%, 75%, 100%) and value-density factors (0.8, 1.0, 1.2). These are deliberately
illustrative assumptions, not confidence intervals or evidence that any share
is feasible. Boundary review must precede a preferred scenario.

## Reproduction and code changes

```powershell
python -m src.soldier_field_analysis --assessment-year 2023 --parcel-year 2024
python -m pytest tests/test_soldier_field_analysis.py -q
python -m ruff check src/soldier_field_analysis.py tests/test_soldier_field_analysis.py
```

Omitting `--parcel-year` requires the assessment year in both files and fails
with the current parcel snapshot. Invalid or duplicate data now stops the run
instead of silently producing a headline. The loader reads CSV chunks and keeps
the selected study area, avoiding a full-county in-memory merge.

Outputs under `analysis_results/` are a revised summary CSV, a sensitivity CSV,
and `soldier_field_run.json` containing input SHA-256 fingerprints, file sizes,
bounds, years, assessment stage, diagnostics and assumptions. A small checked-in
[audit snapshot](soldier_field_audit_2026-11-19.json) preserves the reviewed run;
raw data and regenerated outputs remain ignored. The old financial CSV fields
are intentionally absent; downstream consumers must use the new labeled fields.

The 15 regression cases cover year selection, PIN normalization, duplicate-key
rejection, missing/zero/invalid values, empty reference selection, proportional
scenario scaling, CSV loading and provenance output. They pass. These checks
establish accounting behavior, not the economic validity of the analogy.

The broader non-data suite has 94 passes and one existing failure in the removed
OSM-fallback behavior. A full-suite run showed failures during lengthy local-data
checks and was interrupted before producing a complete summary; those data
failures have not been diagnosed. Repository-wide lint still has 74 findings.
Those issues are recorded in the backlog; the changed analysis and test files
pass Ruff.

## Article structure and publication gates

Working title: **What would an ordinary Chicago neighborhood look like at
Soldier Field?**

1. Open with the land-use question and why a nearby built neighborhood is an
   understandable comparator. Present the grid extension as a thought experiment.
2. Show an audited map of the candidate land and reference areas, including
   public-space exclusions and alternatives.
3. Explain the arithmetic in one sentence: observed value per gross reference
   acre multiplied by assumed gross neighborhood acres and a stated intensity
   factor. Name the value measure and year beside every figure.
4. Show a short sensitivity table and another comparator. Explain what drives
   the range without calling it a statistical confidence interval.
5. Address public ownership/access, stadium reuse, costs, development timing and
   market demand. State what the model cannot decide.
6. Close with the policy question the comparison raises and the evidence needed
   to choose among alternatives. Link the reproducible methods and source notes.

Suggested framing: “This comparison asks what scale of assessed property value
an existing neighborhood represents on a similarly sized area. It does not
estimate net city revenue or establish that this land is available for private
development.”

- [ ] Boundaries and gross-area denominators reviewed and retained as data.
- [ ] Source vintages aligned or a documented exception justified.
- [ ] Assessment stage and class-specific market conversion reconciled if a market-value figure is used.
- [ ] Fiscal assumptions, district allocation and counterfactual verified if a revenue figure is used; otherwise omit it.
- [ ] Comparator choice and sensitivity shown; no housing-unit inference from PINs.
- [ ] Article tables and figure generated from one reproducible run.
- [ ] Independent arithmetic check and editorial review completed.

See the [dated one-week plan](../backlog/README.md). None of these gates requires
finishing the entire Chicago 2030 platform.

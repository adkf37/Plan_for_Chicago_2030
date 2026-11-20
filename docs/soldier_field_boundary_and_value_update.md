# Soldier Field: boundary and valuation corrections

Updated November 19, 2026. This supersedes the boundary, snapshot and arithmetic
limitations in the [initial review](soldier_field_review.md). It does not turn
the neighborhood analogy into a development feasibility study or net fiscal forecast.

**Subsequent recheck:** [the boundary/comparator explorer](soldier_field_recheck.md)
shows why the narrow footprint result is not a settled valuation for the intended
neighborhood. It adds all four reference quarters, drawable boundaries, offline
imagery and initial concept visuals. The arithmetic below remains the original
full-reference scenario calculation.

## Results

The selected physical footprints total **30.56 acres**, not the old 273.68-acre
rectangle. Applying the reference neighborhood's class-adjusted value per gross
acre yields approximately **$429–430 million** of assessment-implied market
equivalent at a comparable completed buildout. This is a 2023 valuation basis,
not new wealth, a sale-price forecast or a 2030 completion estimate.

| Scenario | Gross acres | Assessment-implied market equivalent | Annual combined tax benchmark, before exemptions | City corporate-rate component, before exemptions |
|---|---:|---:|---:|---:|
| Waldron Deck + South Lot; retain stadium | 16.08 | $225.6–226.4m | $5.32m | $1.22m |
| Stadium + both southern parking facilities | 30.56 | $428.8–430.4m | $10.10m | $2.33m |
| Broader connected envelope | 47.11 | $661.1–663.4m | $15.57m | $3.59m |

The narrow market-value range reflects only the documented assessment-level
uncertainty for two Class 7b properties. It does **not** capture uncertainty about
the comparator, future building mix, construction, demand, timing or land availability.
The separately exported 0.8/1.0/1.2 density cases address assumed intensity, not
statistical confidence.

The tax columns hold 2023 rates fixed and deduct no exemptions. They are not
observed bills, additional collections, a City budget forecast or net fiscal
benefits. The city corporate-rate component also excludes the separately listed
library and school-building funds. These are arithmetic benchmarks that can be
reproduced, not a finding that the City receives the combined tax charge.

## 1. Boundary correction

The [retained GeoJSON](../data/reference/soldier_field/boundaries.geojson) contains
three source components, three scenarios, the fixed reference rectangle and the
withdrawn rectangle for comparison. Every area is calculated in **EPSG:26971**
(metres), divided by 4,046.8564224 square metres per acre.

| Component | Gross acres | Retained source |
|---|---:|---|
| Stadium exterior | 14.48 | [OSM way 24587933, version 24](https://www.openstreetmap.org/way/24587933/history/24) |
| Waldron Deck exterior | 6.06 | [OSM relation 10655279, version 7](https://www.openstreetmap.org/relation/10655279/history/7) |
| South Lot exterior | 10.02 | [OSM relation 17644593, version 2](https://www.openstreetmap.org/relation/17644593/history/2) |

The area is land under each facility, counted once. A two-level deck does not
provide two acres of land per footprint acre. Internal parking islands and
circulation stay inside gross footprints. North Garage, museum grounds, harbor
parking/water, McCormick Place parking and Northerly Island are excluded.

The tight scenario is a union of three disjoint footprints. It excludes the
roads, plazas and green space between them. The broader alternative is their
**projected convex hull**, adding **16.55 acres** of intervening land. That is a
transparent geometric alternative, not a designed street grid or a finding that
the connecting public space should be redeveloped. Its inclusion rule is stored
with the geometry. Neither alternative establishes parcel ownership, legal
availability or necessary approvals.

Locations/names were cross-checked against the Bears' [official parking map](https://static.clubs.nfl.com/image/upload/v1691695208/bears/wjsgu0iueea0q5k9rcg2.pdf)
and the [stadium directions page](https://www.soldierfield.com/plan-your-visit/directions).
The generated [boundary figure](../reports/visualizations/soldier_field_boundaries.png)
was inspected over Esri World Imagery. Imagery is context, not a measurement or
a survey; its acquisition date is not established. OSM component edits retained
in this snapshot date to June/September 2026. The monetary and reference parcel
location inputs are separately aligned to 2023.

The reference rectangle remains deliberately fixed, with all its streets and
open space in the denominator. Its projected area is **304.25 acres**, slightly
different from the former degree-based approximation of 304.46. Do not apply a
second generic street deduction to its value per gross acre.

## 2. Property-value correction

The run now joins **2023 locations to 2023 assessments**. The source download is
filtered to the fixed reference bounds, ordered by PIN, checked against the
server's count, and checked for duplicates. All **13,590** location records match;
there are **13,343 positive assessments**, **247 zero assessments**, no missing
values and **zero class disagreements** between these aligned snapshots.

The source is [Assessor Parcel Universe (Historical)](https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.json).
Query and fingerprint are retained in [parcel_source.json](../data/reference/soldier_field/parcel_source.json).
This also resolves the initial review's third bullet, the vintage mismatch.

The main financial calculation explicitly uses **`board_tot`**, the Board of
Review stage in the existing 2023 export, with no fallback to a different stage:

| Reconciliation | Amount |
|---|---:|
| Certified assessed value, original stage | $485,664,537 |
| Board of Review assessed value, selected stage | $476,676,835 |
| Difference between stages | $8,987,702 |
| Class-adjusted market-equivalent total | $4,268,992,476–$4,284,417,226 |

The stage is later than Assessor certification, but the export is not asserted to
contain all subsequent certificates of error or final billing adjustments.

The [sourced assumptions](../data/reference/soldier_field/valuation_assumptions.json)
map each observed class explicitly. The standard vacant/residential/apartment
classes in this sample use 10%; ordinary commercial/industrial classes use 25%.
Class 991 uses the Class 9 rental-housing incentive level of 10%. EX/RR records
have zero assessed contribution here; their underlying real estate is **not**
being declared economically worthless. The result describes assessment-implied
taxable property, not the market value of all land in the rectangle.
[Assessor glossary](https://www.cookcountyassessoril.gov/glossary),
[Class 3 bulletin](https://prodassets.cookcountyassessoril.gov/s3fs-public/form_documents/cls3b.pdf),
[Class 9 bulletin](https://prodassets.cookcountyassessoril.gov/s3fs-public/2024-06/Class9EligibiltyBulletin2024.pdf).

Two Class 748 records have a combined $3,084,950 assessed value. The Assessor's
[class dictionary](https://github.com/ccao-data/data-architecture/blob/master/dbt/seeds/ccao/ccao.class_dict.csv)
identifies these as Class 7b. The County specifies 10%, 15% and 20% levels at
different incentive phases. The available records do not identify their phase,
so the calculation uses the documented endpoints: `AV / 0.20` through `AV / 0.10`.
It does not silently assign a convenient rate. The resulting uncertainty is
$15,424,750 at reference-area scale, approximately $1.55 million in the tight
candidate scenario. [County incentive schedule](https://www.cookcountyil.gov/service/property-tax-incentives).

Unknown classes, a positive assessed value for an excluded class, missing Board
values, duplicate PINs and mismatched vintages stop the financial run. A class
audit CSV makes the contributions and assessment-level assumptions inspectable.

## 3. Tax correction and its limits

The implemented formula is:

```text
EAV = assessed value × equalization factor
tax benchmark = max(EAV − eligible exemption EAV, 0) × rate_percent / 100
```

For the candidate scenarios, the stated assumption is zero exemption deductions.
The fixed 2023 equalizer is **3.0163**, verified against the
[Illinois Department of Revenue announcement](https://taxarchive.illinois.gov/research/news/2023-cook-county-final-multiplier-announced.html).
The Clerk's 2023 report supplies the **6.995% general Chicago composite rate**
and **1.612% city corporate rate**. The calculation applies these to equalized
assessed value, not to market value. [Clerk report, PDF page 26](https://www.cookcountyclerkil.gov/sites/default/files/pdfs/2023%20Tax%20Rate%20Report.pdf#page=26).

Separately, the reference-area diagnostic uses the actual 2023 tax-code rate for
each PIN: 6.995% or 7.018% for the 13 codes present, verified against pages
183–185 of the Clerk's rate summary. Its approximately $100.90 million result is
still **before exemptions**, not a reconstructed total of actual tax bills.
The older Socrata tax-rate datasets stop in 2013; they were deliberately not
used for 2023 rates. [Clerk tax-code summary](https://www.cookcountyclerkil.gov/sites/default/files/pdfs/2023%20Tax%20Code%20Rate%2010%20year%20Summary.pdf#page=183).

The candidate's future tax code is not established; the general city rate is a
declared benchmark. No exemption eligibility, TIF allocation, levy response,
collection losses, existing-site revenues or public-service costs are inferred.
Resolving those requires a separate fiscal model. Therefore the original
“annual city revenue” claim stays withdrawn even though the tax arithmetic is
now explicit and correct for the stated assumptions.

## Reproduce and inspect

```powershell
python -m src.prepare_soldier_field_inputs --with-aerial
python -m src.soldier_field_analysis --assessment-year 2023
python -m pytest tests/test_soldier_field_analysis.py tests/test_soldier_field_valuation.py -q
```

Preparation caches public source responses, verifies the reference row count,
assembles polygons and writes small retained source records. `--refresh` fetches
new source versions and can change boundaries; review those changes before
using a new run in the article. The retained GeoJSON preserves the reviewed
geometry, so subsequent analysis does not require live OSM requests.

The analysis exports the summary, nine scenario/intensity cases, class audit and
a run manifest with input fingerprints. It regenerates the
[interactive map](../maps/soldier_field_analysis_map.html) and boundary figure
from that same manifest. Monetary values are no longer hand-entered into the map.
The [retained audit snapshot](soldier_field_boundary_value_audit_2026-11-19.json)
records the reviewed results and input fingerprints alongside these notes.

**Verification:** 30 Soldier Field regression cases pass, including mixed-class
conversion, incentive bounds, exemption ordering, invalid-input rejection,
duplicate accounting, scenario composition and gross land-area treatment.
The real-data run reconciled every reference PIN. The unrelated repository-wide
test/lint issues identified in the initial review are not claimed resolved.

## What remains before the article

The first two findings now have reproducible physical-area scenarios and a
class-aware valuation / explicitly limited tax benchmark. The next analytical
priority is a second comparator and an assessment of how comparable its building
mix and public-space share are. Keep property values and tax illustrations
separate from claims about net benefit, development approval, housing-unit yield
and a 2030 delivery schedule.

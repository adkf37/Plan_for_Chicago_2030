# Soldier Field: rechecking the low estimate

The earlier $429–430 million result is reproducible for the **30.56-acre physical
footprints** and the **full original reference's average value per gross acre**.
It is not an established valuation for the neighborhood the user intends to
build. Treating those physical footprints as the settled redevelopment boundary
was too restrictive. The boundary still needs agreement.

**Confirmed design direction:** the user selected the stadium, parking and
connecting roads/open space, with roughly **40-story buildings, walkable blocks
and public lakefront beaches**. The 47.11-acre connected envelope is now the
working primary analogy in both script output and map. It is still a geometric
proxy: the exact development polygon and separate beach/access sites remain to
be drawn. The user also confirmed that the HTML map now works.

## What the second check found

- All 13,590 reference PINs still reconcile to the 2023 assessment snapshot.
- Five targeted live-source spot checks, covering classes 299, 391, 517, 748 and
  991, match the local 2023 Board of Review amounts exactly. These are selected
  checks, not a statistical sample or verification of all source assessments.
- The original $4.37 billion figure relied on roughly 274 acres. Reducing that
  to 30.56 acres explains most of the fall in value. The corrected property-class
  conversion and choice of assessment stage account for a smaller change.
- The reference average is about **$14.03–14.08 million per gross acre**.
  At its lower endpoint, a $1 billion analogy requires about **71.27 gross acres**
  at that same intensity. This is arithmetic, not a preferred development target.
- An independent ellipsoidal-area calculation agrees with the projected site
  areas to within 0.01%. There is no evidence of a large units/acreage conversion
  error. The land selected is the consequential question.

The [retained recheck audit](soldier_field_recheck_audit.json) includes the source
query/results, independent area checks, and all scenario/comparator combinations.
The [Assessor's explanation](https://www.cookcountyassessoril.gov/assessor-property-details)
confirms the usual 10% residential and 25% commercial assessment levels.
Special-class treatment remains as documented in the prior methods.

## Comparator sensitivity, without picking just the expensive blocks

The original rectangle is split at its geographic midpoints into **all four
quarters**. Each PIN belongs to exactly one quarter, including points exactly
on a dividing line. All areas retain streets, open land and zero-assessment
records. No quarter is declared the right comparator.

| Reference | Gross acres | PINs | Market equivalent per gross acre, lower incentive endpoint |
|---|---:|---:|---:|
| Full original area | 304.25 | 13,590 | $14.03m |
| Northwest quarter | 76.06 | 2,794 | $10.77m |
| Northeast quarter | 76.06 | 6,279 | $28.81m |
| Southwest quarter | 76.07 | 829 | $3.81m |
| Southeast quarter | 76.07 | 3,688 | $12.74m |

The northeast is materially more valuable per gross acre. Using the **47.11-acre
connected alternative** yields about **$661–663 million** at the full-reference
average, versus **$1.36 billion** at the northeast quarter's average. The other
quarters are deliberately retained in the map so the upward sensitivity is not
presented selectively.

This is **internal sensitivity**, not independent validation or evidence that
the proposed buildings would achieve any of these values. A genuine second
neighborhood, comparable building mix, parcel/building characteristics and sale
or income evidence still need examination. Neither the assessments nor these
illustrative renderings establish a new-construction premium or a current-dollar
market price. The narrow incentive range must not be mistaken for forecast
uncertainty.

## Map repair and boundary discussion

Open [the rebuilt map](../maps/soldier_field_analysis_map.html) directly in a
browser from this checkout. Keep the adjacent `site/` folder: the HTML uses its
local Leaflet/Proj4 files, imagery and concept assets. No API key is required.
The initial map uses a bundled, attributed Esri aerial with retained bounds and
source metadata. Optional online street tiles fall back to that image on failure.

The pre-change Soldier Field page rendered without a key in our browser test;
the user's reported failure was not reproduced. This repair removes its CDN
and live-basemap dependencies rather than claiming a diagnosed missing-key bug.
It does not repair or certify every other generated map in the repository, and
it has not been published to a remote host.

Controls now support:

- Parking-only, physical-facility and connected-neighborhood outlines. The
  connected alternative opens by default and is the script's working primary
  scenario after the user's scope clarification; all three remain exported.
- A toggle for the old rectangle, shown solely for spatial comparison.
- All four reference quarters, with the blue outline following the selection.
- A separately labeled value-intensity multiplier.
- Drawing a custom polygon, recalculating EPSG:26971 acreage, and saving GeoJSON.
  Self-crossing and repeated-corner polygons are rejected. A drawn outline is a
  user assumption and may include water, roads or other uses; it is not screened
  for feasibility. Export it to retain it; drawings are not persisted automatically.

The generated result states **estimated market value at comparable buildout**,
with assessment-derived and 2023-basis qualifications. Assessed value and
pre-exemption tax benchmarks are separated in the methods disclosure.

## First visual direction

Two version-2 images made with the built-in image-generation tool are integrated
below the map: an aerial concept and a street-level view. They follow the user's
40-story direction, with towers set above illustrative 4–6-story street walls,
shops and walkable blocks. The aerial includes a separate public beach on the
lake-facing shore beyond the harbor. Beach area, access, feasibility and cost are
not included in the current stadium-area polygon or valuation. Earlier mid-rise
images and their prompts remain in the asset folder as superseded exploration.

These are **AI-generated atmosphere studies**, not georeferenced visualizations,
measured capacity studies or approved designs. The aerial stylizes geography,
including shoreline and landmarks; use the actual map to discuss the boundary.
There is no inferred housing count, FAR, cost or property value from either image.
The next step is a measured block/massing plan with tower count, floorplates,
podium area, public-space allocation and housing mix. A 40-story height target
does not supply those quantities or justify multiplying existing value by a
story-count ratio. The map now explicitly labels the financial figures as an
existing-neighborhood analogy, not a valuation of the tower concept.

Saved assets and exact prompts:

- [Aerial concept v2](../site/assets/soldier-field/neighborhood-aerial-40-story-v2.png)
- [Street concept v2](../site/assets/soldier-field/neighborhood-street-40-story-v2.png)
- [Full prompt set and limitations](../site/assets/soldier-field/concept-prompts-v2.json)
- [Confirmed design brief](../data/reference/soldier_field/design_brief.json)

## Reproduce

```powershell
python -m src.soldier_field_analysis --assessment-year 2023
python -m pytest tests/test_soldier_field_analysis.py tests/test_soldier_field_valuation.py tests/test_soldier_field_comparators.py -q
```

The main run now recomputes the quadrant audit and embeds it in the same manifest
used for the map. It also retains a small reviewable copy at
`data/reference/soldier_field/comparator_audit.json`. Basemap imagery, vendor
libraries and concept images are retained static assets, not redownloaded or
regenerated by the valuation command.

Verification: 34 focused Python tests pass. Browser checks cover local-file
loading with all external requests blocked, all boundary/comparator combinations,
drawing and export, invalid polygons, street-tile fallback and mobile overflow.
Repository-wide issues from the initial review remain outside this change.

"""Generate the Soldier Field map and figure from the analysis run manifest."""

from __future__ import annotations

import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PlotPolygon
from shapely.geometry import shape

from src.config import (
    SOLDIER_FIELD_MAP,
    SOLDIER_FIELD_FIGURE,
    SOLDIER_FIELD_SOURCE_DIR,
    SOLDIER_FIELD_TEMPLATE,
    SOLDIER_FIELD_REFERENCE_DIR,
)


def render_outputs(manifest_path: Path) -> None:
    run = json.loads(manifest_path.read_text(encoding="utf-8"))
    comparators = run.get("comparator_audit")
    if not comparators:
        raise ValueError("Rerun src.soldier_field_analysis to produce the comparator audit")
    context = json.loads(
        (SOLDIER_FIELD_REFERENCE_DIR / "district_context.json").read_text(encoding="utf-8")
    )
    benchmark = comparators["comparators"][0]
    template = SOLDIER_FIELD_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__BENCHMARK__": json.dumps(benchmark),
        "__BENCHMARK_NAME__": html.escape(benchmark["name"]),
        "__ACRES__": f"{benchmark['gross_acres']:.2f}",
        "__ASSESSED__": f"${benchmark['assessed_value'] / 1e6:.2f} million",
        "__MARKET__": f"${benchmark['market_equivalent_low'] / 1e6:.2f} million",
        "__DENSITY__": f"${benchmark['value_per_gross_acre_low'] / 1e6:.2f} million",
        "__PINS__": f"{benchmark['pins']:,}",
        "__EXEMPT__": str(benchmark["exempt_pins"]),
        "__DISTRICT__": (SOLDIER_FIELD_REFERENCE_DIR / "district.geojson").read_text(
            encoding="utf-8"
        ),
        "__CONTEXT__": json.dumps(context).replace("</", r"<\/"),
    }
    for marker, value in replacements.items():
        template = template.replace(marker, value)
    SOLDIER_FIELD_MAP.parent.mkdir(parents=True, exist_ok=True)
    SOLDIER_FIELD_MAP.write_text(template, encoding="utf-8")
    render_figure(run)


def render_figure(run: dict) -> None:
    features = {f["properties"]["id"]: f for f in run["boundaries"]["features"]}
    if run.get("comparator_audit"):
        features["reference"] = {"geometry": run["comparator_audit"]["comparators"][0]["geometry"]}
    fig, axes = plt.subplots(1, 2, figsize=(12, 8), layout="constrained")
    colors = {
        "stadium": "#9b4f21",
        "waldron": "#196b68",
        "south_lot": "#196b68",
        "reference": "#315a98",
        "legacy_box": "#a33c47",
        "connected_envelope": "#876ca0",
    }
    extents = [(-87.632, -87.609, 41.852, 41.868), (-87.619, -87.6125, 41.8545, 41.8647)]
    for axis, extent in zip(axes, extents):
        axis.set_xlim(extent[0:2])
        axis.set_ylim(extent[2:4])
        axis.set_aspect(1 / 0.745)
        axis.set_facecolor("#f2f4f2")
        axis.ticklabel_format(useOffset=False)
        axis.tick_params(labelsize=8)
        axis.set_xlabel("Longitude")
        axis.set_ylabel("Latitude")
    # Optional cached aerial supplies visual context, never measurement inputs.
    aerial = SOLDIER_FIELD_SOURCE_DIR / "site_aerial.png"
    if aerial.exists():
        axes[1].imshow(
            plt.imread(aerial), extent=(-87.619, -87.6125, 41.8545, 41.8647), aspect="auto"
        )
        axes[1].set_aspect(1 / 0.745)
    for key in ("reference", "legacy_box", "connected_envelope", "stadium", "waldron", "south_lot"):
        geometry = shape(features[key]["geometry"])
        polygons = list(geometry.geoms) if geometry.geom_type == "MultiPolygon" else [geometry]
        for axis in axes:
            if axis is axes[1] and key in ("reference", "legacy_box"):
                continue
            for polygon in polygons:
                axis.add_patch(
                    PlotPolygon(
                        list(polygon.exterior.coords),
                        closed=True,
                        facecolor=colors[key]
                        if key not in ("legacy_box", "connected_envelope")
                        else "none",
                        edgecolor=colors[key],
                        alpha=0.35 if key not in ("legacy_box", "connected_envelope") else 0.95,
                        linewidth=2,
                        linestyle="--" if key in ("legacy_box", "connected_envelope") else "-",
                    )
                )
    for key, label in [
        ("stadium", "Stadium"),
        ("waldron", "Waldron"),
        ("south_lot", "South Lot"),
    ]:
        centre = shape(features[key]["geometry"]).centroid
        label += f"\n{features[key]['properties']['gross_acres']:.2f} acres"
        axes[1].text(
            centre.x,
            centre.y,
            label,
            ha="center",
            va="center",
            fontsize=9,
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "none", "pad": 3},
        )
    axes[0].set_title("Reference area and withdrawn candidate rectangle", fontsize=11)
    axes[1].set_title("Sourced footprints and broader envelope", fontsize=11)
    fig.suptitle("Soldier Field: the land-area assumption", fontsize=18)
    attribution = "Geometry: OpenStreetMap contributors (ODbL)."
    if aerial.exists():
        attribution += " Aerial context: Esri World Imagery."
    fig.text(
        0.5,
        -0.025,
        attribution
        + "\nAreas: EPSG:26971. Purple dashed envelope adds roads/open space; boundaries are not development approvals.",
        ha="center",
        fontsize=9,
    )
    SOLDIER_FIELD_FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(SOLDIER_FIELD_FIGURE, dpi=160, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    from src.config import ANALYSIS_RESULTS_DIR

    render_outputs(ANALYSIS_RESULTS_DIR / "soldier_field_run.json")

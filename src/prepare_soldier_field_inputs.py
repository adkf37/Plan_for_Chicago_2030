"""Freeze reproducible Soldier Field boundaries and aligned 2023 parcel locations.

Run once before the analysis: python -m src.prepare_soldier_field_inputs
Downloads are cached; --refresh explicitly replaces cached source snapshots.
OSM footprints describe physical features, not ownership or development rights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box, mapping
from shapely.ops import polygonize, transform, unary_union

from src.config import (
    REFERENCE_AREA,
    SOLDIER_FIELD_AREA,
    SOLDIER_FIELD_BOUNDARIES,
    SOLDIER_FIELD_REFERENCE_DIR,
    SOLDIER_FIELD_SOURCE_DIR,
)

PARCEL_URL = "https://datacatalog.cookcountyil.gov/resource/nj4t-kc8j.json"
OSM_URL = "https://api.openstreetmap.org/api/0.6/map"
OSM_BBOX = "-87.622,41.852,-87.610,41.866"
PARKING_MAP_URL = (
    "https://static.clubs.nfl.com/image/upload/v1691695208/bears/wjsgu0iueea0q5k9rcg2.pdf"
)
AERIAL_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
AERIAL_PARAMS = {
    "bbox": "-87.619,41.8545,-87.6125,41.8647",
    "bboxSR": 4326,
    "imageSR": 4326,
    "size": "650,1020",
    "format": "png",
    "f": "image",
}
ACRE_M2 = 4046.8564224
TO_METRES = Transformer.from_crs(4326, 26971, always_xy=True).transform
TO_WGS84 = Transformer.from_crs(26971, 4326, always_xy=True).transform


def area_acres(geometry) -> float:
    if (
        geometry.is_empty
        or not geometry.is_valid
        or geometry.geom_type not in ("Polygon", "MultiPolygon")
    ):
        raise ValueError("Area requires a nonempty valid polygon")
    return transform(TO_METRES, geometry).area / ACRE_M2


def rectangle(bounds):
    return box(bounds["min_lon"], bounds["min_lat"], bounds["max_lon"], bounds["max_lat"])


def component_geometry(root, kind: str, object_id: str):
    """Assemble only exterior rings: landscaped islands count in gross site area.

    In particular, a parking deck's land footprint is counted once, irrespective
    of its number of floors. Missing relation members stop boundary preparation.
    """
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.findall("node")}
    ways = {w.get("id"): w for w in root.findall("way")}
    element = root.find(f"{kind}[@id='{object_id}']")
    if element is None:
        raise ValueError(f"Missing OSM {kind}/{object_id}")

    def coords(way):
        return [nodes[n.get("ref")] for n in way.findall("nd")]

    if kind == "way":
        points = coords(element)
        if points[0] != points[-1]:
            raise ValueError("An open way is not a site polygon")
        geometry = Polygon(points)
    else:
        lines = [
            LineString(coords(ways[m.get("ref")]))
            for m in element.findall("member")
            if m.get("role") == "outer" and m.get("type") == "way"
        ]
        geometry = unary_union(list(polygonize(unary_union(lines))))
        if not lines or not unary_union(lines).difference(geometry.boundary).is_empty:
            raise ValueError("Incomplete exterior ring in OSM relation")
    area_acres(geometry)
    return geometry, element


def build_boundaries(osm_xml: bytes) -> dict:
    root = ET.fromstring(osm_xml)
    features, components = [], {}

    def feature(key, label, role, geometry, **properties):
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "id": key,
                    "name": label,
                    "role": role,
                    "gross_acres": area_acres(geometry),
                    **properties,
                },
                "geometry": mapping(geometry),
            }
        )

    for key, label, kind, object_id in [
        ("stadium", "Soldier Field stadium footprint", "way", "24587933"),
        ("waldron", "Waldron Deck land footprint", "relation", "10655279"),
        ("south_lot", "South Lot gross footprint", "relation", "17644593"),
    ]:
        geometry, element = component_geometry(root, kind, object_id)
        components[key] = geometry
        feature(
            key,
            label,
            "component",
            geometry,
            source_url=f"https://www.openstreetmap.org/{kind}/{object_id}",
            source_version=int(element.get("version")),
            source_timestamp=element.get("timestamp"),
            treatment="Exterior footprint includes internal landscaping and circulation; land counted once",
        )

    parking = unary_union([components["waldron"], components["south_lot"]])
    core = unary_union(list(components.values()))
    # A transparent upper-area alternative; explicitly includes intervening land.
    envelope = transform(TO_WGS84, transform(TO_METRES, core).convex_hull)
    for key, label, geometry, note in [
        (
            "parking_only",
            "Parking only; stadium retained",
            parking,
            "Waldron Deck and South Lot exteriors only; excludes stadium and intervening roads/open space",
        ),
        (
            "stadium_and_parking",
            "Stadium plus south parking footprints",
            core,
            "Three mapped exteriors only; excludes intervening public space and roads",
        ),
        (
            "connected_envelope",
            "Broader connected envelope",
            envelope,
            "Projected convex hull of the three footprints; includes intervening roads and open space, requiring separate review",
        ),
    ]:
        feature(
            key,
            label,
            "scenario",
            geometry,
            inclusion_rule=note,
            additional_land_acres=max(0, area_acres(geometry) - area_acres(core))
            if key == "connected_envelope"
            else 0,
            legal_status="Physical-area thought experiment, not an approved or legally developable site",
        )
    feature(
        "reference",
        "Reference comparison rectangle",
        "reference",
        rectangle(REFERENCE_AREA),
        inclusion_rule="All PIN locations within the fixed rectangle; gross denominator includes streets/open space",
    )
    feature(
        "legacy_box",
        "Withdrawn 274-acre candidate rectangle",
        "legacy",
        rectangle(SOLDIER_FIELD_AREA),
        inclusion_rule="Comparison only; never used in new scenario calculations",
    )
    return {
        "type": "FeatureCollection",
        "metadata": {
            "area_crs": "EPSG:26971",
            "acre_square_metres": ACRE_M2,
            "attribution": "OpenStreetMap contributors (ODbL)",
            "license_url": "https://www.openstreetmap.org/copyright",
            "source_url": f"{OSM_URL}?bbox={OSM_BBOX}",
            "source_sha256": hashlib.sha256(osm_xml).hexdigest(),
            "cross_check": PARKING_MAP_URL,
            "excluded": [
                "North Garage",
                "Field Museum grounds",
                "Burnham Harbor parking",
                "harbor water",
                "lakefront trails outside the selected footprints",
                "McCormick Place parking",
                "Northerly Island",
            ],
            "boundary_limit": "Physical OSM outlines; not surveyed parcel boundaries. Broader envelope adds public land.",
        },
        "features": features,
    }


def prepare_inputs(refresh: bool = False, with_aerial: bool = False) -> None:
    SOLDIER_FIELD_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    SOLDIER_FIELD_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    osm_path = SOLDIER_FIELD_SOURCE_DIR / "osm_map.xml"
    if refresh or not osm_path.exists():
        response = requests.get(OSM_URL, params={"bbox": OSM_BBOX}, timeout=60)
        response.raise_for_status()
        # Validate before replacing a usable cached source.
        build_boundaries(response.content)
        osm_path.write_bytes(response.content)
    boundaries = build_boundaries(osm_path.read_bytes())
    SOLDIER_FIELD_BOUNDARIES.write_text(json.dumps(boundaries, indent=2) + "\n", encoding="utf-8")

    b = REFERENCE_AREA
    where = (
        f"year=2023 AND lat between {b['min_lat']} and {b['max_lat']} "
        f"AND lon between {b['min_lon']} and {b['max_lon']}"
    )
    parcel_path = SOLDIER_FIELD_SOURCE_DIR / "parcels_2023.json"
    if refresh or not parcel_path.exists():
        records = []
        for offset in range(0, 100_000, 10_000):
            response = requests.get(
                PARCEL_URL,
                params={
                    "$where": where,
                    "$select": "pin,year,class,lat,lon,tax_code,tax_tif_district_num",
                    "$order": "pin",
                    "$limit": 10_000,
                    "$offset": offset,
                },
                timeout=60,
            )
            response.raise_for_status()
            page = response.json()
            records.extend(page)
            if len(page) < 10_000:
                break
        else:
            raise ValueError("Parcel result exceeded the study-area safety limit")
    else:
        records = json.loads(parcel_path.read_text(encoding="utf-8"))
    response = requests.get(PARCEL_URL, params={"$where": where, "$select": "count(*)"}, timeout=60)
    response.raise_for_status()
    expected = int(response.json()[0]["count"])
    frame = pd.DataFrame(records)
    if len(frame) != expected or not expected or frame["pin"].duplicated().any():
        raise ValueError("Parcel completeness/uniqueness check failed; refresh sources")
    if set(frame["year"].astype(int)) != {2023}:
        raise ValueError("Unexpected parcel vintage")
    parcel_path.write_text(json.dumps(records) + "\n", encoding="utf-8")
    frame.rename(columns={"year": "tax_year", "lat": "latitude", "lon": "longitude"}).to_csv(
        SOLDIER_FIELD_SOURCE_DIR / "parcels_2023.csv", index=False
    )
    source = {
        "url": PARCEL_URL,
        "where": where,
        "order": "pin",
        "expected_rows": expected,
        "rows": len(frame),
        "tax_year": 2023,
        "sha256": hashlib.sha256(parcel_path.read_bytes()).hexdigest(),
    }
    (SOLDIER_FIELD_REFERENCE_DIR / "parcel_source.json").write_text(
        json.dumps(source, indent=2) + "\n", encoding="utf-8"
    )
    aerial_path = SOLDIER_FIELD_SOURCE_DIR / "site_aerial.png"
    if with_aerial and (refresh or not aerial_path.exists()):
        response = requests.get(AERIAL_URL, params=AERIAL_PARAMS, timeout=60)
        response.raise_for_status()
        if not response.headers.get("content-type", "").startswith("image/"):
            raise ValueError("Aerial service did not return an image")
        aerial_path.write_bytes(response.content)
    if aerial_path.exists():
        (SOLDIER_FIELD_REFERENCE_DIR / "aerial_source.json").write_text(
            json.dumps(
                {
                    "url": AERIAL_URL,
                    "parameters": AERIAL_PARAMS,
                    "sha256": hashlib.sha256(aerial_path.read_bytes()).hexdigest(),
                    "use": "Visual context only; not an area measurement or a dated property survey",
                    "attribution": "Esri World Imagery",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    for f in boundaries["features"]:
        if f["properties"]["role"] in ("scenario", "reference"):
            print(f"{f['properties']['name']}: {f['properties']['gross_acres']:.2f} acres")
    print(f"Verified {expected:,} unique 2023 parcel records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--with-aerial", action="store_true", help="Download optional aerial figure context"
    )
    args = parser.parse_args()
    prepare_inputs(args.refresh, args.with_aerial)

"""
build_transit_lines.py
======================
Generates site/data/transit_lines.geojson from two sources:

1. CTA L lines  — derived from data/geojson/cta_stations.geojson which has
   boolean fields (red, blue, g, brn, pnk, p, o, y) per stop.
   Stops for each line are sorted along their principal axis and connected
   into a MultiLineString, with branch splits handled where needed.

2. Metra lines  — hardcoded approximate routes (no public GeoJSON API
   available without GTFS processing).

Run from repo root:
    python scripts/build_transit_lines.py
"""

import json
import math
from pathlib import Path

ROOT = Path(__file__).parent.parent
CTA_STATIONS_FILE = ROOT / "data" / "geojson" / "cta_stations.geojson"
OUT_LINES_FILE    = ROOT / "site" / "data" / "transit_lines.geojson"
OUT_METRA_FILE    = ROOT / "site" / "data" / "metra_stations.geojson"

# ── CTA line metadata ────────────────────────────────────────────────────────
# field_key : (label, hex_colour, sort_axis)
# sort_axis: 'lat' = sort N→S, 'lon' = sort W→E, 'auto' = PCA-based
CTA_LINES = {
    "red":  ("Red Line",    "#c60c30", "lat"),
    "blue": ("Blue Line",   "#00a1de", "lon"),
    "g":    ("Green Line",  "#009b3a", "lon"),
    "brn":  ("Brown Line",  "#62361b", "lat"),
    "p":    ("Purple Line", "#522398", "lat"),
    "pnk":  ("Pink Line",   "#e27ea6", "lon"),
    "o":    ("Orange Line", "#f9461c", "lat"),
    "y":    ("Yellow Line", "#f9e300", "lat"),
}

# Display names for Metra line abbreviations
METRA_LINE_NAMES = {
    "BNSF":  "BNSF",
    "UP-N":  "Union Pacific North",
    "UP-NW": "Union Pacific Northwest",
    "UP-W":  "Union Pacific West",
    "MD-N":  "Milwaukee District North",
    "MD-W":  "Milwaukee District West",
    "NCS":   "North Central Service",
    "SWS":   "SouthWest Service",
    "RI":    "Rock Island District",
    "ME":    "Metra Electric / South Shore",
    "HC":    "Heritage Corridor",
}


# ── Metra station stops (name, line_abbrev, hex_colour, lon, lat) ────────────
METRA_STATIONS = [
    # BNSF Railway  (Union Station → Aurora)
    # Coordinates from Nominatim geocoder, corrected where geocoder returned wrong result
    ("Chicago Union Station",   "BNSF",  "#dc143c", -87.6404, 41.8787),
    ("Western Ave",             "BNSF",  "#dc143c", -87.6863, 41.8773),  # corrected lat
    ("Berwyn",                  "BNSF",  "#dc143c", -87.7935, 41.8331),
    ("Riverside",               "BNSF",  "#dc143c", -87.8201, 41.8272),
    ("LaGrange Road",           "BNSF",  "#dc143c", -87.8699, 41.8073),
    ("Downers Grove/Main",      "BNSF",  "#dc143c", -88.0141, 41.7969),
    ("Naperville",              "BNSF",  "#dc143c", -88.1473, 41.7669),  # geocoder gave Route 59
    ("Aurora",                  "BNSF",  "#dc143c", -88.3168, 41.7578),

    # Union Pacific North  (Ogilvie → Kenosha)
    ("Chicago Ogilvie Center",  "UP-N",  "#0047ab", -87.6405, 41.8838),
    ("Clybourn",                "UP-N",  "#0047ab", -87.6684, 41.9162),
    ("Ravenswood",              "UP-N",  "#0047ab", -87.6741, 41.9680),
    ("Rogers Park",             "UP-N",  "#0047ab", -87.6754, 42.0091),
    ("Evanston (Davis St)",     "UP-N",  "#0047ab", -87.6826, 42.0461),
    ("Wilmette",                "UP-N",  "#0047ab", -87.7093, 42.0774),
    ("Waukegan",                "UP-N",  "#0047ab", -87.8484, 42.3573),

    # Union Pacific Northwest  (Ogilvie → Elgin / Harvard)
    ("Chicago Ogilvie Center",  "UP-NW", "#0047ab", -87.6405, 41.8838),
    ("Jefferson Park",          "UP-NW", "#0047ab", -87.7616, 41.9706),
    ("Des Plaines",             "UP-NW", "#0047ab", -87.8867, 42.0410),
    ("Arlington Heights",       "UP-NW", "#0047ab", -87.9806, 42.0880),
    ("Barrington",              "UP-NW", "#0047ab", -88.1320, 42.1529),

    # Union Pacific West  (Ogilvie → Geneva / Elburn)
    ("Chicago Ogilvie Center",  "UP-W",  "#0047ab", -87.6405, 41.8838),
    ("Oak Park (UP)",           "UP-W",  "#0047ab", -87.7835, 41.8853),  # geocoder found wrong station
    ("Elmhurst",                "UP-W",  "#0047ab", -87.9409, 41.8998),
    ("Wheaton",                 "UP-W",  "#0047ab", -88.1065, 41.8601),
    ("Geneva",                  "UP-W",  "#0047ab", -88.3100, 41.8817),

    # Milwaukee District North  (Union Station → Fox Lake)
    ("Chicago Union Station",   "MD-N",  "#006400", -87.6404, 41.8787),
    ("Glenview",                "MD-N",  "#006400", -87.8278, 42.0647),  # traditional Glenview stn
    ("Lake Forest",             "MD-N",  "#006400", -87.8396, 42.2524),
    ("Fox Lake",                "MD-N",  "#006400", -88.1823, 42.3983),

    # Milwaukee District West  (Union Station → Elgin)
    ("Chicago Union Station",   "MD-W",  "#006400", -87.6404, 41.8787),
    ("Elmwood Park",            "MD-W",  "#006400", -87.8163, 41.9196),
    ("Maywood",                 "MD-W",  "#006400", -87.8446, 41.8798),
    ("Elgin (MD)",              "MD-W",  "#006400", -88.2862, 42.0362),

    # North Central Service  (Union Station → Antioch)
    ("Chicago Union Station",   "NCS",   "#ff8c00", -87.6404, 41.8787),
    ("Rosemont (NCS)",          "NCS",   "#ff8c00", -87.8584, 41.9853),  # corrected
    ("Wheeling",                "NCS",   "#ff8c00", -87.9274, 42.1365),
    ("Antioch",                 "NCS",   "#ff8c00", -88.0924, 42.4810),

    # SouthWest Service  (Union Station → Manhattan)
    ("Chicago Union Station",   "SWS",   "#8b008b", -87.6404, 41.8787),
    ("35th/Archer (Bridgeport)","SWS",   "#8b008b", -87.6578, 41.8307),
    ("Chicago Ridge",           "SWS",   "#8b008b", -87.7803, 41.7034),
    ("Orland Park",             "SWS",   "#8b008b", -87.8576, 41.6079),

    # Rock Island District  (LaSalle St → Joliet)
    ("Chicago LaSalle St",      "RI",    "#8b0000", -87.6316, 41.8757),
    ("35th St (RI)",            "RI",    "#8b0000", -87.6316, 41.8308),
    ("Beverly / 95th",          "RI",    "#8b0000", -87.6600, 41.7222),
    ("Blue Island",             "RI",    "#8b0000", -87.6761, 41.6559),
    ("Joliet (RI)",             "RI",    "#8b0000", -88.0831, 41.5250),

    # Metra Electric / South Shore  (Millennium → University Park)
    ("Millennium Station",      "ME",    "#b8960c", -87.6237, 41.8844),
    ("Van Buren St (ME)",       "ME",    "#b8960c", -87.6225, 41.8764),
    ("18th St (ME)",            "ME",    "#b8960c", -87.6226, 41.8560),
    ("47th St (ME)",            "ME",    "#b8960c", -87.5957, 41.8097),
    ("53rd St / Hyde Park",     "ME",    "#b8960c", -87.5897, 41.7986),
    ("63rd St (ME)",            "ME",    "#b8960c", -87.5831, 41.7802),
    ("95th St (ME)",            "ME",    "#b8960c", -87.5606, 41.7223),
    ("Harvey",                  "ME",    "#b8960c", -87.6469, 41.6079),
    ("Chicago Heights",         "ME",    "#b8960c", -87.6355, 41.5066),

    # Heritage Corridor  (Union Station → Joliet)
    ("Chicago Union Station",   "HC",    "#a0522d", -87.6404, 41.8787),
    ("Summit",                  "HC",    "#a0522d", -87.8152, 41.7832),  # geocoder gave wrong city
    ("Joliet (HC)",             "HC",    "#a0522d", -88.0831, 41.5250),
]


def load_cta_stations():
    with open(CTA_STATIONS_FILE) as f:
        return json.load(f)["features"]


def pca_angle(coords):
    """Return the angle of the first principal component of a point cloud."""
    n = len(coords)
    if n < 2:
        return 0
    mx = sum(c[0] for c in coords) / n
    my = sum(c[1] for c in coords) / n
    sxx = sum((c[0] - mx) ** 2 for c in coords)
    syy = sum((c[1] - my) ** 2 for c in coords)
    sxy = sum((c[0] - mx) * (c[1] - my) for c in coords)
    angle = 0.5 * math.atan2(2 * sxy, sxx - syy)
    return angle


def project(coord, angle):
    return coord[0] * math.cos(angle) + coord[1] * math.sin(angle)


def nearest_neighbor_path(coords):
    """
    Build a path by always connecting to the nearest unvisited station.
    Starts from the station furthest from the centroid (a natural endpoint).

    This correctly handles through-running lines with U/S shapes (e.g. the
    Blue Line O'Hare→Loop→Forest Park) that trip up PCA-axis sorting, which
    interleaves the two western branches because they share similar longitudes
    but sit several miles apart north-to-south.
    """
    if len(coords) < 2:
        return list(coords)
    coords = list(coords)
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    start_idx = max(range(len(coords)),
                    key=lambda i: (coords[i][0] - cx) ** 2 + (coords[i][1] - cy) ** 2)
    unvisited = list(coords)
    path = [unvisited.pop(start_idx)]
    while unvisited:
        cur = path[-1]
        best = min(range(len(unvisited)),
                   key=lambda i: (unvisited[i][0] - cur[0]) ** 2 + (unvisited[i][1] - cur[1]) ** 2)
        path.append(unvisited.pop(best))
    return path


def split_branches(sorted_coords, gap_factor=4.0):
    """
    Split a sorted coordinate sequence into branches at large spatial gaps.
    Returns a list of coordinate-list segments.
    """
    if len(sorted_coords) < 2:
        return [sorted_coords]

    # Calculate typical inter-station distance
    dists = []
    for i in range(len(sorted_coords) - 1):
        dx = sorted_coords[i + 1][0] - sorted_coords[i][0]
        dy = sorted_coords[i + 1][1] - sorted_coords[i][1]
        dists.append(math.sqrt(dx * dx + dy * dy))
    if not dists:
        return [sorted_coords]
    median_d = sorted(dists)[len(dists) // 2]
    threshold = median_d * gap_factor

    segments = []
    current = [sorted_coords[0]]
    for i, d in enumerate(dists):
        if d > threshold:
            if len(current) >= 2:
                segments.append(current)
            current = [sorted_coords[i + 1]]
        else:
            current.append(sorted_coords[i + 1])
    if len(current) >= 2:
        segments.append(current)
    return segments if segments else [sorted_coords]


def build_cta_line_feature(field_key, label, colour, stations):
    """Build a GeoJSON Feature (MultiLineString) for one CTA L line."""
    # Deduplicate by map_id (each physical station has 2 directional stops).
    # Average the coordinates of duplicate stops to get a clean centre point.
    station_coords = {}  # map_id -> [list of (lon, lat)]
    for feat in stations:
        props = feat.get("properties", feat)
        val = props.get(field_key, False)
        if val is True or str(val).lower() == "true":
            geom = feat.get("geometry", {})
            if geom and geom.get("type") == "Point":
                lon, lat = geom["coordinates"][0], geom["coordinates"][1]
                mid = props.get("map_id", props.get("stop_id", f"{lon},{lat}"))
                station_coords.setdefault(mid, []).append((lon, lat))

    coords_with_raw = []
    for pts in station_coords.values():
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
        coords_with_raw.append((lon, lat))

    if not coords_with_raw:
        return None

    # Nearest-neighbor traversal starting from most extreme station.
    # Correctly handles through-running lines (e.g. Blue Line O'Hare → Loop → Forest Park)
    # where PCA-axis sorting zigzags between parallel branches at similar longitudes.
    coords_sorted = nearest_neighbor_path(coords_with_raw)

    # Split into branch segments at large spatial gaps (handles Y-shaped branching lines)
    segments = split_branches(coords_sorted)

    return {
        "type": "Feature",
        "properties": {
            "line_name": label,
            "line_type": "CTA_L",
            "colour": colour,
        },
        "geometry": {
            "type": "MultiLineString",
            "coordinates": segments,
        },
    }


def build_metra_lines_from_stations(station_list):
    """Derive Metra LineString features by ordering each line's stations with
    nearest-neighbour traversal.  Guarantees every station dot sits on its line.
    """
    from collections import defaultdict
    line_data = defaultdict(lambda: {"pts": [], "colour": "#888"})
    for _name, abbrev, colour, lon, lat in station_list:
        line_data[abbrev]["colour"] = colour
        line_data[abbrev]["pts"].append((lon, lat))

    features = []
    for abbrev, data in line_data.items():
        # De-duplicate (same terminal appears on multiple lines)
        seen, unique = set(), []
        for p in data["pts"]:
            k = (round(p[0], 4), round(p[1], 4))
            if k not in seen:
                seen.add(k)
                unique.append(p)
        if len(unique) < 2:
            continue
        ordered = nearest_neighbor_path(unique)
        features.append({
            "type": "Feature",
            "properties": {
                "line_name":   METRA_LINE_NAMES.get(abbrev, abbrev),
                "line_abbrev": abbrev,
                "line_type":   "Metra",
                "colour":      data["colour"],
            },
            "geometry": {"type": "LineString", "coordinates": ordered},
        })
    return features


def build_metra_station_feature(name, line_abbrev, colour, lon, lat):
    return {
        "type": "Feature",
        "properties": {
            "station_name": name,
            "line_abbrev": line_abbrev,
            "station_type": "Metra",
            "colour": colour,
        },
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def main():
    print("Loading CTA stations …")
    stations = load_cta_stations()
    print(f"  {len(stations)} stops loaded")

    features = []

    print("Building CTA L line geometries …")
    for field_key, (label, colour, _sort) in CTA_LINES.items():
        feat = build_cta_line_feature(field_key, label, colour, stations)
        if feat:
            n_seg = len(feat["geometry"]["coordinates"])
            n_pts = sum(len(s) for s in feat["geometry"]["coordinates"])
            print(f"  {label:20s} {n_pts:3d} stops, {n_seg} segment(s)")
            features.append(feat)
        else:
            print(f"  {label:20s} — no stops found (field: {field_key})")

    print("Adding Metra line geometries (derived from stations) …")
    metra_line_feats = build_metra_lines_from_stations(METRA_STATIONS)
    for feat in metra_line_feats:
        n = len(feat["geometry"]["coordinates"])
        print(f"  {feat['properties']['line_name']:35s} {n} stations")
    features.extend(metra_line_feats)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    OUT_LINES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_LINES_FILE, "w", encoding="utf-8") as f:
        json.dump(geojson, f, separators=(",", ":"))
    print(f"\nWrote {len(features)} line features → {OUT_LINES_FILE}")

    # ── Metra station points ───────────────────────────────────────────────
    print("\nBuilding Metra station points …")
    station_feats = [
        build_metra_station_feature(name, abbrev, colour, lon, lat)
        for name, abbrev, colour, lon, lat in METRA_STATIONS
    ]
    metra_geojson = {
        "type": "FeatureCollection",
        "features": station_feats,
    }
    with open(OUT_METRA_FILE, "w", encoding="utf-8") as f:
        json.dump(metra_geojson, f, separators=(",", ":"))
    print(f"Wrote {len(station_feats)} Metra station points → {OUT_METRA_FILE}")


if __name__ == "__main__":
    main()

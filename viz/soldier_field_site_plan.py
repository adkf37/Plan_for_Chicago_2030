"""Draw the illustrative surface plan in metres. It is independent of the valuation."""

from collections import defaultdict
from itertools import pairwise
from math import atan2, degrees, floor

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box, mapping, shape
from shapely.ops import nearest_points, transform, unary_union

from src.prepare_soldier_field_inputs import TO_METRES, TO_WGS84


def surface_plan(district):
    features = {f["properties"]["name"]: shape(f["geometry"]) for f in district["features"]}
    routes = [features[f"{n}th Street to beach"] for n in (14, 16, 18)]
    # Rotate the working grid to the mapped 16th Street alignment.
    start, end = transform(TO_METRES, routes[1]).coords
    angle = degrees(atan2(end[1] - start[1], end[0] - start[0]))

    def local(geometry):
        return affinity.rotate(transform(TO_METRES, geometry), -angle, origin=start)

    site = local(features["Tracks to Northerly Island"])
    deck = local(features["Deck over operating rail tracks"])
    # Follow the eastern perimeter between the ends of the existing shore guide.
    guide = features["Public beach and park on the lake edge"]
    ring = list(site.exterior.coords)[:-1]
    tips = [local(Point(p)) for p in (guide.coords[0], guide.coords[-1])]
    north, south = [
        min(range(len(ring)), key=lambda i: tip.distance(Point(ring[i]))) for tip in tips
    ]
    shore = LineString(ring[north : south + 1])
    museum = local(Point(-87.60686, 41.86634)).buffer(57)
    surface = site.difference(museum)
    # From the water inland: 75 ft of sand, 45 ft of dunes, 30 ft of promenade.
    sand = shore.buffer(75 * 0.3048)
    dunes = shore.buffer(120 * 0.3048)
    public_shore = shore.buffer(150 * 0.3048)
    south_park = local(
        Polygon(
            [
                (-87.6133, 41.8548),
                (-87.6098, 41.8548),
                (-87.6093, 41.8570),
                (-87.6052, 41.8570),
                (-87.6052, 41.8490),
                (-87.6133, 41.8490),
            ]
        )
    )
    museum_green = local(
        Polygon(
            [
                (-87.6104, 41.8668),
                (-87.6060, 41.8668),
                (-87.6057, 41.8650),
                (-87.6092, 41.8650),
                (-87.6104, 41.8657),
            ]
        )
    )
    routes = [local(route) for route in routes]
    ends = [nearest_points(Point(route.coords[-1]), shore)[1] for route in routes]
    # Plazas widen the public strip inland at the three entrances.
    plazas = unary_union([p.buffer(200 * 0.3048, resolution=12) for p in ends])
    deck_green = deck.buffer(17)
    parks = unary_union([public_shore, south_park, museum_green, plazas, deck_green])
    neighborhood = surface.difference(parks)
    layers = defaultdict(list)

    def add(kind, geometry):
        if not geometry.is_empty:
            layers[kind].append(geometry)

    add("green", surface)
    add("streets", neighborhood)
    add("deck", deck_green.intersection(surface))
    # Link the south park to the shore promenade and to the blocks on its west.
    park_walk = local(
        LineString(
            [
                (-87.6077, 41.8575),
                (-87.6078, 41.8562),
                (-87.6085, 41.8554),
                (-87.6084, 41.8544),
                (-87.6075, 41.8539),
                (-87.6071, 41.8536),
            ]
        )
    )
    lake_walk = local(
        LineString(
            [
                (-87.6095, 41.8554),
                (-87.6085, 41.8554),
                (-87.6079, 41.8556),
                (-87.6069, 41.8556),
            ]
        )
    )
    add(
        "park_path",
        unary_union([park_walk, lake_walk])
        .buffer(2.5)
        .intersection(south_park)
        .intersection(surface),
    )
    add("park_path", deck.buffer(2.5).intersection(surface))
    add("plaza", plazas.intersection(surface))
    for kind, band in [("promenade", public_shore), ("dunes", dunes), ("sand", sand)]:
        add(kind, band.intersection(surface))

    left, bottom, right, top = surface.bounds
    # Cross streets divide the spaces between 14th, 16th and 18th into short blocks.
    main_rows = sorted(line.coords[0][1] for line in routes)
    rows = [main_rows[0] - 98 * n for n in range(1, 1 + int((main_rows[0] - bottom) / 98) + 1)]
    for low, high in pairwise(main_rows):
        rows.extend(low + (high - low) * n / 4 for n in range(4))
    rows.extend(main_rows[-1] + 98 * n for n in range(2 + int((top - main_rows[-1]) / 98)))
    rows.sort()
    pitch = 105
    stadium = local(features["Remove Soldier Field"])
    for row, (y0, y1) in enumerate(pairwise(rows)):
        for col in range(floor((right - left) / pitch) + 1):
            x0 = left + col * pitch
            block = box(x0 + 8, y0 + 8, x0 + pitch - 8, y1 - 8).intersection(
                neighborhood, grid_size=0.01
            )
            if block.area < 600:
                continue
            add("block", block)
            # A planted square breaks up the blocks at the former stadium.
            if block.covers(stadium):
                add("green_square", block)
                continue
            inset = block.buffer(-5, join_style="mitre")
            if inset.area < 900:
                continue
            court = inset.buffer(-14, join_style="mitre")
            if court.area < 120:
                continue
            # Mix perimeter blocks, paired apartment buildings and U-shaped courts.
            cx, cy = court.representative_point().coords[0]
            frontage = (row * 3 + col) % 5
            if frontage == 0:
                buildings = inset.difference(box(cx - 10, y0, cx + 10, y1))
            elif frontage == 1:
                buildings = inset.difference(box(cx, cy, x0 + pitch, y1))
            else:
                passage = box(cx - 5, cy, cx + 5, y1) if col % 2 else box(x0, cy - 5, cx, cy + 5)
                buildings = inset.difference(court.union(passage))
            add("roof", buildings)
            if (row + col) % 3 == 0:
                tx = x0 + (15 if row % 2 else 60)
                pad = box(tx, y0 + 15, tx + 25, y0 + 42)
                if inset.covers(pad):
                    add("tower", pad)

    # Carry the named streets over the deck, then a walking route through the sand.
    # Outside the study perimeter keep the short links to the existing grid visible.
    links, labels = [], []
    for number, line, end_point in zip((14, 16, 18), routes, ends):
        access = LineString([line.coords[0], end_point.coords[0]])
        road = access.buffer(8, cap_style="flat").intersection(surface).difference(plazas)
        add("avenue", road)
        walk = access.intersection(plazas).buffer(2.5, cap_style="flat").intersection(surface)
        add("access", walk)
        outside = access.difference(site)
        if not outside.is_empty:
            links.append(outside)
        labels.append((number, access.interpolate(0.51, normalized=True)))
    if links:
        add("connection", unary_union(links))

    def geojson(kind, geometry, **props):
        geographic = transform(TO_WGS84, affinity.rotate(geometry, angle, origin=start))
        # Sub-metre precision keeps the standalone page compact.
        geographic = transform(lambda x, y: (round(x, 6), round(y, 6)), geographic)
        return {
            "type": "Feature",
            "properties": {"kind": kind, **props},
            "geometry": mapping(geographic),
        }

    result = [
        geojson(kind, unary_union(layers[kind]))
        for kind in (
            "green",
            "streets",
            "deck",
            "park_path",
            "block",
            "green_square",
            "roof",
            "tower",
            "plaza",
            "promenade",
            "dunes",
            "sand",
            "avenue",
            "access",
            "connection",
        )
        if layers[kind]
    ]
    result.extend(geojson("label", point, street=number) for number, point in labels)
    return {"type": "FeatureCollection", "features": result}

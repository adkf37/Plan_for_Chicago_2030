"""Systematic internal sensitivity check, not independent comparator validation.

Divide the original reference at its geographic midpoints before comparing all
four quadrants. Half-open cuts assign each PIN to exactly one quadrant.
"""

import pandas as pd
from shapely.geometry import mapping

from src.prepare_soldier_field_inputs import area_acres, rectangle


def comparator_audit(valued: pd.DataFrame, bounds: dict) -> dict:
    west, east = bounds["min_lon"], bounds["max_lon"]
    south, north = bounds["min_lat"], bounds["max_lat"]
    mid_x, mid_y = (west + east) / 2, (south + north) / 2
    if not (valued.longitude.between(west, east) & valued.latitude.between(south, north)).all():
        raise ValueError("Comparator inputs must lie inside the reference bounds")
    masks = {
        "full": pd.Series(True, index=valued.index),
        "northwest": (valued.longitude < mid_x) & (valued.latitude >= mid_y),
        "northeast": (valued.longitude >= mid_x) & (valued.latitude >= mid_y),
        "southwest": (valued.longitude < mid_x) & (valued.latitude < mid_y),
        "southeast": (valued.longitude >= mid_x) & (valued.latitude < mid_y),
    }
    boxes = {
        "full": (west, south, east, north),
        "northwest": (west, mid_y, mid_x, north),
        "northeast": (mid_x, mid_y, east, north),
        "southwest": (west, south, mid_x, mid_y),
        "southeast": (mid_x, south, east, mid_y),
    }
    results = []
    for key, mask in masks.items():
        w, s, e, n = boxes[key]
        geometry = rectangle(dict(min_lon=w, max_lon=e, min_lat=s, max_lat=n))
        acres = area_acres(geometry)
        part = valued.loc[mask]
        results.append(
            {
                "id": key,
                "name": "Full original reference"
                if key == "full"
                else key.capitalize() + " quarter",
                "gross_acres": acres,
                "pins": len(part),
                "assessed_value": float(part.assessed_value.sum()),
                "market_equivalent_low": float(part.market_equivalent_low.sum()),
                "market_equivalent_high": float(part.market_equivalent_high.sum()),
                "value_per_gross_acre_low": float(part.market_equivalent_low.sum() / acres),
                "value_per_gross_acre_high": float(part.market_equivalent_high.sum() / acres),
                "geometry": mapping(geometry),
            }
        )
    return {
        "method": "All four geographic midpoint quadrants of the fixed reference, including streets and zero-value land. Partition audit. Northeast is the selected project benchmark.",
        "assessment_year": 2023,
        "assessment_stage": "board_tot",
        "comparators": results,
    }


def street_locations(year, bounds):
    """Cache a complete bounding-box extract before the exact polygon selection."""
    from src.config import SOLDIER_FIELD_SOURCE_DIR
    from src.prepare_soldier_field_inputs import PARCEL_URL
    import hashlib
    import requests

    west, south, east, north = (bounds[k] for k in ("min_lon", "min_lat", "max_lon", "max_lat"))
    where = f"year={year} AND lat between {south} and {north} AND lon between {west} and {east}"
    key = hashlib.sha256(where.encode()).hexdigest()[:12]
    path = SOLDIER_FIELD_SOURCE_DIR / f"wabash_michigan_{year}_{key}.csv"
    if path.exists():
        return path

    def query(**params):
        response = requests.get(PARCEL_URL, params={"$where": where, **params}, timeout=60)
        response.raise_for_status()
        return response.json()

    count = int(query(**{"$select": "count(*)"})[0]["count"])
    rows = []
    for offset in range(0, count, 5000):
        rows.extend(
            query(
                **{
                    "$select": "pin,year,class,lat,lon,tax_code",
                    "$order": "pin",
                    "$limit": 5000,
                    "$offset": offset,
                }
            )
        )
    if not rows or len(rows) != count or len({r["pin"] for r in rows}) != count:
        raise ValueError("Incomplete comparator parcel extract")
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows).rename(
        columns={"year": "tax_year", "lat": "latitude", "lon": "longitude"}
    )
    temporary = path.with_suffix(".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)
    return path


if __name__ == "__main__":
    from src.soldier_field_analysis import main

    raise SystemExit(main())

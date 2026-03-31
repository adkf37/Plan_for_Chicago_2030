"""
fetch_metra_stations.py
=======================
Tries to download authoritative Metra station coordinates from public APIs.
Falls back gracefully and prints what it finds.
"""
import json, urllib.request, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUT = ROOT / "data" / "geojson" / "metra_stations_raw.geojson"

ENDPOINTS = [
    # Metra GTFS published via RTAMS / RTA
    ("RTA Metra stops",
     "https://rtams.org/api/metra/stops?format=geojson"),
    # Chicago Regional Transit Authority open data
    ("CMAP Metra stops GeoJSON",
     "https://opendata.arcgis.com/datasets/43b718ab3b4949b49ec3f87a0c741e30_0.geojson"),
    # City of Chicago transit stops (all modes)
    ("Chicago transit stops",
     "https://data.cityofchicago.org/api/geospatial/yglt-ybi7?method=export&type=GeoJSON"),
]

def try_fetch(label, url):
    print(f"Trying {label} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "python/3.11"})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        d = json.loads(raw)
        features = d.get("features", d if isinstance(d, list) else [])
        print(f"  OK -> {len(features)} features")
        if features:
            sample = features[0]
            props = sample.get("properties", sample)
            print(f"  Sample keys: {list(props.keys())[:10]}")
            if "name" in props or "stop_name" in props or "STATION_NAME" in props:
                name_key = next(k for k in ("name","stop_name","STATION_NAME","Name") if k in props)
                print(f"  Sample name: {props[name_key]}")
        return d
    except Exception as e:
        print(f"  FAIL: {e}")
        return None

for label, url in ENDPOINTS:
    result = try_fetch(label, url)
    if result:
        features = result.get("features", [])
        # Filter to Metra if possible
        metra = [f for f in features
                 if any("metra" in str(v).lower() or "rail" in str(v).lower()
                        for v in (f.get("properties") or f).values())]
        print(f"  Metra-tagged features: {len(metra)}")
        if len(metra) > 10:
            OUT.parent.mkdir(parents=True, exist_ok=True)
            fc = {"type":"FeatureCollection","features":metra}
            with open(OUT,"w") as fp:
                json.dump(fc, fp, indent=2)
            print(f"  Saved {len(metra)} features -> {OUT}")
            sys.exit(0)
    print()

print("No suitable endpoint found. Manual coordinates remain.")

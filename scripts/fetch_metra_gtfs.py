import urllib.request, zipfile, io, csv, json, sys
from pathlib import Path

ROOT = Path(r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030")
OUT_STOPS = ROOT / "data" / "geojson" / "metra_gtfs_stops.geojson"
OUT_ROUTES = ROOT / "data" / "geojson" / "metra_gtfs_routes.json"

urls = [
    "https://www.metrarail.com/content/dam/metra/documents/GTFS/GTFS.zip",
    "https://transitfeeds.com/p/metra/5/latest/download",
    "https://www.transitchicago.com/downloads/sch_data/google_transit.zip",
]

z = None
for url in urls:
    try:
        print(f"Trying {url[:60]}...")
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        print(f"  Downloaded {len(data):,} bytes")
        z = zipfile.ZipFile(io.BytesIO(data))
        print(f"  Files: {z.namelist()}")
        break
    except Exception as e:
        print(f"  FAIL: {e}")

if not z:
    print("Could not download GTFS.")
    sys.exit(1)

# Parse stops.txt
stops = list(csv.DictReader(io.StringIO(z.read("stops.txt").decode("utf-8"))))
print(f"\n{len(stops)} stops found")
print(f"Columns: {list(stops[0].keys())}")
print(f"Sample: {stops[0]}")

# Build GeoJSON
features = []
for s in stops:
    try:
        lon = float(s.get("stop_lon") or s.get("lon", 0))
        lat = float(s.get("stop_lat") or s.get("lat", 0))
        features.append({
            "type": "Feature",
            "properties": {
                "stop_id":   s.get("stop_id",""),
                "stop_name": s.get("stop_name",""),
                "zone_id":   s.get("zone_id",""),
            },
            "geometry": {"type":"Point","coordinates":[lon,lat]},
        })
    except:
        pass

fc = {"type":"FeatureCollection","features":features}
OUT_STOPS.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_STOPS,"w") as f:
    json.dump(fc, f, indent=2)
print(f"\nWrote {len(features)} stop features -> {OUT_STOPS}")

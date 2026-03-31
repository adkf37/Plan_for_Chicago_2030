import urllib.request, json, time, urllib.parse
from pathlib import Path
import sys

ROOT = Path(r"C:\Users\aaron\OneDrive\Desktop\OneDrive Desktop files\Sandboxes\Plan_for_Chicago_2030")

# All stations: (display_name, line_abbrev, colour, search_query)
STATIONS_TO_GEOCODE = [
    ("Chicago Union Station",    "BNSF",  "#dc143c", "Chicago Union Station, Chicago IL"),
    ("Western Ave",              "BNSF",  "#dc143c", "Metra Western Avenue station, Chicago IL"),
    ("Berwyn",                   "BNSF",  "#dc143c", "Metra Berwyn station, Berwyn IL"),
    ("Riverside",                "BNSF",  "#dc143c", "Metra Riverside station, Riverside IL"),
    ("LaGrange Road",            "BNSF",  "#dc143c", "Metra LaGrange Road station, La Grange IL"),
    ("Downers Grove/Main",       "BNSF",  "#dc143c", "Metra Downers Grove Main Street station IL"),
    ("Naperville",               "BNSF",  "#dc143c", "Metra Naperville station, Naperville IL"),
    ("Aurora",                   "BNSF",  "#dc143c", "Metra Aurora station, Aurora IL"),
    ("Chicago Ogilvie Center",   "UP-N",  "#0047ab", "Chicago Ogilvie Transportation Center, Chicago IL"),
    ("Clybourn",                 "UP-N",  "#0047ab", "Metra Clybourn station, Chicago IL"),
    ("Ravenswood",               "UP-N",  "#0047ab", "Metra Ravenswood station, Chicago IL"),
    ("Rogers Park",              "UP-N",  "#0047ab", "Metra Rogers Park station, Chicago IL"),
    ("Evanston Davis St",        "UP-N",  "#0047ab", "Metra Davis Street Evanston station IL"),
    ("Wilmette",                 "UP-N",  "#0047ab", "Metra Wilmette station, Wilmette IL"),
    ("Waukegan",                 "UP-N",  "#0047ab", "Metra Waukegan station, Waukegan IL"),
    ("Jefferson Park",           "UP-NW", "#0047ab", "Metra Jefferson Park station, Chicago IL"),
    ("Des Plaines",              "UP-NW", "#0047ab", "Metra Des Plaines station, Des Plaines IL"),
    ("Arlington Heights",        "UP-NW", "#0047ab", "Metra Arlington Heights station IL"),
    ("Barrington",               "UP-NW", "#0047ab", "Metra Barrington station, Barrington IL"),
    ("Oak Park",                 "UP-W",  "#0047ab", "Metra Oak Park station, Oak Park IL"),
    ("Elmhurst",                 "UP-W",  "#0047ab", "Metra Elmhurst station, Elmhurst IL"),
    ("Wheaton",                  "UP-W",  "#0047ab", "Metra Wheaton station, Wheaton IL"),
    ("Geneva",                   "UP-W",  "#0047ab", "Metra Geneva station, Geneva IL"),
    ("Glenview",                 "MD-N",  "#006400", "Metra Glenview station, Glenview IL"),
    ("Lake Forest",              "MD-N",  "#006400", "Metra Lake Forest station, Lake Forest IL"),
    ("Fox Lake",                 "MD-N",  "#006400", "Metra Fox Lake station, Fox Lake IL"),
    ("Maywood",                  "MD-W",  "#006400", "Metra Maywood station, Maywood IL"),
    ("Elmwood Park",             "MD-W",  "#006400", "Metra Elmwood Park station, Elmwood Park IL"),
    ("Elgin",                    "MD-W",  "#006400", "Metra Elgin station, Elgin IL"),
    ("Rosemont",                 "NCS",   "#ff8c00", "Metra Rosemont station, Rosemont IL"),
    ("Wheeling",                 "NCS",   "#ff8c00", "Metra Wheeling station, Wheeling IL"),
    ("Antioch",                  "NCS",   "#ff8c00", "Metra Antioch station, Antioch IL"),
    ("35th Archer Bridgeport",   "SWS",   "#8b008b", "Metra 35th Street Archer station, Chicago IL"),
    ("Chicago Ridge",            "SWS",   "#8b008b", "Metra Chicago Ridge station, Chicago Ridge IL"),
    ("Orland Park",              "SWS",   "#8b008b", "Metra Orland Park station, Orland Park IL"),
    ("Chicago LaSalle St",       "RI",    "#8b0000", "Chicago LaSalle Street Station, Chicago IL"),
    ("95th Beverly",             "RI",    "#8b0000", "Metra Beverly Hills 95th Street station, Chicago IL"),
    ("Blue Island",              "RI",    "#8b0000", "Metra Blue Island station, Blue Island IL"),
    ("Joliet",                   "RI",    "#8b0000", "Metra Joliet station, Joliet IL"),
    ("Millennium Station",       "ME",    "#b8960c", "Millennium Station Chicago IL"),
    ("Van Buren St",             "ME",    "#b8960c", "Metra Van Buren Street station, Chicago IL"),
    ("18th St",                  "ME",    "#b8960c", "Metra 18th Street station, Chicago IL"),
    ("47th St",                  "ME",    "#b8960c", "Metra 47th Street station, Chicago IL"),
    ("53rd Hyde Park",           "ME",    "#b8960c", "Metra 53rd Street Hyde Park station, Chicago IL"),
    ("63rd St",                  "ME",    "#b8960c", "Metra 63rd Street station, Chicago IL"),
    ("95th St",                  "ME",    "#b8960c", "Metra 95th Street station, Chicago IL"),
    ("Harvey",                   "ME",    "#b8960c", "Metra Harvey station, Harvey IL"),
    ("Chicago Heights",          "ME",    "#b8960c", "Metra Chicago Heights station, Chicago Heights IL"),
    ("Summit",                   "HC",    "#a0522d", "Metra Summit station, Summit IL"),
]

results = []
failed = []
BASE = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q="

for name, abbrev, colour, query in STATIONS_TO_GEOCODE:
    url = BASE + urllib.parse.quote(query) + "&countrycodes=us"
    req = urllib.request.Request(url, headers={"User-Agent": "chicago2030-map"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            hits = json.loads(r.read())
        if hits:
            lon = float(hits[0]["lon"])
            lat = float(hits[0]["lat"])
            results.append((name, abbrev, colour, lon, lat))
            print(f"  OK  {name:40s} [{lon:.4f}, {lat:.4f}]  ({hits[0]['display_name'][:60]})")
        else:
            failed.append((name, abbrev, colour, query))
            print(f"  MISS {name}")
    except Exception as e:
        failed.append((name, abbrev, colour, query))
        print(f"  ERR  {name}: {e}")
    time.sleep(0.5)   # Nominatim rate limit is 1 req/sec

print(f"\n{len(results)} geocoded, {len(failed)} failed")

OUT = ROOT / "data" / "geojson" / "metra_stations_geocoded.json"
with open(OUT, "w") as f:
    json.dump(results, f, indent=2)
print(f"Saved -> {OUT}")

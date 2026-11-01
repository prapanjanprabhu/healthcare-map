"""Build the analysis files for the map. Needs no API key; standard library only.
  deserts.geojson   ~2.7 km grid cells over INHABITED land, with distance (km) to the nearest hospital
  settlements.geojson  villages/towns more than 8 km from a hospital
  stats.json        headline numbers
  boundary.geojson  state outline
Usage: python build_deserts.py     (needs data.geojson from prepare_data.py; change AREA for another region)
"""
import json, math, urllib.request, urllib.parse

AREA = "Tamil Nadu, India"
STEP = 0.025          # grid size in degrees (~2.7 km)
NEAR_SETTLEMENT = 4   # km: a cell counts as inhabited if a settlement is this close
FAR = 10              # km threshold for "far from a hospital"
UA = {"User-Agent": "health-map-challenge/1.0"}

def get(url, data=None):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=300))

def overpass(q):
    return get("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": q}).encode())["elements"]

boundary = get("https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
    {"q": AREA, "format": "geojson", "polygon_geojson": 1, "polygon_threshold": 0.003, "limit": 1}))["features"][0]["geometry"]
polys = boundary["coordinates"] if boundary["type"] == "MultiPolygon" else [boundary["coordinates"]]

def in_ring(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside

def in_state(x, y):
    return any(in_ring(x, y, p[0]) and not any(in_ring(x, y, h) for h in p[1:]) for p in polys)

xs = [c[0] for p in polys for c in p[0]]
ys = [c[1] for p in polys for c in p[0]]
PAD = 0.6
bbox = f"({min(ys)-PAD},{min(xs)-PAD},{max(ys)+PAD},{max(xs)+PAD})"

def center(e):
    return (e.get("lon") or e.get("center", {}).get("lon"), e.get("lat") or e.get("center", {}).get("lat"))

# hospitals in a buffer around the state, so border cells are not wrongly flagged
hospitals = [c for c in map(center, overpass(f'[out:json][timeout:180];nwr["amenity"="hospital"]{bbox};out center;')) if c[0] is not None]
print(len(hospitals), "hospitals used (state + buffer)")
places = overpass(f'[out:json][timeout:180];node["place"~"^(city|town|village|hamlet)$"]{bbox};out;')
print(len(places), "settlements")

TILE = 0.25
def index(points):
    t = {}
    for p in points:
        t.setdefault((int(p[0] // TILE), int(p[1] // TILE)), []).append(p)
    return t

def km(x1, y1, x2, y2):
    return math.hypot((x2 - x1) * math.cos(math.radians((y1 + y2) / 2)) * 111.32, (y2 - y1) * 110.57)

def nearest(t, x, y, limit=12):
    tx, ty, r, best = int(x // TILE), int(y // TILE), 0, 1e9
    while r < limit:
        for i in range(tx - r, tx + r + 1):
            for j in range(ty - r, ty + r + 1):
                if max(abs(i - tx), abs(j - ty)) == r:
                    for p in t.get((i, j), ()):
                        d = km(x, y, p[0], p[1])
                        if d < best:
                            best = d
        if best < r * TILE * 100:
            break
        r += 1
    return best

H = index(hospitals)
S = index([(e["lon"], e["lat"]) for e in places])

# settlements: distance to nearest hospital
setts, total = [], 0
for e in places:
    if e["tags"].get("place") == "hamlet" or not in_state(e["lon"], e["lat"]):
        continue
    total += 1
    d = nearest(H, e["lon"], e["lat"])
    if d > 8:
        setts.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(e["lon"], 4), round(e["lat"], 4)]},
                      "properties": {"name": e["tags"].get("name:en") or e["tags"].get("name", "Unnamed settlement"),
                                     "kind": e["tags"]["place"], "km": round(d, 1)}})
far = [s for s in setts if s["properties"]["km"] > FAR]

# grid over inhabited land
cells, inland = [], 0
x = math.floor(min(xs) / STEP) * STEP
while x < max(xs):
    y = math.floor(min(ys) / STEP) * STEP
    while y < max(ys):
        cx, cy = x + STEP / 2, y + STEP / 2
        if in_state(cx, cy):
            inland += 1
            if nearest(S, cx, cy, 4) <= NEAR_SETTLEMENT:
                d = round(nearest(H, cx, cy), 1)
                a, b, c, e = round(x, 3), round(y, 3), round(x + STEP, 3), round(y + STEP, 3)
                cells.append({"type": "Feature", "properties": {"km": d},
                              "geometry": {"type": "Polygon", "coordinates": [[[a, b], [c, b], [c, e], [a, e], [a, b]]]}})
        y += STEP
    x += STEP

worst = max(setts, key=lambda s: s["properties"]["km"])
stats = {"settlements": total, "far_settlements": len(far), "pct_far_settlements": round(100 * len(far) / total, 1),
         "far_km": FAR, "inhabited_cells": len(cells), "pct_far_land": round(100 * sum(c["properties"]["km"] > FAR for c in cells) / len(cells), 1),
         "worst": worst["properties"] | {"coordinates": worst["geometry"]["coordinates"]}}

dump = lambda name, obj: json.dump(obj, open(name, "w"), separators=(",", ":"))
dump("deserts.geojson", {"type": "FeatureCollection", "features": cells})
dump("settlements.geojson", {"type": "FeatureCollection", "features": setts})
dump("boundary.geojson", {"type": "Feature", "properties": {}, "geometry": boundary})
dump("stats.json", stats)
print(json.dumps(stats, indent=1))

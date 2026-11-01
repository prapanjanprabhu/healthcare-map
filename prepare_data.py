"""Download healthcare places (hospitals, clinics, pharmacies) from OpenStreetMap
via the Overpass API and save them as data.geojson. No API key, standard library only.
Usage: python prepare_data.py            (change AREA below to any region name)
"""
import json, urllib.request, urllib.parse

AREA = "Tamil Nadu"   # <- any state/district/country name known to OpenStreetMap
QUERY = f"""
[out:json][timeout:180];
area["name"="{AREA}"]->.a;
nwr["amenity"~"^(hospital|clinic|pharmacy)$"](area.a);
out center tags;
"""
req = urllib.request.Request(
    "https://overpass-api.de/api/interpreter",
    data=urllib.parse.urlencode({"data": QUERY}).encode(),
    headers={"User-Agent": "health-map-challenge/1.0"},
)
elements = json.load(urllib.request.urlopen(req, timeout=300))["elements"]

features = []
for e in elements:
    lat = e.get("lat") or e.get("center", {}).get("lat")
    lon = e.get("lon") or e.get("center", {}).get("lon")
    if lat is None or lon is None:
        continue
    t = e.get("tags", {})
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "name": t.get("name", "(unnamed)"),
            "type": t["amenity"],
            "address": ", ".join(filter(None, [t.get("addr:street"), t.get("addr:city")])),
            "phone": t.get("phone", ""),
            "emergency": t.get("emergency", ""),
            "beds": t.get("beds", ""),
        },
    })

json.dump({"type": "FeatureCollection", "features": features}, open("data.geojson", "w"))
print(f"Saved {len(features)} places to data.geojson")
from collections import Counter
print(Counter(f["properties"]["type"] for f in features))

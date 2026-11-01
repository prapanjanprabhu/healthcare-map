# Healthcare Deserts of Tamil Nadu

An interactive map that shows **how far every part of Tamil Nadu is from the nearest hospital**, built on **Amazon Location Service**.

**Finding:** **1,359 of 16,113 towns and villages (8.4%) in Tamil Nadu are more than 10 km from a hospital.** The most remote, Urigam, is about 24 km away. Click anywhere on the map to get the real road route and drive time to the nearest hospital.

## What you can do on the map
- See a distance surface: ~2.7 km cells over inhabited land, coloured by straight-line distance to the nearest hospital, plus a dot for every village 10+ km away.
- Click any spot, or search a town, to get the road route, distance and drive time to the nearest hospital.
- Zoom in to see 9,290 hospitals, clinics and pharmacies; filter by type; click one for details.
- "Fly to the most remote village" jumps to Urigam and routes from it.

## Dataset
OpenStreetMap (ODbL), pulled with the Overpass API: every `amenity=hospital|clinic|pharmacy` in Tamil Nadu (5,833 hospitals, 2,670 clinics, 787 pharmacies), about 16,000 towns and villages (`place=*`), and the state boundary from Nominatim. Public data only, no personal information.

## How it works (AWS pieces)
| Piece | Service | Why |
|---|---|---|
| Base map | **Amazon Location Service, Maps** (v2 Standard style, MapLibre GL JS) | Vector tiles with one API key |
| Search | **Amazon Location Service, Places** (Geocode) | Turns a town or address into a point |
| Route + drive time | **Amazon Location Service, Routes** (CalculateRoutes) | Real road distance, not straight line |
| Hosting | **AWS Amplify Hosting** | Live HTTPS site |
| Data files | **Amazon S3** | Stores the processed GeoJSON |

The API key is restricted to the site's URL in the Amazon Location console.

## Pipeline (reusable for any region)
1. `python prepare_data.py` downloads facilities to `data.geojson` (change `AREA`).
2. `python build_deserts.py` measures, for every town and village, the distance to the nearest hospital (counting hospitals just across state borders), and builds a ~2.7 km grid over inhabited land (cells within 4 km of a mapped settlement, so forest and hills are left out). Output: `deserts.geojson`, `settlements.geojson`, `stats.json`, `boundary.geojson`.
3. `index.html` loads the data files, shades the grid, clusters the facilities, and calls Amazon Location for map, search and routes.

Standard-library Python only. Swap `AREA` and the map centre and it works for any state or country.

## Limits
- Shading uses straight-line distance; the route panel uses road distance.
- OpenStreetMap coverage varies, so some hospitals may be missing and some areas may look more remote than they are.
- Settlements are not weighted by population, and OpenStreetMap place coverage varies, so a few remote hamlets may be missing.
- Distance is not the same as quality or capacity of care.

## Run locally
1. Put your Amazon Location API key and region in `index.html`.
2. `python -m http.server 8000` and open http://localhost:8000

## License
Code: MIT (see `LICENSE`). Data: © OpenStreetMap contributors, ODbL.

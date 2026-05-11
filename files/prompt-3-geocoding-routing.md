# Prompt 3 — Geocoding & Routing Services

Implement `backend/planner/services/geocoding.py` and `backend/planner/services/routing.py`.

## geocoding.py — uses Nominatim (OpenStreetMap)

- Base URL: `https://nominatim.openstreetmap.org/search`
- Must send a User-Agent header (Nominatim requires it): `"spotter-eld/1.0"`
- Function: `geocode(address: str) -> dict` with keys `{lat: float, lon: float, display_name: str}`
- Raise `GeocodingError` if no results.
- Cache results in-memory (`functools.lru_cache`) keyed by address string.
- Add a small `time.sleep(1)` between live calls to respect Nominatim's 1 req/sec policy.

## routing.py — uses OSRM public demo (no key needed)

- Base URL: `https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2};{lon3},{lat3}?overview=full&geometries=geojson&steps=false`
- Function: `get_route(waypoints: list[tuple[float, float]]) -> dict` with keys:
    - `distance_miles`: float (convert from meters)
    - `duration_hours`: float (convert from seconds, but this is CAR time; we won't actually use it for HOS — HOS uses 55 mph truck speed)
    - `geometry`: list of `[lon, lat]` pairs (the polyline)
    - `legs`: list of `{distance_miles, duration_hours}` per leg
- Raise `RoutingError` on non-200 or no routes.
- Set a 15-second timeout.

Both modules should have clean exception classes and decent error messages. No external deps beyond `requests` (already in requirements.txt).

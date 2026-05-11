"""
Routing service — wraps the OSRM public demo API (no API key required).

OSRM coordinate order is lon,lat; waypoints accepted by this module use the
standard geographic (lat, lon) convention and are converted internally.

Note: OSRM returns car travel times. Duration is included for completeness
but HOS calculations use 55 mph truck speed, not this figure.
"""

import requests

_OSRM_BASE = "https://router.project-osrm.org/route/v1/driving"
_METERS_PER_MILE = 1_609.344
_TIMEOUT = 15  # seconds


class RoutingError(Exception):
    """Raised when a route cannot be obtained from OSRM."""


def get_route(waypoints: list[tuple[float, float]]) -> dict:
    """
    Fetch a driving route between two or more waypoints.

    Parameters
    ----------
    waypoints : list of (lat, lon) tuples — at least two required.

    Returns
    -------
    dict with keys:
        distance_miles  : float — total route distance
        duration_hours  : float — OSRM car travel time (not used for HOS)
        geometry        : list of [lon, lat] pairs forming the polyline
        legs            : list of {distance_miles, duration_hours} per segment

    Raises
    ------
    RoutingError
        On HTTP error, OSRM error status, or empty route list.
    """
    if len(waypoints) < 2:
        raise RoutingError("At least two waypoints are required.")

    # OSRM expects lon,lat order; our API accepts the conventional lat,lon.
    coord_str = ";".join(f"{lon},{lat}" for lat, lon in waypoints)
    url = f"{_OSRM_BASE}/{coord_str}"

    try:
        resp = requests.get(
            url,
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise RoutingError(f"OSRM request failed: {exc}") from exc

    if resp.status_code != 200:
        raise RoutingError(f"OSRM returned HTTP {resp.status_code}: {resp.text[:200]}")

    data = resp.json()

    if data.get("code") != "Ok":
        raise RoutingError(f"OSRM error: {data.get('message', data.get('code', 'unknown'))}")

    routes = data.get("routes")
    if not routes:
        raise RoutingError("OSRM returned no routes for the given waypoints.")

    route = routes[0]

    def _leg(leg: dict) -> dict:
        return {
            "distance_miles": leg["distance"] / _METERS_PER_MILE,
            "duration_hours": leg["duration"] / 3_600,
        }

    return {
        "distance_miles": route["distance"] / _METERS_PER_MILE,
        "duration_hours": route["duration"] / 3_600,
        "geometry": route["geometry"]["coordinates"],   # list of [lon, lat]
        "legs": [_leg(leg) for leg in route.get("legs", [])],
    }

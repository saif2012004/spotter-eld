"""
Geocoding service — wraps Nominatim (OpenStreetMap).

Rate limit: 1 request/second per Nominatim usage policy.
Results are cached in-process so the sleep only fires on actual HTTP calls.
"""

import time
from functools import lru_cache

import requests

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "spotter-eld/1.0"}
_TIMEOUT = 10  # seconds


class GeocodingError(Exception):
    """Raised when an address cannot be geocoded."""


@lru_cache(maxsize=512)
def geocode(address: str) -> dict:
    """
    Convert a free-text address to coordinates.

    Returns
    -------
    dict with keys:
        lat          : float — latitude
        lon          : float — longitude
        display_name : str  — canonical address as returned by Nominatim

    Raises
    ------
    GeocodingError
        If Nominatim returns no results or the request fails.
    """
    # Respect Nominatim's 1 req/sec policy on every cache miss.
    time.sleep(1)

    try:
        resp = requests.get(
            _NOMINATIM_URL,
            params={"q": address, "format": "json", "limit": 1},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise GeocodingError(f"Nominatim request failed for {address!r}: {exc}") from exc

    if resp.status_code != 200:
        raise GeocodingError(
            f"Nominatim returned HTTP {resp.status_code} for {address!r}"
        )

    results = resp.json()
    if not results:
        raise GeocodingError(f"No geocoding results found for {address!r}")

    hit = results[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "display_name": hit.get("display_name", address),
    }

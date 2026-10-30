"""Place name <-> coordinates, restricted to Punjab."""
from config import OPEN_METEO_GEOCODE_URL, PUNJAB_BOUNDS

from .http import FetchError, get_json

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
# Nominatim's usage policy requires an identifying User-Agent
USER_AGENT = {"User-Agent": "FasalKavach-hackathon/0.1"}


def in_punjab(lat: float, lon: float) -> bool:
    b = PUNJAB_BOUNDS
    return b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]


def geocode(query: str) -> dict:
    """Village/town/district name -> coordinates (Open-Meteo geocoding)."""
    data, meta = get_json(OPEN_METEO_GEOCODE_URL,
                          {"name": query, "count": 10, "countryCode": "IN", "language": "en"},
                          ttl=24 * 3600)
    for r in data.get("results", []):
        if r.get("admin1") == "Punjab" or in_punjab(r["latitude"], r["longitude"]):
            return {
                "name": r["name"], "district": r.get("admin2"), "state": "Punjab",
                "lat": r["latitude"], "lon": r["longitude"],
                "source": "Open-Meteo Geocoding API", **meta,
            }
    raise FetchError(f"No place called '{query}' found in Punjab")


def reverse_geocode(lat: float, lon: float) -> dict:
    """Coordinates -> district name (OpenStreetMap Nominatim). Needed for mandi prices."""
    data, meta = get_json(NOMINATIM_REVERSE_URL,
                          {"lat": lat, "lon": lon, "format": "json", "zoom": 10},
                          ttl=24 * 3600, headers=USER_AGENT)
    addr = data.get("address", {})
    district = (addr.get("state_district") or addr.get("county") or addr.get("city") or "")
    district = district.replace(" District", "").replace(" Tahsil", "").strip() or None
    return {"district": district, "state": addr.get("state"),
            "display_name": data.get("display_name"),
            "source": "OpenStreetMap Nominatim", **meta}

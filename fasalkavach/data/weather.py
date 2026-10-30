"""Weather data from Open-Meteo (free, no API key).

Fallback chain: ECMWF ensemble -> GFS ensemble -> single deterministic forecast.
"""
from config import ENSEMBLE_MODELS, FORECAST_DAYS, OPEN_METEO_ENSEMBLE_URL, OPEN_METEO_FORECAST_URL

from .http import FetchError, get_json

VARIABLES = ["precipitation", "temperature_2m", "wind_gusts_10m"]


def _split_members(hourly: dict) -> dict[str, list[list]]:
    """Open-Meteo returns `precipitation`, `precipitation_member01`, ... -> list of members."""
    members = {}
    for var in VARIABLES:
        series = [v for k, v in sorted(hourly.items())
                  if k == var or k.startswith(var + "_member")]
        if series:
            members[var] = series
    return members


def get_ensemble_forecast(lat: float, lon: float) -> dict:
    errors = []
    for model in ENSEMBLE_MODELS:
        params = {
            "latitude": lat, "longitude": lon,
            "hourly": ",".join(VARIABLES),
            "models": model,
            "forecast_days": FORECAST_DAYS,
            "timezone": "Asia/Kolkata",
        }
        try:
            data, meta = get_json(OPEN_METEO_ENSEMBLE_URL, params)
            members = _split_members(data.get("hourly", {}))
            if not members:
                raise FetchError(f"{model}: response had no ensemble members")
            return {
                "times": data["hourly"]["time"],
                "members": members,
                "model": model,
                "is_ensemble": True,
                "source": f"Open-Meteo Ensemble API ({model}, {len(members['precipitation'])} members)",
                **meta,
            }
        except (FetchError, KeyError) as e:
            errors.append(str(e))

    # Last resort: one deterministic run. Probabilities become 0 or 1 -> low confidence.
    params = {"latitude": lat, "longitude": lon, "hourly": ",".join(VARIABLES),
              "forecast_days": FORECAST_DAYS, "timezone": "Asia/Kolkata"}
    try:
        data, meta = get_json(OPEN_METEO_FORECAST_URL, params)
    except FetchError as e:
        errors.append(str(e))
        raise FetchError("All weather sources failed: " + " | ".join(errors))
    hourly = data["hourly"]
    return {
        "times": hourly["time"],
        "members": {v: [hourly[v]] for v in VARIABLES if v in hourly},
        "model": "deterministic",
        "is_ensemble": False,
        "source": "Open-Meteo Forecast API (single run - ensemble unavailable)",
        "warnings": errors,
        **meta,
    }


def get_soil_moisture(lat: float, lon: float) -> dict:
    params = {"latitude": lat, "longitude": lon,
              "hourly": "soil_moisture_0_to_1cm,soil_moisture_1_to_3cm",
              "forecast_days": 2, "timezone": "Asia/Kolkata"}
    data, meta = get_json(OPEN_METEO_FORECAST_URL, params)
    vals = [v for v in data.get("hourly", {}).get("soil_moisture_1_to_3cm", [])[:24] if v is not None]
    if not vals:
        raise FetchError("Soil moisture not available for this location")
    return {
        "topsoil_moisture_m3m3": round(sum(vals) / len(vals), 3),
        "source": "Open-Meteo Forecast API (soil_moisture_1_to_3cm, next 24h mean)",
        **meta,
    }

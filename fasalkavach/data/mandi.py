"""Live mandi prices from Agmarknet via the data.gov.in API.

Fallback chain: district modal price -> Punjab-wide modal price -> official MSP.
"""
from statistics import median

from config import AGMARKNET_URL, DATA_GOV_API_KEY
from engine.crops import CROPS, SOURCES

from .http import FetchError, get_json


def _query(commodity: str, district: str | None) -> tuple[list, dict]:
    # data.gov.in has used both `filters[x]` and `filters[x.keyword]` - try both
    for suffix in (".keyword", ""):
        params = {"api-key": DATA_GOV_API_KEY, "format": "json", "limit": 100,
                  f"filters[state{suffix}]": "Punjab",
                  f"filters[commodity{suffix}]": commodity}
        if district:
            params[f"filters[district{suffix}]"] = district
        data, meta = get_json(AGMARKNET_URL, params)
        records = data.get("records", [])
        if records:
            return records, meta
    return [], meta


def get_mandi_price(crop: str, district: str | None = None) -> dict:
    info = CROPS[crop]
    commodity = info["agmarknet_commodity"]
    warnings = []

    if not DATA_GOV_API_KEY:
        warnings.append("DATA_GOV_API_KEY not set - live mandi prices unavailable")
    else:
        for scope in ([district, None] if district else [None]):
            try:
                records, meta = _query(commodity, scope)
            except FetchError as e:
                warnings.append(str(e))
                break
            prices = [float(r["modal_price"]) for r in records
                      if str(r.get("modal_price", "")).replace(".", "", 1).isdigit()
                      and float(r["modal_price"]) > 0]
            if prices:
                markets = sorted({r.get("market", "?") for r in records})[:5]
                dates = sorted({r.get("arrival_date", "") for r in records})
                return {
                    "price_rs_per_q": round(median(prices)),
                    "basis": f"median modal price, {scope + ' district' if scope else 'Punjab'}",
                    "markets": markets,
                    "arrival_date": dates[-1] if dates else None,
                    "source": "Agmarknet via data.gov.in",
                    "is_fallback": False,
                    "warnings": warnings,
                    **meta,
                }
            warnings.append(f"No {commodity} arrivals reported for {scope or 'Punjab'} today")

    return {
        "price_rs_per_q": info["msp_rs_per_q"],
        "basis": "Minimum Support Price (live mandi price unavailable)",
        "source": SOURCES["msp"],
        "is_fallback": True,
        "warnings": warnings,
    }

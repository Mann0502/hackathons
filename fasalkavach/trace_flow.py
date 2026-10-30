"""Run the pipeline step by step and print what each step produces.

    python trace_flow.py                       # live APIs, Ludhiana wheat
    python trace_flow.py --place Bathinda --crop rice --planted 2026-07-01
    python trace_flow.py --lat 30.9 --lon 75.85 --agent   # also run the AI agent
    python trace_flow.py --offline              # no internet: uses the test fixture data
"""
import argparse
import json
from datetime import date, timedelta

from agent.tools import FarmSession, ToolError


def show(title: str, data, keys=None):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    if keys and isinstance(data, dict):
        data = {k: data.get(k) for k in keys}
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False)[:2500])


def use_offline_data():
    """Swap the live API calls for the synthetic test fixture (offline learning only)."""
    from agent import tools
    from tests.test_engine import make_ensemble
    import tests.test_engine as te
    te.TODAY = date.today()
    ens = make_ensemble(10, [[30, 30, 0, 0, 0, 0, 0, 0, 0, 0]] * 3 + [[0] * 10], gust=45)
    stub = {"fetched_at": "offline", "stale": False}
    tools.get_ensemble_forecast = lambda lat, lon: {**ens, "model": "OFFLINE", "is_ensemble": True,
                                                    "source": "offline test fixture", **stub}
    tools.get_soil_moisture = lambda lat, lon: {"topsoil_moisture_m3m3": 0.42, "source": "offline", **stub}
    tools.geocode = lambda q: {"name": q, "district": "Ludhiana", "lat": 30.9, "lon": 75.85, "source": "offline", **stub}
    tools.reverse_geocode = lambda lat, lon: {"district": "Ludhiana", "source": "offline", **stub}
    tools.get_mandi_price = lambda crop, d: {"price_rs_per_q": 2450, "basis": "offline", "source": "offline",
                                             "is_fallback": False, "warnings": []}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--place", default="Ludhiana")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--crop", default="wheat", choices=["wheat", "rice"])
    p.add_argument("--planted", default=(date.today() - timedelta(days=140)).isoformat())
    p.add_argument("--area", type=float, default=5)
    p.add_argument("--yield-q", type=float)
    p.add_argument("--lang", default="en", choices=["en", "hi", "pa"])
    p.add_argument("--agent", action="store_true", help="also run the AI agent (needs ANTHROPIC_API_KEY)")
    p.add_argument("--offline", action="store_true")
    a = p.parse_args()

    if a.offline:
        use_offline_data()
        print("OFFLINE MODE: weather/price/location are synthetic test data, not real.")

    s = FarmSession()
    try:
        show("STEP 1  resolve_location  (data/location.py)",
             s.resolve_location(place_name=None if a.lat else a.place, lat=a.lat, lon=a.lon))
        show("STEP 2  get_crop_stage  (engine/stage.py)",
             s.get_crop_stage(a.crop, a.planted))
        r = s.get_weather_risk()
        show("STEP 3a forecast used  (data/weather.py)", r["forecast"])
        show("STEP 3b event probabilities  (engine/risk.py)",
             {k: v["window"] for k, v in s.risks.items()})
        show("STEP 3c heavy rain day by day", s.risks.get("heavy_rain", {}).get("daily", [])[:7])
        try:
            show("STEP 4  get_soil_moisture  (data/weather.py)", s.get_soil_moisture())
        except ToolError as e:
            print(f"\nSTEP 4  soil moisture skipped (optional): {e}")
        show("STEP 5  get_mandi_price  (data/mandi.py)", s.get_mandi_price())
        d = s.evaluate_actions(a.area, a.yield_q)
        show("STEP 6a expected loss if farmer does nothing  (engine/decision.py)",
             d, ["crop_value_rs_per_acre", "expected_loss_7d_rs_per_acre", "event_losses", "soil_note"])
        show("STEP 6b actions: benefit vs cost", d["actions"])
        show("Sources cited", s.sources)
        if s.warnings:
            show("Warnings", s.warnings)
    except ToolError as e:
        print(f"\nSTOPPED: {e}")
        return

    if a.agent:
        from agent.loop import AgentUnavailable, run_agent
        req = {"place_name": a.place, "lat": a.lat, "lon": a.lon, "crop": a.crop, "planted_on": a.planted,
               "area_acres": a.area, "yield_q_per_acre": a.yield_q, "language": a.lang}
        try:
            out = run_agent(req, FarmSession())
            show("STEP 7  AI agent trace  (agent/loop.py)", out["trace"])
            show("STEP 8  validated advisory", out["advisory"])
        except AgentUnavailable as e:
            print(f"\nAgent unavailable: {e}")


if __name__ == "__main__":
    main()

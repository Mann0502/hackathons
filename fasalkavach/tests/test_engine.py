"""Unit tests for the stage, risk and decision logic.

The ensemble below is a small synthetic test fixture (not app data): it lets us
check the maths exactly, e.g. 3 of 4 members raining -> 75%.
"""
from datetime import date, timedelta

import pytest

from engine.decision import assess
from engine.crops import DEFAULT_COSTS
from engine.risk import compute_event_probabilities, daily_aggregate
from engine.stage import StageError, get_crop_stage

TODAY = date(2026, 3, 10)


def make_ensemble(days: int, rain_per_member_day: list[list[float]], tmax=25.0, tmin=12.0, gust=15.0):
    """Hourly series where each member's daily rain falls in one hour."""
    times, members = [], {"precipitation": [], "temperature_2m": [], "wind_gusts_10m": []}
    for d in range(days):
        for h in range(24):
            times.append(f"{(TODAY + timedelta(days=d)).isoformat()}T{h:02d}:00")
    for member_rain in rain_per_member_day:
        precip, temp, wind = [], [], []
        for d in range(days):
            for h in range(24):
                precip.append(member_rain[d] if h == 12 else 0.0)
                temp.append(tmax if h == 14 else tmin)
                wind.append(gust)
        members["precipitation"].append(precip)
        members["temperature_2m"].append(temp)
        members["wind_gusts_10m"].append(wind)
    return {"times": times, "members": members}


# ---------- stage ----------

def test_wheat_stage_grain_filling():
    s = get_crop_stage("wheat", "2025-11-10", TODAY)   # 120 days
    assert s["stage"] == "grain_filling"
    assert s["days_since_planting"] == 120


def test_future_date_rejected():
    with pytest.raises(StageError, match="future"):
        get_crop_stage("wheat", "2026-04-01", TODAY)


def test_season_over_rejected():
    with pytest.raises(StageError, match="harvested"):
        get_crop_stage("rice", "2025-06-15", TODAY)


# ---------- risk ----------

def test_daily_aggregate_sum_and_skips_none():
    times = ["2026-03-10T00:00", "2026-03-10T01:00", "2026-03-11T00:00"]
    assert daily_aggregate(times, [1.0, None, 2.0], "sum") == {"2026-03-10": 1.0, "2026-03-11": 2.0}


def test_probabilities_from_members():
    # 4 members x 7 days. Day 1: members 0-2 get 25 mm, member 3 dry -> 75% heavy rain
    rain = [[25, 0, 0, 0, 0, 0, 0]] * 3 + [[0] * 7]
    risks = compute_event_probabilities(make_ensemble(7, rain), "wheat")
    assert risks["heavy_rain"]["daily"][0]["probability"] == 0.75
    assert risks["heavy_rain"]["daily"][1]["probability"] == 0.0
    assert risks["heavy_rain"]["window"]["2d"] == 0.75
    assert risks["frost"]["window"]["7d"] == 0.0
    assert risks["heat_stress"]["threshold"] == 34.0


def test_window_counts_members_not_days():
    # Each member rains on a different day: daily P = 25%, but every member has rain in 7 days
    rain = [[30 if d == m else 0 for d in range(7)] for m in range(4)]
    risks = compute_event_probabilities(make_ensemble(7, rain), "wheat")
    assert risks["heavy_rain"]["window"]["7d"] == 1.0
    assert risks["heavy_rain"]["window"]["2d"] == 0.5


# ---------- decision ----------

FARM = {"area_acres": 5, "yield_q_per_acre": 20, "price_rs_per_q": 2400}


def test_early_harvest_recommended_at_maturity_when_rain_likely():
    stage = get_crop_stage("wheat", "2025-10-20", TODAY)   # 141 days -> maturity
    rain = [[30, 30, 0, 0, 0, 0, 0]] * 3 + [[0] * 7]
    risks = compute_event_probabilities(make_ensemble(7, rain), "wheat")
    d = assess("wheat", stage, risks, FARM, DEFAULT_COSTS)
    eh = next(a for a in d["actions"] if a["action_id"] == "early_harvest")
    # benefit = 0.9 effectiveness x 0.75 P x 0.15 damage x 48,000 value = 4,860
    assert eh["benefit_rs_per_acre"] == 4860
    assert eh["recommended"] is True
    assert "postpone_spray" in d["recommended_actions"]


def test_nothing_recommended_when_dry():
    stage = get_crop_stage("wheat", "2025-10-20", TODAY)
    risks = compute_event_probabilities(make_ensemble(7, [[0] * 7] * 4), "wheat")
    d = assess("wheat", stage, risks, FARM, DEFAULT_COSTS)
    assert d["recommended_actions"] == []
    assert d["expected_loss_7d_rs_per_acre"] == 0


def test_spray_postponed_only_above_break_even():
    stage = get_crop_stage("wheat", "2025-12-20", TODAY)
    # 1 of 4 members rains in 2 days -> 25% < 35% break-even -> keep spraying
    rain = [[5, 0, 0, 0, 0, 0, 0]] + [[0] * 7] * 3
    risks = compute_event_probabilities(make_ensemble(7, rain), "wheat")
    d = assess("wheat", stage, risks, FARM, DEFAULT_COSTS)
    assert "postpone_spray" not in d["recommended_actions"]


def test_wet_soil_increases_heavy_rain_damage():
    stage = get_crop_stage("wheat", "2025-10-20", TODAY)
    rain = [[30] * 7] * 4
    risks = compute_event_probabilities(make_ensemble(7, rain), "wheat")
    dry = assess("wheat", stage, risks, FARM, DEFAULT_COSTS, {"topsoil_moisture_m3m3": 0.2})
    wet = assess("wheat", stage, risks, FARM, DEFAULT_COSTS, {"topsoil_moisture_m3m3": 0.45})
    assert wet["expected_loss_7d_rs_per_acre"] > dry["expected_loss_7d_rs_per_acre"]
    assert wet["soil_note"]

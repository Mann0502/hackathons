"""Turn an ensemble weather forecast into event probabilities.

An ensemble forecast is the same weather model run many times (e.g. 51 for
ECMWF) with slightly different starting conditions. If 33 of 51 runs show
>= 20 mm of rain tomorrow, P(heavy rain tomorrow) = 33/51 = 65%.
"""
from collections import defaultdict
from statistics import median

from .crops import EVENTS

WINDOWS = (2, 3, 5, 7, 10)


def _threshold(event: dict, crop: str) -> float:
    return event["per_crop"][crop] if "per_crop" in event else event["threshold"]


def _exceeds(value: float, op: str, threshold: float) -> bool:
    return value >= threshold if op == ">=" else value <= threshold


def daily_aggregate(times: list[str], member_hourly: list, how: str) -> dict[str, float]:
    """Collapse one member's hourly series into one value per day (sum/max/min)."""
    by_day = defaultdict(list)
    for t, v in zip(times, member_hourly):
        if v is not None:
            by_day[t[:10]].append(v)
    agg = {"sum": sum, "max": max, "min": min}[how]
    return {day: agg(vals) for day, vals in by_day.items() if vals}


def compute_event_probabilities(ensemble: dict, crop: str, events: list[str] | None = None) -> dict:
    """Return per-day and per-window probabilities for each weather event.

    `ensemble` = {"times": [...hourly ISO times...],
                  "members": {variable: [member0_hourly, member1_hourly, ...]}}
    """
    times = ensemble["times"]
    results = {}

    for key in events or EVENTS:
        event = EVENTS[key]
        if "per_crop" in event and crop not in event["per_crop"]:
            continue
        members = ensemble["members"].get(event["variable"])
        if not members:
            continue  # variable missing from this forecast - skip, don't guess
        thr = _threshold(event, crop)

        member_days = [daily_aggregate(times, m, event["agg"]) for m in members]
        days = sorted(set().union(*member_days))
        # Drop days where most members have no data (usually the partial last day)
        days = [d for d in days if sum(d in md for md in member_days) >= len(members) / 2]

        daily = []
        for d in days:
            vals = [md[d] for md in member_days if d in md]
            hits = sum(_exceeds(v, event["op"], thr) for v in vals)
            daily.append({
                "date": d,
                "probability": round(hits / len(vals), 3),
                "median_value": round(median(vals), 1),
            })

        # Window probability: share of members where the event happens on ANY day
        # in the window. This is more honest than adding up daily probabilities.
        window = {}
        for n in WINDOWS:
            win_days = days[:n]
            if len(win_days) < n:
                continue
            hit_members = sum(
                any(d in md and _exceeds(md[d], event["op"], thr) for d in win_days)
                for md in member_days
            )
            window[f"{n}d"] = round(hit_members / len(member_days), 3)

        results[key] = {
            "label": event["label"],
            "variable": event["variable"],
            "threshold": thr,
            "members": len(members),
            "daily": daily,
            "window": window,
            "source": event["source"],
        }
    return results

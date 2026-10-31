"""Check a registered field, describe the result, and decide when to alert.

Each check produces a small `snapshot` (probabilities, recommended actions, Rs).
We store the last snapshot per field and only alert when the new one is
meaningfully worse - so farmers are not spammed every 6 hours.
"""
from datetime import datetime, timezone

from agent.tools import FarmSession, ToolError
from engine.crops import CROPS

from .i18n import ACTIONS, EVENTS, STAGES, label, rupees, t

# Alert when an event's 7-day probability rises by at least this much AND ends above ALERT_MIN_PROB
ALERT_RISE = 0.25
ALERT_MIN_PROB = 0.40


def assess_field(field: dict) -> dict:
    """Run the full pipeline for one stored field. Raises ToolError on failure."""
    s = FarmSession()
    # Location was resolved at registration - reuse it instead of geocoding again
    s.location = {"lat": field["lat"], "lon": field["lon"], "name": field["place"],
                  "district": field.get("district")}
    s.get_crop_stage(field["crop"], field["planted_on"])
    s.get_weather_risk()
    try:
        s.get_soil_moisture()
    except ToolError:
        pass  # optional input
    s.get_mandi_price()
    d = s.evaluate_actions(field["area_acres"])

    # Events this crop stage is sensitive to, plus plain rain (drives spray/irrigation advice)
    shown = [e for e in s.risks if e in s.stage["sensitivity"] or e == "rain"]
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stage": s.stage["stage"],
        "days": s.stage["days_since_planting"],
        "risks": {e: s.risks[e]["window"].get("7d", 0.0) for e in shown},
        "recommended": d["recommended_actions"],
        "actions": [{"id": a["action_id"], "net": a["net_benefit_rs_per_acre"]}
                    for a in d["actions"] if a["recommended"]],
        "loss_per_acre": d["expected_loss_7d_rs_per_acre"],
        "price": s.price["price_rs_per_q"],
        "price_is_msp": s.price.get("is_fallback", False),
        "forecast_source": s.forecast_meta["source"],
        "is_ensemble": s.forecast_meta["is_ensemble"],
    }


def find_changes(old: dict | None, new: dict) -> list[dict]:
    """What got worse since the last check? Empty list = no alert."""
    if not old:
        return []
    changes = []
    for event, p in new["risks"].items():
        before = old.get("risks", {}).get(event, 0.0)
        if p - before >= ALERT_RISE and p >= ALERT_MIN_PROB:
            changes.append({"event": event, "old": before, "new": p})
    for action in new["recommended"]:
        if action not in old.get("recommended", []):
            changes.append({"action": action})
    return changes


def _pct(p: float) -> str:
    return f"{round(p * 100)}%"


def format_report(field: dict, snap: dict, lang: str) -> str:
    crop_label = t(lang, f"crop_{field['crop']}").replace("🌾 ", "")
    lines = [
        t(lang, "report_title", crop=crop_label, place=field["place"], area=f"{field['area_acres']:g}"),
        t(lang, "report_stage", stage=label(STAGES, snap["stage"], lang), days=snap["days"]),
        "",
        t(lang, "report_risk_header"),
    ]
    for event, p in sorted(snap["risks"].items(), key=lambda kv: -kv[1]):
        flag = " 🔴" if p >= 0.6 else " 🟠" if p >= 0.3 else ""
        lines.append(f"  {label(EVENTS, event, lang)}: {_pct(p)}{flag}")
    lines += ["", t(lang, "report_loss", loss=rupees(snap["loss_per_acre"]))]

    if snap["actions"]:
        lines.append(t(lang, "report_do"))
        for a in snap["actions"]:
            lines.append(f"  • {label(ACTIONS, a['id'], lang)} ({t(lang, 'report_saves', amount=rupees(a['net']))})")
    else:
        lines.append(t(lang, "report_no_action"))

    basis = "MSP" if snap["price_is_msp"] else "mandi"
    lines += ["", t(lang, "report_price", price=rupees(snap["price"]), basis=basis),
              t(lang, "report_source", source=snap["forecast_source"])]
    return "\n".join(lines)


def format_alert(field: dict, snap: dict, changes: list[dict], lang: str) -> str:
    lines = [t(lang, "alert_title")]
    for c in changes:
        if "event" in c:
            lines.append("  " + t(lang, "alert_change", event=label(EVENTS, c["event"], lang),
                                  old=_pct(c["old"]), new=_pct(c["new"])))
    return "\n".join(lines) + "\n\n" + format_report(field, snap, lang)


def field_name(field: dict) -> str:
    return f"#{field['id']} {CROPS[field['crop']]['label']} @ {field['place']}"

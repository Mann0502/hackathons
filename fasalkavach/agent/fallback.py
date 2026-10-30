"""Rule-based path: runs the same tools in a fixed order and fills a template.

Used when no LLM key is configured or the agent fails, so the app never breaks
during a demo. The numbers are identical - only the wording is simpler.
"""
from .tools import FarmSession, ToolError


def run_rule_based(req: dict, session: FarmSession) -> dict:
    trace = []

    def step(name, fn, *args, optional=False, **kwargs):
        try:
            out = fn(*args, **kwargs)
            trace.append({"step": len(trace) + 1, "tool": name, "ok": True})
            return out
        except ToolError as e:
            trace.append({"step": len(trace) + 1, "tool": name, "ok": False, "result": str(e)})
            if optional:
                session.warnings.append(f"{name} skipped: {e}")
                return None
            raise

    step("resolve_location", session.resolve_location,
         place_name=req.get("place_name"), lat=req.get("lat"), lon=req.get("lon"))
    step("get_crop_stage", session.get_crop_stage, req["crop"], req["planted_on"])
    step("get_weather_risk", session.get_weather_risk)
    step("get_soil_moisture", session.get_soil_moisture, optional=True)
    step("get_mandi_price", session.get_mandi_price)
    d = step("evaluate_actions", session.evaluate_actions,
             req["area_acres"], req.get("yield_q_per_acre"))

    recommended = [a for a in d["actions"] if a["recommended"]]
    stage = session.stage["stage"].replace("_", " ")
    if recommended:
        headline = f"{len(recommended)} action(s) recommended for your {session.stage['crop_label'].lower()}"
        body = " ".join(f"{a['label']} (saves about Rs {a['net_benefit_rs_per_acre']}/acre)."
                        for a in recommended)
    else:
        headline = "No protective action needed right now"
        body = "Weather risk is low compared with the cost of acting. Continue normal field work."
    text = (f"Your crop is at the {stage} stage. "
            f"Expected weather loss over the next 7 days if you do nothing: about Rs {d['expected_loss_7d_rs_per_acre']}/acre. "
            + body)

    return {
        "advisory": {"headline": headline, "advisory_text": text, "language": "en",
                     "recommended_action_ids": [a["action_id"] for a in recommended]},
        "trace": trace, "mode": "rule_based",
    }

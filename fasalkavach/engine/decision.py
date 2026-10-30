"""Cost-loss decision engine: is a protective action worth its cost?

Rule:  take the action if  P(event) x loss_avoided  >  cost_of_action
Equivalently: act when P(event) > cost / loss  (the "break-even probability").

All arithmetic happens here, in plain Python - never inside the LLM.
"""
from .crops import ACTIONS, CROPS

# Waterlogging makes heavy rain worse when the topsoil is already saturated.
SATURATED_SOIL_M3M3 = 0.40
SATURATION_MULTIPLIER = 1.25
# Postponing a spray/irrigation is not free (pests keep growing, crop waits).
# Modelled as a share of the input cost -> "postpone only if P(rain) > 35%".
DELAY_COST_FRACTION = 0.35


def _window_prob(risks: dict, event: str, days: int) -> float:
    w = risks.get(event, {}).get("window", {})
    if f"{days}d" in w:
        return w[f"{days}d"]
    # Forecast shorter than the window: fall back to the longest window we have
    return max(w.values()) if w else 0.0


def assess(crop: str, stage: dict, risks: dict, farm: dict, costs: dict, soil: dict | None = None) -> dict:
    """Compute expected losses per event and evaluate every applicable action.

    farm = {"area_acres", "yield_q_per_acre", "price_rs_per_q"}
    """
    value_per_acre = farm["yield_q_per_acre"] * farm["price_rs_per_q"]
    area = farm["area_acres"]

    sensitivity = dict(stage["sensitivity"])
    soil_note = None
    if soil and soil.get("topsoil_moisture_m3m3") is not None and "heavy_rain" in sensitivity:
        if soil["topsoil_moisture_m3m3"] >= SATURATED_SOIL_M3M3:
            sensitivity["heavy_rain"] = round(sensitivity["heavy_rain"] * SATURATION_MULTIPLIER, 3)
            soil_note = (f"Topsoil already wet ({soil['topsoil_moisture_m3m3']} m3/m3), "
                         f"heavy-rain damage raised x{SATURATION_MULTIPLIER}")

    # Expected loss over the next 7 days if the farmer does nothing
    event_losses = []
    for event, sens in sensitivity.items():
        if event not in risks:
            continue
        p = _window_prob(risks, event, 7)
        event_losses.append({
            "event": event,
            "label": risks[event]["label"],
            "probability_7d": p,
            "damage_fraction": sens,
            "expected_loss_rs_per_acre": round(p * sens * value_per_acre),
        })
    event_losses.sort(key=lambda e: -e["expected_loss_rs_per_acre"])

    actions = []
    for action_id, a in ACTIONS.items():
        if crop not in a["crops"]:
            continue
        if a["stages"] and stage["stage"] not in a["stages"]:
            continue
        if not all(e in risks for e in a["events"]):
            continue

        if a["kind"] == "save_input":
            p = _window_prob(risks, a["events"][0], a["window_days"])
            input_cost = costs[a["input_cost_key"]]
            benefit = p * input_cost
            cost = DELAY_COST_FRACTION * input_cost
            explain = (f"P(rain in {a['window_days']} days) = {p:.0%}; input worth Rs {input_cost:.0f}/acre "
                       f"would be wasted; delaying costs ~Rs {cost:.0f}/acre")
        else:
            benefit = 0.0
            parts = []
            for e in a["events"]:
                sens = sensitivity.get(e, 0.0)
                p = _window_prob(risks, e, a["window_days"])
                benefit += a["effectiveness"] * p * sens * value_per_acre
                parts.append(f"P({e}, {a['window_days']}d) = {p:.0%} x damage {sens:.0%}")
            cost = costs[a["cost_key"]]
            explain = (f"{'; '.join(parts)}; crop value Rs {value_per_acre:.0f}/acre; "
                       f"action avoids {a['effectiveness']:.0%} of loss; costs Rs {cost:.0f}/acre")
            if benefit == 0:
                continue  # stage not sensitive to these events

        net = benefit - cost
        actions.append({
            "action_id": action_id,
            "label": a["label"],
            "recommended": net > 0,
            "benefit_rs_per_acre": round(benefit),
            "cost_rs_per_acre": round(cost),
            "net_benefit_rs_per_acre": round(net),
            "net_benefit_total_rs": round(net * area),
            "explanation": explain,
        })
    actions.sort(key=lambda x: -x["net_benefit_rs_per_acre"])

    total_expected_loss = sum(e["expected_loss_rs_per_acre"] for e in event_losses)
    return {
        "crop_value_rs_per_acre": round(value_per_acre),
        "area_acres": area,
        "expected_loss_7d_rs_per_acre": round(total_expected_loss),
        "expected_loss_7d_total_rs": round(total_expected_loss * area),
        "event_losses": event_losses,
        "actions": actions,
        "recommended_actions": [a["action_id"] for a in actions if a["recommended"]],
        "soil_note": soil_note,
    }


def default_farm(crop: str, area_acres: float, yield_q: float | None, price: float) -> dict:
    return {
        "area_acres": area_acres,
        "yield_q_per_acre": yield_q or CROPS[crop]["default_yield_q_per_acre"],
        "price_rs_per_q": price,
    }

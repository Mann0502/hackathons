"""FasalKavach - Flask entry point.

POST /api/advise  -> runs the AI agent (or the rule-based fallback) and returns
                     risks, actions, the advisory text, sources and the agent trace.
"""
import logging
from datetime import date

from flask import Flask, jsonify, render_template, request

import config
from agent.fallback import run_rule_based
from agent.loop import AgentUnavailable, run_agent
from agent.tools import FarmSession, ToolError
from engine.crops import CROPS, DEFAULT_COSTS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("fasalkavach")


class BadInput(ValueError):
    pass


def parse_request(body: dict) -> dict:
    """Validate and normalise user input. Raises BadInput with a friendly message."""
    if not isinstance(body, dict):
        raise BadInput("Request body must be JSON")

    req = {}
    crop = str(body.get("crop", "")).lower()
    if crop not in CROPS:
        raise BadInput(f"Choose a crop: {', '.join(CROPS)}")
    req["crop"] = crop

    try:
        planted = date.fromisoformat(str(body.get("planted_on", "")))
    except ValueError:
        raise BadInput(f"Enter a valid {CROPS[crop]['date_label']}")
    req["planted_on"] = planted.isoformat()

    lat, lon = body.get("lat"), body.get("lon")
    place = (body.get("place_name") or "").strip()[:100]
    if lat not in (None, "") and lon not in (None, ""):
        try:
            req["lat"], req["lon"] = round(float(lat), 4), round(float(lon), 4)
        except (TypeError, ValueError):
            raise BadInput("Latitude/longitude must be numbers")
    elif not place:
        raise BadInput("Pick your field on the map or type a village/town name")
    req["place_name"] = place or None

    try:
        req["area_acres"] = float(body.get("area_acres") or 0)
    except (TypeError, ValueError):
        raise BadInput("Area must be a number")
    if not 0 < req["area_acres"] <= 1000:
        raise BadInput("Area must be between 0 and 1000 acres")

    y = body.get("yield_q_per_acre")
    if y not in (None, ""):
        try:
            y = float(y)
        except (TypeError, ValueError):
            raise BadInput("Yield must be a number")
        if not 1 <= y <= 60:
            raise BadInput("Yield should be between 1 and 60 quintal/acre")
    req["yield_q_per_acre"] = y or None

    req["language"] = body.get("language") if body.get("language") in ("en", "hi", "pa") else "en"
    req["question"] = (body.get("question") or "").strip()[:500] or None

    costs = {}
    for key in DEFAULT_COSTS:
        v = (body.get("costs") or {}).get(key)
        if v not in (None, ""):
            try:
                costs[key] = max(0.0, float(v))
            except (TypeError, ValueError):
                raise BadInput(f"Cost '{key}' must be a number")
    req["costs"] = costs
    return req


@app.get("/")
def index():
    return render_template("index.html", crops=CROPS, costs=DEFAULT_COSTS,
                           bounds=config.PUNJAB_BOUNDS)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "llm_configured": bool(config.ANTHROPIC_API_KEY),
                    "mandi_configured": bool(config.DATA_GOV_API_KEY)})


@app.post("/api/advise")
def advise():
    try:
        req = parse_request(request.get_json(silent=True))
    except BadInput as e:
        return jsonify({"error": str(e)}), 400

    result, session, agent_error = None, None, None
    if config.ANTHROPIC_API_KEY:
        session = FarmSession(costs=req["costs"])
        try:
            result = run_agent(req, session)
        except AgentUnavailable as e:
            agent_error = str(e)
            log.warning("Agent failed, using rule-based path: %s", e)

    if result is None:
        session = FarmSession(costs=req["costs"])
        try:
            result = run_rule_based(req, session)
        except ToolError as e:
            return jsonify({"error": str(e)}), 422
        if agent_error:
            session.warnings.insert(0, f"AI agent unavailable ({agent_error}) - showing rule-based advice")
        elif not config.ANTHROPIC_API_KEY:
            session.warnings.insert(0, "AI agent not configured - showing rule-based advice")

    facts = session.facts()
    return jsonify({
        **result,
        "request": req,
        "location": facts["location"],
        "stage": facts["stage"],
        "forecast": facts["forecast"],
        "risks": facts["risks"],
        "soil": facts["soil"],
        "price": facts["price"],
        "decision": facts["decision"],
        "sources": session.sources,
        "warnings": list(dict.fromkeys(session.warnings)),  # de-duplicate, keep order
    })


@app.errorhandler(Exception)
def unexpected(e):
    log.exception("Unhandled error")
    code = getattr(e, "code", 500)
    return jsonify({"error": "Something went wrong on our side. Please try again."}), code if isinstance(code, int) else 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)

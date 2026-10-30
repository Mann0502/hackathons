"""Tests for the validator guardrail, the tool session, and the Flask API.

External HTTP calls are replaced with stubs here so the tests run offline.
The real app always calls the live APIs.
"""
from datetime import date

import pytest

import app as app_module
import config
from agent import tools as tools_module
from agent.tools import FarmSession, ToolError
from agent.validator import extract_numbers, validate_advisory
from tests.test_engine import TODAY, make_ensemble


@pytest.fixture
def stub_apis(monkeypatch):
    rain = [[30, 30, 0, 0, 0, 0, 0, 0, 0, 0]] * 3 + [[0] * 10]
    ens = make_ensemble(10, rain)
    monkeypatch.setattr(tools_module, "get_ensemble_forecast", lambda lat, lon: {
        **ens, "model": "test", "is_ensemble": True, "source": "stub",
        "fetched_at": "2026-03-10T00:00:00+00:00", "cached": False, "stale": False})
    monkeypatch.setattr(tools_module, "get_soil_moisture", lambda lat, lon: {
        "topsoil_moisture_m3m3": 0.3, "source": "stub", "fetched_at": None, "stale": False})
    monkeypatch.setattr(tools_module, "reverse_geocode", lambda lat, lon: {
        "district": "Ludhiana", "source": "stub", "fetched_at": None, "stale": False})
    monkeypatch.setattr(tools_module, "get_mandi_price", lambda crop, district: {
        "price_rs_per_q": 2400, "basis": "stub", "source": "stub", "is_fallback": False, "warnings": []})


def ready_session():
    s = FarmSession(today=TODAY)
    s.resolve_location(lat=30.9, lon=75.85)
    s.get_crop_stage("wheat", "2025-10-20")
    s.get_weather_risk()
    s.get_mandi_price()
    s.evaluate_actions(5, 20)
    return s


# ---------- tools ----------

def test_tool_order_errors_guide_the_agent(stub_apis):
    s = FarmSession(today=TODAY)
    with pytest.raises(ToolError, match="resolve_location"):
        s.get_weather_risk()
    with pytest.raises(ToolError, match="get_crop_stage"):
        s.evaluate_actions(5)


def test_outside_punjab_rejected(stub_apis):
    with pytest.raises(ToolError, match="outside Punjab"):
        FarmSession(today=TODAY).resolve_location(lat=19.07, lon=72.87)  # Mumbai


def test_full_session(stub_apis):
    s = ready_session()
    assert s.location["district"] == "Ludhiana"
    assert "early_harvest" in s.decision["recommended_actions"]
    assert len(s.sources) >= 3


# ---------- validator ----------

def test_extract_numbers_handles_indian_digits():
    assert extract_numbers("₹4,860 और ७५%") == [4860.0, 75.0]


def test_validator_accepts_grounded_advisory(stub_apis):
    s = ready_session()
    adv = {"headline": "Harvest early", "language": "en",
           "advisory_text": "75% chance of heavy rain. Harvesting early saves about Rs 4,860 per acre.",
           "recommended_action_ids": s.decision["recommended_actions"]}
    assert validate_advisory(adv, s.facts()) == []


def test_validator_rejects_invented_numbers_and_actions(stub_apis):
    s = ready_session()
    adv = {"headline": "x", "language": "en",
           "advisory_text": "There is a 92% chance of hail causing Rs 15,000 loss.",
           "recommended_action_ids": ["light_irrigation_frost", "made_up_action"]}
    problems = " ".join(validate_advisory(adv, s.facts()))
    assert "92" in problems and "15000" in problems
    assert "made_up_action" in problems
    assert "early_harvest" in problems  # approved but missing


# ---------- Flask API ----------

@pytest.fixture
def client(monkeypatch, stub_apis):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")   # force rule-based path
    monkeypatch.setattr(tools_module, "date", type("D", (date,), {"today": staticmethod(lambda: TODAY)}))
    return app_module.app.test_client()


def test_api_rejects_bad_input(client):
    r = client.post("/api/advise", json={"crop": "maize"})
    assert r.status_code == 400
    r = client.post("/api/advise", json={"crop": "wheat", "planted_on": "2025-10-20", "area_acres": 5})
    assert r.status_code == 400 and "map" in r.get_json()["error"]
    r = client.post("/api/advise", data="not json")
    assert r.status_code == 400


def test_api_rule_based_end_to_end(client):
    r = client.post("/api/advise", json={"crop": "wheat", "planted_on": "2025-10-20", "area_acres": 5,
                                         "lat": 30.9, "lon": 75.85})
    data = r.get_json()
    assert r.status_code == 200, data
    assert data["mode"] == "rule_based"
    assert "early_harvest" in data["advisory"]["recommended_action_ids"]
    assert any("not configured" in w for w in data["warnings"])


def test_api_outside_punjab_is_friendly_error(client):
    r = client.post("/api/advise", json={"crop": "wheat", "planted_on": "2025-10-20", "area_acres": 5,
                                         "lat": 19.07, "lon": 72.87})
    assert r.status_code == 422 and "Punjab" in r.get_json()["error"]


# ---------- agent loop (scripted fake LLM) ----------

from types import SimpleNamespace as NS

from agent import loop as loop_module


def tool_use(id_, name, inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


class FakeClient:
    """Plays back a fixed list of LLM turns, recording what it was sent."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.sent = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        self.sent.append(kwargs)
        content = self.turns.pop(0)
        if callable(content):  # turns that depend on earlier tool results
            content = content()
        return NS(content=content, stop_reason="tool_use" if any(b.type == "tool_use" for b in content) else "end_turn")


def test_agent_recovers_from_errors_and_failed_validation(stub_apis, monkeypatch):
    good = {"headline": "Harvest early", "language": "en",
            "advisory_text": "75% chance of heavy rain. Harvest early.",
            "recommended_action_ids": []}
    turns = [
        # 1. calls weather before location -> tool error, agent must recover
        [tool_use("t1", "get_weather_risk", {})],
        [tool_use("t2", "resolve_location", {"lat": 30.9, "lon": 75.85}),
         tool_use("t3", "get_crop_stage", {"crop": "wheat", "planted_on": "2025-10-20"})],
        [tool_use("t4", "get_weather_risk", {}), tool_use("t5", "get_mandi_price", {})],
        [tool_use("t6", "evaluate_actions", {"area_acres": 5, "yield_q_per_acre": 20})],
        # 5. invents a number -> rejected by validator
        lambda: [tool_use("t7", "submit_advisory", {**good, "advisory_text": "93% chance of rain."})],
        lambda: [tool_use("t8", "submit_advisory", good)],
    ]
    fake = FakeClient(turns)
    monkeypatch.setattr(loop_module.anthropic, "Anthropic", lambda: fake)

    session = FarmSession(today=TODAY)
    # The scripted "LLM" copies whatever the decision engine approved
    orig = session.evaluate_actions

    def evaluate_and_capture(*a, **k):
        d = orig(*a, **k)
        good["recommended_action_ids"] = list(d["recommended_actions"])
        return d
    session.evaluate_actions = evaluate_and_capture
    req = {"crop": "wheat", "planted_on": "2025-10-20", "area_acres": 5, "lat": 30.9, "lon": 75.85}
    out = loop_module.run_agent(req, session)

    assert out["mode"] == "agent"
    assert out["trace"][0]["ok"] is False                  # first call failed...
    assert any(t["tool"] == "submit_advisory" and not t["ok"] for t in out["trace"])  # ...validation rejected once
    assert out["advisory"] == good
    # Parallel tool results go back in a single user message
    history = fake.sent[-1]["messages"]
    assert any(m["role"] == "user" and isinstance(m["content"], list) and len(m["content"]) == 2
               and all(r["type"] == "tool_result" for r in m["content"]) for m in history)

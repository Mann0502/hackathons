"""Tests for the chat bot: registration conversation, alerts, Telegram formatting.

The field check (`assess`) and geocoding are stubbed so these run offline.
"""
from datetime import date, timedelta

import pytest

import app as app_module
import config
from agent import tools as tools_module
from bot import telegram
from bot.core import Bot, Incoming, parse_crop, parse_date, parse_number
from bot.i18n import rupees
from bot.monitor import find_changes, format_report
from bot.store import Store

RIPE_RICE_DATE = (date.today() - timedelta(days=125)).strftime("%d-%m-%Y")


def snapshot(heavy_rain=0.1, recommended=()):
    return {"checked_at": "now", "stage": "maturity_harvest", "days": 125,
            "risks": {"rain": 0.2, "heavy_rain": heavy_rain, "strong_wind": 0.0},
            "recommended": list(recommended),
            "actions": [{"id": a, "net": 4500} for a in recommended],
            "loss_per_acre": 1234, "price": 2369, "price_is_msp": True,
            "forecast_source": "Open-Meteo Ensemble API (ecmwf_ifs025, 51 members)", "is_ensemble": True}


class Harness:
    """A bot wired to a temp database, a fake 'assess', and a list collecting sent messages."""

    def __init__(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tools_module, "geocode", lambda q: {
            "name": q.title(), "district": "Ludhiana", "lat": 30.9, "lon": 75.85,
            "source": "stub", "fetched_at": None, "stale": False})
        self.sent = []
        self.next_snapshot = snapshot()
        self.bot = Bot(Store(str(tmp_path / "test.db")),
                       send=lambda ch, cid, out: self.sent.append(out),
                       assess=lambda field: self.next_snapshot)

    def say(self, text=None, location=None, chat="42"):
        self.sent.clear()
        self.bot.handle(Incoming("telegram", chat, text=text, location=location))
        return self.sent

    def register(self, lang_button="हिन्दी"):
        self.say("/start")
        self.say(lang_button)
        self.say("ludhiana")
        self.say("धान")
        self.say(RIPE_RICE_DATE)
        return self.say("5 एकड़")


@pytest.fixture
def h(tmp_path, monkeypatch):
    return Harness(tmp_path, monkeypatch)


# ---------- parsing helpers ----------

def test_parsers():
    assert parse_date("25-06-2026") == "2026-06-25"
    assert parse_date("२५/०६/२०२६") == "2026-06-25"     # Hindi digits
    assert parse_number("5.5 एकड़") == 5.5
    assert parse_crop("ਝੋਨਾ") == "rice" and parse_crop("Wheat") == "wheat" and parse_crop("maize") is None
    assert rupees(1234567) == "₹12,34,567" and rupees(950) == "₹950"


# ---------- conversation ----------

def test_full_registration_in_hindi(h):
    out = h.register()
    assert "खेत सेव हो गया" in out[0].text
    report = out[1].text
    assert "धान" in report and "कटाई के लिए तैयार" in report and "₹1,234" in report
    fields = h.bot.store.fields_for("telegram", "42")
    assert len(fields) == 1 and fields[0]["crop"] == "rice" and fields[0]["area_acres"] == 5
    assert fields[0]["last_snapshot"]["risks"]["heavy_rain"] == 0.1


def test_bad_answers_are_asked_again(h):
    h.say("/start")
    assert "language" in h.say("klingon")[0].text.lower()
    h.say("English")
    h.say("ludhiana")
    assert "Which crop" in h.say("maize")[0].text
    h.say("rice")
    assert "❌" in h.say("yesterday")[0].text
    future = (date.today() + timedelta(days=10)).strftime("%d-%m-%Y")
    assert "future" in h.say(future)[0].text
    h.say(RIPE_RICE_DATE)
    assert "❌" in h.say("lots")[0].text
    assert "Field saved" in h.say("5")[0].text


def test_location_outside_punjab_rejected(h):
    h.say("/start")
    h.say("English")
    out = h.say(location=(19.07, 72.87))   # Mumbai
    assert "outside Punjab" in out[0].text


def test_commands(h):
    h.register("English")
    assert "#1" in h.say("/fields")[0].text
    assert "paused" in h.say("/stop")[0].text
    assert h.bot.store.users_with_alerts() == []
    h.say("/resume")
    out = h.say("/status")
    assert "Checking" in out[0].text and "Rice" in out[1].text


def test_question_without_agent_falls_back_to_report(h, monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")
    h.register("English")
    out = h.say("Should I harvest tomorrow?")
    assert "not available" in out[0].text and "Next 7 days" in out[1].text


# ---------- monitoring & alerts ----------

def test_alert_only_when_risk_rises(h):
    h.register("English")
    # Same weather -> no alert
    h.sent.clear()
    assert h.bot.run_monitor()["alerts"] == 0 and h.sent == []
    # Heavy rain jumps from 10% to 75% and early harvest becomes worth it -> alert
    h.next_snapshot = snapshot(heavy_rain=0.75, recommended=["early_harvest"])
    stats = h.bot.run_monitor()
    assert stats["alerts"] == 1
    assert "ALERT" in h.sent[0].text and "10% → 75%" in h.sent[0].text and "Harvest early" in h.sent[0].text
    # Unchanged on the next run -> quiet again
    h.sent.clear()
    assert h.bot.run_monitor()["alerts"] == 0


def test_paused_users_get_no_alerts(h):
    h.register("English")
    h.say("/stop")
    h.next_snapshot = snapshot(heavy_rain=0.9)
    h.sent.clear()
    assert h.bot.run_monitor()["checked"] == 0 and h.sent == []


def test_find_changes_thresholds():
    old = snapshot(heavy_rain=0.3)
    assert find_changes(old, snapshot(heavy_rain=0.5)) == []             # rose only 20 points
    assert find_changes(old, snapshot(heavy_rain=0.6))[0]["new"] == 0.6  # rose 30 points, above 40%
    assert find_changes(None, snapshot(heavy_rain=0.9)) == []            # first check never alerts


def test_report_in_punjabi():
    field = {"id": 1, "crop": "wheat", "place": "Bathinda", "area_acres": 3}
    text = format_report(field, snapshot(recommended=["postpone_spray"]), "pa")
    assert "ਕਣਕ" in text and "ਸਪਰੇ" in text


# ---------- Telegram adapter ----------

def test_telegram_parse_and_payload():
    msg = telegram.parse_update({"update_id": 1, "message": {"chat": {"id": 99}, "location": {"latitude": 30.9, "longitude": 75.8}}})
    assert msg.chat_id == "99" and msg.location == (30.9, 75.8)
    assert telegram.parse_update({"update_id": 2, "my_chat_member": {}}) is None

    from bot.core import Outgoing
    p = telegram.build_payload("99", Outgoing("hi", request_location="📍 Share"))
    assert p["reply_markup"]["keyboard"][0][0]["request_location"] is True
    p = telegram.build_payload("99", Outgoing("x" * 5000, buttons=[["A", "B"]]))
    assert len(p["text"]) == 4096 and p["reply_markup"]["keyboard"][0][1]["text"] == "B"


def test_webhook_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_WEBHOOK_SECRET", "s3cret")
    client = app_module.app.test_client()
    assert client.post("/telegram/webhook", json={}).status_code == 403
    assert client.post("/telegram/webhook", json={},
                       headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 403

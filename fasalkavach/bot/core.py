"""Channel-independent bot logic: registration chat, commands, questions, monitoring.

Adapters (Telegram now, WhatsApp later) turn platform messages into `Incoming`,
call `Bot.handle()`, and deliver the `Outgoing` messages the bot sends back.

Registration is a small state machine stored per user:
    choose_lang -> ask_location -> ask_crop -> ask_date -> ask_area -> ready
"""
import logging
import re
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime
from typing import Callable

from agent.tools import FarmSession, ToolError
from config import ANTHROPIC_API_KEY, CHECK_INTERVAL_HOURS
from engine.stage import StageError, get_crop_stage

from .i18n import LANGS, t
from .monitor import assess_field, field_name, find_changes, format_alert, format_report
from .store import Store

log = logging.getLogger("fasalkavach.bot")

_DIGITS = str.maketrans("०१२३४५६७८९੦੧੨੩੪੫੬੭੮੯", "01234567890123456789")
CROP_WORDS = {
    "wheat": ["wheat", "gehu", "gehun", "kanak", "गेहूँ", "गेहूं", "ਕਣਕ"],
    "rice": ["rice", "paddy", "dhan", "jhona", "धान", "चावल", "ਝੋਨਾ", "ਚੌਲ"],
}


@dataclass
class Incoming:
    channel: str
    chat_id: str
    text: str | None = None
    location: tuple[float, float] | None = None


@dataclass
class Outgoing:
    text: str
    buttons: list[list[str]] | None = None      # rows of tap-able reply buttons
    request_location: str | None = None         # label for a "share location" button
    remove_keyboard: bool = dc_field(default=False)


def parse_date(text: str) -> str:
    text = text.translate(_DIGITS).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"'{text}' is not a date I understand")


def parse_number(text: str) -> float | None:
    m = re.search(r"\d+(?:\.\d+)?", text.translate(_DIGITS))
    return float(m.group()) if m else None


def parse_crop(text: str) -> str | None:
    low = text.lower()
    for crop, words in CROP_WORDS.items():
        if any(w in low for w in words):
            return crop
    return None


class Bot:
    def __init__(self, store: Store, send: Callable[[str, str, Outgoing], None],
                 assess: Callable[[dict], dict] = assess_field, agent=None):
        self.store = store
        self.send = send            # send(channel, chat_id, Outgoing)
        self.assess = assess
        self.agent = agent          # optional: callable(req, session) -> agent result

    # ---- entry point ------------------------------------------------------------

    def handle(self, msg: Incoming):
        user = self.store.get_user(msg.channel, msg.chat_id)
        lang = user["language"]
        reply = lambda out: self.send(msg.channel, msg.chat_id, out)  # noqa: E731
        text = (msg.text or "").strip()
        command = text.split()[0].lower().split("@")[0] if text.startswith("/") else None

        if command == "/start" or user["state"] == "new":
            return self._ask_language(msg, reply, next_state="ask_location")
        if command == "/language":
            return self._ask_language(msg, reply, next_state="ready")
        if command == "/add":
            self.store.update_user(msg.channel, msg.chat_id, state="ask_location", draft={})
            return self._ask_location(lang, reply)
        if command == "/help":
            return reply(Outgoing(t(lang, "help")))
        if command == "/stop":
            self.store.update_user(msg.channel, msg.chat_id, alerts_on=0)
            return reply(Outgoing(t(lang, "stopped")))
        if command == "/resume":
            self.store.update_user(msg.channel, msg.chat_id, alerts_on=1)
            return reply(Outgoing(t(lang, "resumed")))
        if command == "/fields":
            return self._list_fields(msg, lang, reply)
        if command == "/status":
            return self.check_user_fields(msg.channel, msg.chat_id, lang)

        step = getattr(self, f"_on_{user['state']}", None)
        if step is None:
            return reply(Outgoing(t(lang, "help")))
        return step(msg, user, lang, reply)

    # ---- registration steps -------------------------------------------------------

    def _ask_language(self, msg, reply, next_state):
        self.store.update_user(msg.channel, msg.chat_id, state="choose_lang",
                               draft={"after_lang": next_state})
        reply(Outgoing(t("en", "welcome") if next_state != "ready" else "Choose your language:",
                       buttons=[list(LANGS.values())]))

    def _on_choose_lang(self, msg, user, lang, reply):
        chosen = next((code for code, name in LANGS.items()
                       if (msg.text or "").strip().lower() in (name.lower(), code)), None)
        if not chosen:
            return reply(Outgoing("Please tap a language:", buttons=[list(LANGS.values())]))
        next_state = user["draft"].get("after_lang", "ask_location")
        self.store.update_user(msg.channel, msg.chat_id, language=chosen, state=next_state, draft={})
        if next_state == "ask_location":
            return self._ask_location(chosen, reply)
        reply(Outgoing("✅ " + LANGS[chosen], remove_keyboard=True))

    def _ask_location(self, lang, reply):
        reply(Outgoing(t(lang, "ask_location"), request_location=t(lang, "share_location_button")))

    def _on_ask_location(self, msg, user, lang, reply):
        session = FarmSession()
        try:
            if msg.location:
                loc = session.resolve_location(lat=msg.location[0], lon=msg.location[1])
                loc["name"] = loc.get("district") or loc["name"]
            elif msg.text:
                loc = session.resolve_location(place_name=msg.text)
            else:
                return self._ask_location(lang, reply)
        except ToolError as e:
            return reply(Outgoing(t(lang, "location_error", error=e),
                                  request_location=t(lang, "share_location_button")))
        draft = {"place": loc["name"], "district": loc.get("district"), "lat": loc["lat"], "lon": loc["lon"]}
        self.store.update_user(msg.channel, msg.chat_id, state="ask_crop", draft=draft)
        reply(Outgoing(t(lang, "ask_crop", place=loc["name"]),
                       buttons=[[t(lang, "crop_wheat"), t(lang, "crop_rice")]]))

    def _on_ask_crop(self, msg, user, lang, reply):
        crop = parse_crop(msg.text or "")
        if not crop:
            return reply(Outgoing(t(lang, "ask_crop", place=user["draft"]["place"]),
                                  buttons=[[t(lang, "crop_wheat"), t(lang, "crop_rice")]]))
        self.store.update_user(msg.channel, msg.chat_id, state="ask_date", draft={**user["draft"], "crop": crop})
        reply(Outgoing(t(lang, f"ask_date_{crop}"), remove_keyboard=True))

    def _on_ask_date(self, msg, user, lang, reply):
        crop = user["draft"]["crop"]
        try:
            planted = parse_date(msg.text or "")
            get_crop_stage(crop, planted, date.today())   # rejects future / season-over dates
        except (ValueError, StageError) as e:
            return reply(Outgoing(t(lang, "date_error", error=e)))
        self.store.update_user(msg.channel, msg.chat_id, state="ask_area",
                               draft={**user["draft"], "planted_on": planted})
        reply(Outgoing(t(lang, "ask_area")))

    def _on_ask_area(self, msg, user, lang, reply):
        area = parse_number(msg.text or "")
        if area is None or not 0.1 <= area <= 1000:
            return reply(Outgoing(t(lang, "area_error")))
        new_field = {**user["draft"], "area_acres": area}
        field_id = self.store.add_field(msg.channel, msg.chat_id, new_field)
        self.store.update_user(msg.channel, msg.chat_id, state="ready", draft={})
        reply(Outgoing(t(lang, "registered", hours=f"{CHECK_INTERVAL_HOURS:g}")))
        field = next(f for f in self.store.fields_for(msg.channel, msg.chat_id) if f["id"] == field_id)
        self._check_and_report(field, lang, reply)

    def _on_ready(self, msg, user, lang, reply):
        """Free text after registration = a question for the AI agent."""
        if not msg.text:
            return reply(Outgoing(t(lang, "help")))
        fields = self.store.fields_for(msg.channel, msg.chat_id)
        if not fields:
            return reply(Outgoing(t(lang, "ask_needs_field")))
        field = fields[-1]   # most recently added field
        if self.agent is None or not ANTHROPIC_API_KEY:
            reply(Outgoing(t(lang, "agent_offline")))
            return self._check_and_report(field, lang, reply)

        reply(Outgoing(t(lang, "checking")))
        req = {"place_name": field["place"], "lat": field["lat"], "lon": field["lon"],
               "crop": field["crop"], "planted_on": field["planted_on"],
               "area_acres": field["area_acres"], "yield_q_per_acre": None,
               "language": lang, "question": msg.text}
        try:
            out = self.agent(req, FarmSession())
        except Exception as e:  # agent failures must never break the chat
            log.warning("Agent failed for chat %s: %s", msg.chat_id, e)
            reply(Outgoing(t(lang, "agent_offline")))
            return self._check_and_report(field, lang, reply)
        adv = out["advisory"]
        parts = [f"🤖 {adv['headline']}", adv.get("answer_to_question") or "", adv["advisory_text"]]
        reply(Outgoing("\n\n".join(p for p in parts if p)))

    # ---- checks & monitoring ------------------------------------------------------

    def _list_fields(self, msg, lang, reply):
        fields = self.store.fields_for(msg.channel, msg.chat_id)
        if not fields:
            return reply(Outgoing(t(lang, "no_fields")))
        lines = [t(lang, "fields_header")] + [
            f"{field_name(f)} · {f['area_acres']:g} ac · {f['planted_on']}" for f in fields]
        reply(Outgoing("\n".join(lines)))

    def _check_and_report(self, field: dict, lang: str, reply) -> dict | None:
        try:
            snap = self.assess(field)
        except ToolError as e:
            reply(Outgoing(t(lang, "check_failed", name=field_name(field), error=e)))
            return None
        self.store.save_snapshot(field["id"], snap)
        reply(Outgoing(format_report(field, snap, lang)))
        return snap

    def check_user_fields(self, channel: str, chat_id: str, lang: str | None = None):
        """/status: check every field of one user right now and send full reports."""
        lang = lang or self.store.get_user(channel, chat_id)["language"]
        reply = lambda out: self.send(channel, chat_id, out)  # noqa: E731
        fields = self.store.fields_for(channel, chat_id)
        if not fields:
            return reply(Outgoing(t(lang, "no_fields")))
        reply(Outgoing(t(lang, "checking")))
        for f in fields:
            self._check_and_report(f, lang, reply)

    def run_monitor(self) -> dict:
        """Scheduled job: re-check every field; message the farmer only if risk got worse."""
        users = {(u["channel"], u["chat_id"]): u for u in self.store.users_with_alerts()}
        stats = {"checked": 0, "alerts": 0, "failed": 0}
        for f in self.store.all_fields():
            user = users.get((f["channel"], f["chat_id"]))
            if not user:
                continue  # alerts paused
            try:
                snap = self.assess(f)
            except ToolError as e:
                log.info("Skipping field %s: %s", f["id"], e)
                stats["failed"] += 1
                continue
            stats["checked"] += 1
            changes = find_changes(f["last_snapshot"], snap)
            self.store.save_snapshot(f["id"], snap)
            if changes:
                stats["alerts"] += 1
                self.send(f["channel"], f["chat_id"], Outgoing(format_alert(f, snap, changes, user["language"])))
        log.info("Monitor run: %s", stats)
        return stats

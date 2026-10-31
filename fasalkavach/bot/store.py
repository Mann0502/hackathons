"""SQLite storage for bot users, their registration progress, and their fields.

A user is identified by (channel, chat_id), so the same database serves
Telegram now and WhatsApp later.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone

from config import BOT_DB_PATH

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    channel     TEXT NOT NULL,
    chat_id     TEXT NOT NULL,
    language    TEXT NOT NULL DEFAULT 'en',
    state       TEXT NOT NULL DEFAULT 'new',   -- where the user is in the registration chat
    draft       TEXT NOT NULL DEFAULT '{}',    -- answers collected so far (JSON)
    alerts_on   INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (channel, chat_id)
);
CREATE TABLE IF NOT EXISTS fields (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    channel      TEXT NOT NULL,
    chat_id      TEXT NOT NULL,
    place        TEXT NOT NULL,
    district     TEXT,
    lat          REAL NOT NULL,
    lon          REAL NOT NULL,
    crop         TEXT NOT NULL,
    planted_on   TEXT NOT NULL,
    area_acres   REAL NOT NULL,
    last_snapshot TEXT,          -- risk summary from the last check (JSON), used to detect changes
    last_checked TEXT,
    created_at   TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str = BOT_DB_PATH):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with _lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def _exec(self, sql: str, params: tuple = ()):
        with _lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    # ---- users -----------------------------------------------------------------

    def get_user(self, channel: str, chat_id: str) -> dict:
        row = self._exec("SELECT * FROM users WHERE channel=? AND chat_id=?", (channel, chat_id)).fetchone()
        if row is None:
            self._exec("INSERT INTO users (channel, chat_id, created_at) VALUES (?, ?, ?)",
                       (channel, chat_id, _now()))
            return self.get_user(channel, chat_id)
        user = dict(row)
        user["draft"] = json.loads(user["draft"])
        return user

    def update_user(self, channel: str, chat_id: str, **changes):
        if "draft" in changes:
            changes["draft"] = json.dumps(changes["draft"])
        cols = ", ".join(f"{k}=?" for k in changes)
        self._exec(f"UPDATE users SET {cols} WHERE channel=? AND chat_id=?",
                   (*changes.values(), channel, chat_id))

    def users_with_alerts(self) -> list[dict]:
        return [dict(r) for r in self._exec("SELECT * FROM users WHERE alerts_on=1").fetchall()]

    # ---- fields ----------------------------------------------------------------

    def add_field(self, channel: str, chat_id: str, f: dict) -> int:
        cur = self._exec(
            "INSERT INTO fields (channel, chat_id, place, district, lat, lon, crop, planted_on, area_acres, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (channel, chat_id, f["place"], f.get("district"), f["lat"], f["lon"],
             f["crop"], f["planted_on"], f["area_acres"], _now()))
        return cur.lastrowid

    def fields_for(self, channel: str, chat_id: str) -> list[dict]:
        rows = self._exec("SELECT * FROM fields WHERE channel=? AND chat_id=? ORDER BY id",
                          (channel, chat_id)).fetchall()
        return [self._field(r) for r in rows]

    def all_fields(self) -> list[dict]:
        return [self._field(r) for r in self._exec("SELECT * FROM fields ORDER BY id").fetchall()]

    def save_snapshot(self, field_id: int, snapshot: dict):
        self._exec("UPDATE fields SET last_snapshot=?, last_checked=? WHERE id=?",
                   (json.dumps(snapshot), _now(), field_id))

    @staticmethod
    def _field(row) -> dict:
        f = dict(row)
        f["last_snapshot"] = json.loads(f["last_snapshot"]) if f["last_snapshot"] else None
        return f

"""Shared HTTP helper: retries, an in-memory TTL cache, and stale-cache fallback.

If an API is down during the demo we serve the last good response (marked
`stale`) instead of crashing.
"""
import json
import time
from datetime import datetime, timezone

import requests

from config import CACHE_TTL_S, HTTP_TIMEOUT_S

_cache: dict[str, tuple[float, dict, str]] = {}  # key -> (stored_at, data, fetched_at_iso)


class FetchError(RuntimeError):
    pass


def get_json(url: str, params: dict, ttl: int = CACHE_TTL_S, headers: dict | None = None,
             retries: int = 2) -> tuple[dict, dict]:
    """Return (data, meta). meta = {"cached": bool, "stale": bool, "fetched_at": iso}."""
    key = url + "?" + json.dumps(params, sort_keys=True)
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1], {"cached": True, "stale": False, "fetched_at": hit[2]}

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            _cache[key] = (now, data, fetched_at)
            return data, {"cached": False, "stale": False, "fetched_at": fetched_at}
        except (requests.RequestException, ValueError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.5 * 2 ** attempt)

    if hit:  # API failed, but we have an older answer
        return hit[1], {"cached": True, "stale": True, "fetched_at": hit[2]}
    raise FetchError(f"{url} failed: {last_err}")

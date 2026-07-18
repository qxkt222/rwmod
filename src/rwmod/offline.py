"""Offline mode — graceful degradation when Steam API is unreachable.

When Steam API is down or network is unavailable, rwmod falls back to
locally cached data instead of showing errors. Status is tracked so
the UI can display connectivity state.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request

_log = logging.getLogger(__name__)

# ── connectivity state ─────────────────────────────────────────────

_last_check_time: float = 0
_is_online: bool = True
_check_interval: float = 30  # seconds between connectivity checks


def is_online(force: bool = False) -> bool:
    """Check if Steam API is reachable.

    Caches the result for _check_interval seconds to avoid
    hammering the API on every request.
    """
    global _last_check_time, _is_online

    now = time.monotonic()
    if not force and (now - _last_check_time) < _check_interval:
        return _is_online

    _last_check_time = now
    _is_online = _ping_steam()
    if not _is_online:
        _log.warning("Steam API 不可达——进入离线模式")
    return _is_online


def get_status() -> dict:
    """Return current connectivity status for API reporting."""
    return {
        "online": _is_online,
        "last_check": _last_check_time,
        "last_check_ago_sec": round(time.monotonic() - _last_check_time, 1)
        if _last_check_time
        else 0,
    }


def mark_offline() -> None:
    """Force offline mode (used when an API call fails)."""
    global _is_online, _last_check_time
    _is_online = False
    _last_check_time = time.monotonic()


def mark_online() -> None:
    """Force online mode (used when a retry succeeds)."""
    global _is_online, _last_check_time
    _is_online = True
    _last_check_time = time.monotonic()


# ── graceful fallback helpers ──────────────────────────────────────


def safe_fetch(fetch_fn, *args, **kwargs):
    """Wrap a Steam API fetch function with offline fallback.

    If the API call fails, marks offline and returns empty/default.
    On success, marks online.

    Usage:
        result = safe_fetch(fetch_item_details, mod_ids)
    """
    try:
        result = fetch_fn(*args, **kwargs)
        mark_online()
        return result
    except Exception as e:
        _log.debug("API 调用失败（离线模式）: %s", e)
        mark_offline()
        # Return appropriate empty value based on expected return type
        return _get_default(fetch_fn)


def _get_default(fn) -> dict | list:
    """Return appropriate empty value for known fetch functions."""
    name = getattr(fn, "__name__", "")
    if "dependencies" in name or "details" in name or "batch" in name:
        return {}
    if "search" in name or "children" in name or "collection" in name:
        return []
    return {}


# ── internal ───────────────────────────────────────────────────────


def _ping_steam(timeout: float = 5.0) -> bool:
    """Lightweight ping to Steam API to check connectivity."""
    url = "https://api.steampowered.com/ISteamWebAPIUtil/GetServerInfo/v1/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rwmod/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return "response" in data
    except Exception:
        return False

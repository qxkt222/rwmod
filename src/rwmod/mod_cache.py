"""Mod metadata cache — avoids re-parsing About.xml on every request.

Uses a TTL-based in-memory cache with directory mtime-based invalidation.
When a mod folder is touched (installed/deleted), only that entry is invalidated.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

from rwmod.metadata import ModMeta, read_mod_metadata

__all__ = ["get_cached_mods", "invalidate_cache"]

_MAX_AGE_SECONDS = 30  # TTL: re-scan entire mods dir after this many seconds
_cache: dict[str, ModMeta] = {}
_cache_time: float = 0
_cache_dir_mtime: float = 0
_lock = threading.Lock()


def get_cached_mods(mods_dir: Path) -> list[ModMeta]:
    """Return cached mod metadata with three-layer fallback.

    1. In-memory TTL cache (30s) — instant for rapid re-requests.
    2. SQLite persistent cache — per-mod incremental refresh, survives restarts.
    3. Full filesystem scan — only when cache is cold (first run).
    """
    global _cache, _cache_time, _cache_dir_mtime

    if not mods_dir.exists():
        with _lock:
            _cache.clear()
            _cache_time = 0
            _cache_dir_mtime = 0
        return []

    dir_mtime = _mods_dir_mtime(mods_dir)
    now = time.monotonic()

    # Layer 1: in-memory cache hit
    with _lock:
        if _cache and (now - _cache_time) < _MAX_AGE_SECONDS and dir_mtime == _cache_dir_mtime:
            return list(_cache.values())

    # Layer 2: persistent SQLite cache with per-mod incremental refresh
    # get_or_refresh_metas handles cold start internally — if DB is empty,
    # it does a full scan and writes results back to SQLite.
    try:
        from rwmod.cache_db import get_or_refresh_metas

        metas = get_or_refresh_metas(mods_dir)
    except Exception:
        _log = logging.getLogger(__name__)
        _log.warning("持久化缓存不可用，回退到全量扫描", exc_info=True)
        metas = []

    if metas:
        with _lock:
            _cache = {m.folder: m for m in metas}
            _cache_time = now
            _cache_dir_mtime = dir_mtime
        return metas

    # Layer 3: full filesystem scan (only if DB is broken or cache_db import fails)
    # os.scandir() caches stat info in DirEntry, avoiding extra syscalls per entry
    new_cache: dict[str, ModMeta] = {}
    with os.scandir(mods_dir) as entries:
        for entry in sorted(entries, key=lambda e: e.name):
            if not entry.is_dir():
                continue
            meta = read_mod_metadata(Path(entry.path))
            if meta:
                new_cache[meta.folder] = meta

    metas_full = list(new_cache.values())
    with _lock:
        _cache = new_cache
        _cache_time = now
        _cache_dir_mtime = dir_mtime
    return metas_full


def invalidate_cache(folder: str | None = None) -> None:
    """Invalidate a specific folder entry or the entire cache.

    Args:
        folder: mod folder name to invalidate, or None for full invalidation.
    """
    global _cache, _cache_time
    with _lock:
        if folder is None:
            _cache.clear()
            _cache_time = 0
        elif folder in _cache:
            del _cache[folder]

    # Also invalidate the persistent cache
    try:
        from rwmod.cache_db import invalidate_all, invalidate_folder

        if folder is None:
            invalidate_all()
        else:
            invalidate_folder(folder)
    except Exception:
        pass


def _mods_dir_mtime(mods_dir: Path) -> float:
    """Get the latest mtime of the mods directory or any mod subdirectory.

    Uses directory modification time as a coarse invalidation signal.
    A new mod folder or deletion changes the parent dir's mtime.
    """
    try:
        return mods_dir.stat().st_mtime
    except OSError:
        return 0

"""RimPy Mod Database integration — community-maintained mod rules.

Downloads and caches the RimPy community database for:
1. Known incompatible mod pairs (replaces hardcoded rules in load_order.py)
2. Load-order rules (required before/after relationships)
3. Mod metadata enrichment (categories, tags, notes)

Database source: https://github.com/rimpy-custom/RimPy-ModManager-Database
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from urllib.request import Request, urlopen

__all__ = ["RimPyDB", "DATABASE_URL"]

_log = logging.getLogger(__name__)

DATABASE_URL = (
    "https://raw.githubusercontent.com/rimpy-custom/RimPy-ModManager-Database/"
    "master/rimpy_database.json"
)
_CACHE_TTL = 24 * 3600  # 24 hours


class RimPyDB:
    """Singleton accessor for the RimPy community database."""

    _instance: RimPyDB | None = None

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or (Path.home() / ".rwmod")
        self._cache_path = self._cache_dir / "rimpy_database.json"
        self._data: dict = {}
        self._loaded: bool = False
        self._load_attempted: bool = False

    @classmethod
    def get(cls, cache_dir: Path | None = None) -> RimPyDB:
        if cls._instance is None:
            cls._instance = cls(cache_dir)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    # ── public API ──────────────────────────────────────────────────

    def ensure_loaded(self) -> bool:
        """Load the database from cache or download if needed."""
        if self._loaded:
            return True
        if self._load_attempted:
            return bool(self._data)
        self._load_attempted = True

        if self._load_from_cache():
            self._loaded = True
            return True
        if self._download():
            self._loaded = True
            return True

        _log.warning("RimPy database unavailable — conflict detection limited")
        return False

    def get_conflicts(self, workshop_ids: set[str]) -> list[dict]:
        """Find known conflicts among the given workshop IDs."""
        if not self.ensure_loaded():
            return []
        conflicts: list[dict] = []
        rules = self._data.get("conflicts", []) if isinstance(self._data, dict) else []
        ids_set = set(workshop_ids)
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            a = str(rule.get("a", "") or rule.get("mod_a", "") or rule.get("id1", ""))
            b = str(rule.get("b", "") or rule.get("mod_b", "") or rule.get("id2", ""))
            if a in ids_set and b in ids_set:
                conflicts.append({
                    "mod_a": a, "mod_b": b,
                    "reason": str(rule.get("reason", "") or rule.get("description", "") or "Known conflict"),
                })
        return conflicts

    def get_load_rules(self, workshop_ids: set[str]) -> list[dict]:
        """Get load-order rules (before/after relationships)."""
        if not self.ensure_loaded():
            return []
        rules = self._data.get("load_rules", []) if isinstance(self._data, dict) else []
        ids_set = set(workshop_ids)
        result: list[dict] = []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            mid = str(rule.get("id", "") or rule.get("mod_id", ""))
            if mid in ids_set or any(
                str(x) in ids_set for x in rule.get("before", []) + rule.get("after", [])
            ):
                result.append({
                    "mod_id": mid,
                    "before": [str(x) for x in rule.get("before", [])],
                    "after": [str(x) for x in rule.get("after", [])],
                    "note": str(rule.get("note", "")),
                })
        return result

    def search_by_workshop_id(self, workshop_id: str) -> dict | None:
        """Look up a workshop ID for metadata enrichment."""
        if not self.ensure_loaded():
            return None
        mods = self._data.get("mods", {}) if isinstance(self._data, dict) else {}
        if isinstance(mods, dict):
            return mods.get(str(workshop_id))
        return None

    # ── internal ───────────────────────────────────────────────────

    def _load_from_cache(self) -> bool:
        if not self._cache_path.exists():
            return False
        age = time.time() - self._cache_path.stat().st_mtime
        if age > _CACHE_TTL:
            return False
        try:
            data = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data:
                self._data = data
                _log.info("RimPy DB loaded from cache (%d KB)", self._cache_path.stat().st_size // 1024)
                return True
        except (OSError, json.JSONDecodeError) as e:
            _log.debug("RimPy cache read failed: %s", e)
        return False

    def _download(self) -> bool:
        _log.info("Downloading RimPy database...")
        try:
            req = Request(DATABASE_URL, headers={"User-Agent": "rwmod/1.0"})
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
            data = json.loads(raw)
            if not isinstance(data, dict):
                return False
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=None), encoding="utf-8")
            self._data = data
            _log.info("RimPy DB downloaded (%d KB)", len(raw) // 1024)
            return True
        except Exception as e:
            _log.warning("Failed to download RimPy DB: %s", e)
            return False

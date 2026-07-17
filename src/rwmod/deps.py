"""FastAPI dependency injection — provides config, DB, and queue singletons."""

from __future__ import annotations

from rwmod.autoupdate import AutoUpdateManager
from rwmod.config import Config
from rwmod.database import _get_conn
from rwmod.queue import get_queue as _get_queue

__all__ = ["get_config", "get_db", "get_queue", "get_autoupdate"]

# Module-level singletons (one per app instance)
_autoupdate: AutoUpdateManager | None = None


def get_autoupdate() -> AutoUpdateManager:
    """Return the module-level AutoUpdateManager singleton."""
    global _autoupdate
    if _autoupdate is None:
        _autoupdate = AutoUpdateManager()
    return _autoupdate


def get_config() -> Config:
    """FastAPI dependency: load config from ~/.rwmod.toml."""
    return Config.load()


def get_db():
    """FastAPI dependency: return persistent SQLite connection."""
    return _get_conn()


def get_queue():
    """FastAPI dependency: return the download queue singleton."""
    return _get_queue()

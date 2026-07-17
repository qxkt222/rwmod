"""SQLite persistence layer — download history, mod metadata cache.

Uses a module-level persistent connection to avoid per-query open/close overhead.
Connection is lazily initialized and thread-safe via check_same_thread=False.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

__all__ = [
    "DB_PATH",
    "init_db",
    "record_download",
    "get_download_history",
    "get_download_stats",
    "clear_history",
    "cache_mod",
    "get_cached_mod",
]

DB_PATH = Path.home() / ".rwmod.db"

_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    """Return the module-level persistent connection, creating it lazily."""
    global _conn
    if _conn is not None:
        return _conn
    with _lock:
        if _conn is not None:
            return _conn
        _conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
        _conn.execute("PRAGMA cache_size=-8000")  # 8MB page cache
        _conn.execute("PRAGMA synchronous=NORMAL")  # safe with WAL
        return _conn


def close_db() -> None:
    """Close the persistent connection. Called on shutdown."""
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


def init_db() -> None:
    db = _get_conn()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS download_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            workshop_id TEXT    NOT NULL,
            mod_name    TEXT    DEFAULT '',
            package_id  TEXT    DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'pending',  -- pending|success|failed|skipped
            msg         TEXT    DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mod_cache (
            workshop_id  TEXT PRIMARY KEY,
            title        TEXT    DEFAULT '',
            author       TEXT    DEFAULT '',
            description  TEXT    DEFAULT '',
            time_updated INTEGER DEFAULT 0,
            cached_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS local_mod_metadata (
            folder       TEXT PRIMARY KEY,
            name         TEXT    NOT NULL,
            package_id   TEXT    DEFAULT '',
            workshop_id  TEXT    DEFAULT '',
            dir_mtime    REAL    DEFAULT 0,
            cached_at    REAL    DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_dl_workshop ON download_history(workshop_id);
        CREATE INDEX IF NOT EXISTS idx_dl_created   ON download_history(created_at);
        CREATE INDEX IF NOT EXISTS idx_lmm_workshop ON local_mod_metadata(workshop_id);
    """)
    db.commit()


def record_download(
    workshop_id: str, status: str, mod_name: str = "", package_id: str = "", msg: str = ""
) -> int:
    db = _get_conn()
    cur = db.execute(
        "INSERT INTO download_history (workshop_id, mod_name, package_id, status, msg) VALUES (?,?,?,?,?)",
        (workshop_id, mod_name, package_id, status, msg),
    )
    db.commit()
    return cur.lastrowid or -1


def get_download_history(limit: int = 50, status: str = "") -> list[dict]:
    db = _get_conn()
    query = "SELECT * FROM download_history"
    params: list = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def cache_mod(
    workshop_id: str,
    title: str = "",
    author: str = "",
    description: str = "",
    time_updated: int = 0,
) -> None:
    db = _get_conn()
    db.execute(
        """INSERT OR REPLACE INTO mod_cache (workshop_id, title, author, description, time_updated, cached_at)
           VALUES (?,?,?,?,?,datetime('now'))""",
        (workshop_id, title, author, description, time_updated),
    )
    db.commit()


def get_cached_mod(workshop_id: str) -> dict | None:
    db = _get_conn()
    row = db.execute("SELECT * FROM mod_cache WHERE workshop_id = ?", (workshop_id,)).fetchone()
    return dict(row) if row else None


def get_download_stats() -> dict:
    db = _get_conn()
    total = db.execute("SELECT COUNT(*) as n FROM download_history").fetchone()["n"]
    success = db.execute(
        "SELECT COUNT(*) as n FROM download_history WHERE status='success'"
    ).fetchone()["n"]
    failed = db.execute(
        "SELECT COUNT(*) as n FROM download_history WHERE status='failed'"
    ).fetchone()["n"]
    return {"total": total, "success": success, "failed": failed}


def clear_history() -> None:
    db = _get_conn()
    db.execute("DELETE FROM download_history")
    db.commit()

"""Persistent mod metadata cache backed by SQLite.

Provides per-mod incremental refresh: on startup, only re-parses About.xml
for mod folders whose mtime has changed since the last cache write.
New mods are scanned; deleted mods are cleaned up automatically.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from rwmod.database import _get_conn
from rwmod.metadata import ModMeta, read_mod_metadata


def get_or_refresh_metas(mods_dir: Path) -> list[ModMeta]:
    """Return mod metadata using SQLite cache with per-mod incremental refresh.

    Strategy:
    1. Read all cached entries from local_mod_metadata table.
    2. Scan mods_dir via os.scandir (fast — DirEntry caches stat).
    3. For each mod folder:
       - Cache hit + mtime unchanged → use cached data (zero I/O).
       - Cache miss or mtime changed → parse About.xml.
    4. Remove deleted mods from cache.
    5. Write back newly parsed entries.

    Returns:
        List of ModMeta, sorted by folder name for deterministic output.
    """
    if not mods_dir.exists():
        _clear_all()
        return []

    db = _get_conn()
    cached = {
        row["folder"]: dict(row)
        for row in db.execute("SELECT * FROM local_mod_metadata").fetchall()
    }

    current_folders: set[str] = set()
    metas: list[ModMeta] = []
    needs_upsert: list[ModMeta] = []
    deleted: list[str] = []

    with os.scandir(mods_dir) as entries:
        for entry in sorted(entries, key=lambda e: e.name):
            if not entry.is_dir():
                continue
            folder = entry.name
            current_folders.add(folder)

            row = cached.get(folder)
            if row is not None and row["dir_mtime"] >= entry.stat().st_mtime:
                # Cache hit — folder unchanged since last scan
                metas.append(
                    ModMeta(
                        folder=folder,
                        name=row["name"],
                        package_id=row["package_id"],
                        workshop_id=row["workshop_id"],
                    )
                )
            else:
                # Cache miss or stale — parse About.xml from disk
                meta = read_mod_metadata(Path(entry.path))
                if meta:
                    metas.append(meta)
                    needs_upsert.append(meta)

    # Remove deleted mods from cache
    deleted = [f for f in cached if f not in current_folders]

    # Write changes in a single transaction
    if deleted or needs_upsert:
        now = time.time()
        with db:
            for folder in deleted:
                db.execute("DELETE FROM local_mod_metadata WHERE folder = ?", (folder,))
            for m in needs_upsert:
                mod_path = mods_dir / m.folder
                mtime = mod_path.stat().st_mtime if mod_path.is_dir() else 0
                db.execute(
                    """INSERT OR REPLACE INTO local_mod_metadata
                       (folder, name, package_id, workshop_id, dir_mtime, cached_at)
                       VALUES (?,?,?,?,?,?)""",
                    (m.folder, m.name, m.package_id, m.workshop_id, mtime, now),
                )

    return metas


def invalidate_folder(folder: str) -> None:
    """Remove a single mod folder from the persistent cache."""
    db = _get_conn()
    with db:
        db.execute("DELETE FROM local_mod_metadata WHERE folder = ?", (folder,))


def invalidate_all() -> None:
    """Clear the entire persistent cache."""
    _clear_all()


def _clear_all() -> None:
    db = _get_conn()
    with db:
        db.execute("DELETE FROM local_mod_metadata")

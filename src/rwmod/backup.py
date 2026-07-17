"""Mod backup & rollback — zip existing mod before overwriting.

Backups are stored as timestamped zip files:
    {backup_dir}/{workshop_id}__{folder_name}__{iso_timestamp}.zip

The double-underscore separator avoids collisions with mod names that
contain single underscores.
"""

from __future__ import annotations

import logging
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path

_log = logging.getLogger(__name__)

_SEP = "__"  # separator between workshop_id, folder_name, timestamp


def backup_mod(
    mods_dir: Path,
    workshop_id: str,
    folder_name: str,
    backup_dir: Path,
) -> Path | None:
    """Zip an existing mod folder before it gets overwritten.

    Args:
        mods_dir: RimWorld Mods directory.
        workshop_id: Steam Workshop ID of the mod.
        folder_name: Current folder name of the mod in mods_dir.
        backup_dir: Where to store backup zips.

    Returns:
        Path to the created zip, or None if backup was skipped.
    """
    source = mods_dir / folder_name
    if not source.is_dir():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    safe_name = _safe_filename(folder_name)
    zip_path = backup_dir / f"{workshop_id}{_SEP}{safe_name}{_SEP}{ts}.zip"

    _log.info("备份: %s → %s", folder_name, zip_path.name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(source.rglob("*")):
            if f.is_file():
                # Store relative to mods_dir so restore extracts cleanly
                arcname = str(f.relative_to(mods_dir))
                zf.write(f, arcname)

    return zip_path


def restore_mod(
    mods_dir: Path,
    workshop_id: str,
    backup_dir: Path,
    backup_filename: str | None = None,
) -> dict:
    """Restore a mod from backup.

    Args:
        mods_dir: RimWorld Mods directory.
        workshop_id: Steam Workshop ID to restore.
        backup_dir: Where backups are stored.
        backup_filename: Specific backup file to restore, or None for latest.

    Returns:
        {"ok": bool, "msg": str, "restored_folder": str|None}
    """
    backups = _find_backups(backup_dir, workshop_id)
    if not backups:
        return {"ok": False, "msg": f"未找到 {workshop_id} 的备份"}

    if backup_filename:
        target = backup_dir / backup_filename
        if not target.exists():
            return {"ok": False, "msg": f"备份文件不存在: {backup_filename}"}
    else:
        # Latest backup (sorted by timestamp in filename)
        target = backups[-1]["path"]

    # Remove current mod if exists
    meta = _backup_metadata(target)
    folder_name = meta.get("folder_name", f"mod_{workshop_id}")
    current = mods_dir / folder_name
    if current.exists():
        shutil.rmtree(current)

    # Extract
    _log.info("回滚: %s → %s", target.name, folder_name)
    with zipfile.ZipFile(target, "r") as zf:
        zf.extractall(mods_dir)

    return {"ok": True, "msg": f"已恢复 {folder_name}", "restored_folder": folder_name}


def list_backups(backup_dir: Path, workshop_id: str | None = None) -> list[dict]:
    """List all backups, optionally filtered by workshop_id.

    Returns list of {filename, workshop_id, folder_name, timestamp, size_mb}.
    """
    if not backup_dir.exists():
        return []

    results: list[dict] = []
    for f in sorted(backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not f.is_file():
            continue
        name = f.stem
        parts = name.split(_SEP, 2)
        if len(parts) < 3:
            continue
        wid, folder_name, ts = parts
        if workshop_id and wid != workshop_id:
            continue
        results.append(
            {
                "filename": f.name,
                "workshop_id": wid,
                "folder_name": folder_name,
                "timestamp": _parse_timestamp(ts),
                "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            }
        )

    if workshop_id:
        return results
    return results


def delete_backup(backup_dir: Path, filename: str) -> bool:
    """Delete a specific backup zip. Returns True if deleted."""
    path = backup_dir / filename
    if not path.exists():
        return False
    path.unlink()
    _log.info("删除备份: %s", filename)
    return True


def cleanup_backups(backup_dir: Path, keep_per_mod: int = 5) -> int:
    """Keep only the N most recent backups per mod. Returns count of deleted files."""
    if not backup_dir.exists():
        return 0

    by_mod: dict[str, list[Path]] = {}
    for f in backup_dir.glob("*.zip"):
        parts = f.stem.split(_SEP, 1)
        if parts:
            by_mod.setdefault(parts[0], []).append(f)

    deleted = 0
    for paths in by_mod.values():
        paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for old in paths[keep_per_mod:]:
            old.unlink()
            deleted += 1
            _log.info("清理旧备份: %s", old.name)

    return deleted


# ── internal helpers ───────────────────────────────────────────────


def _safe_filename(name: str) -> str:
    """Replace filesystem-unfriendly characters."""
    import re

    return re.sub(r'[<>:"/\\|?*]', "_", name)


def _find_backups(backup_dir: Path, workshop_id: str) -> list[dict]:
    """Find all backups for a workshop_id, sorted by timestamp."""
    results: list[dict] = []
    prefix = f"{workshop_id}{_SEP}"
    for f in sorted(backup_dir.glob(f"{prefix}*.zip")):
        results.append(
            {
                "path": f,
                "filename": f.name,
                "mtime": f.stat().st_mtime,
            }
        )
    return results


def _backup_metadata(zip_path: Path) -> dict:
    """Extract metadata from backup filename."""
    parts = zip_path.stem.split(_SEP, 2)
    if len(parts) < 3:
        return {}
    return {"workshop_id": parts[0], "folder_name": parts[1], "timestamp": parts[2]}


def _parse_timestamp(ts_str: str) -> str:
    """Convert YYYYMMDD_HHMMSS to ISO format for display."""
    try:
        dt = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
        return dt.replace(tzinfo=UTC).isoformat()
    except ValueError:
        return ts_str

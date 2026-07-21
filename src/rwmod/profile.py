"""Mod profile management — save/restore ModsConfig.xml snapshots.

RimWorld players often switch between mod sets (vanilla, medieval, etc.).
Profiles are stored as named XML copies in ~/.rwmod/profiles/.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from rwmod.utils import safe_filename

__all__ = [
    "PROFILES_DIR",
    "list_profiles",
    "save_profile",
    "restore_profile",
    "delete_profile",
    "resolve_modsconfig_path",
]

PROFILES_DIR = Path.home() / ".rwmod" / "profiles"

_log = logging.getLogger(__name__)


def resolve_modsconfig_path(rimworld_dir: Path) -> Path | None:
    """Find the active ModsConfig.xml for the RimWorld installation.

    Checks common locations:
    1. Standard Ludeon Studios config (Steam, GoG)
    2. RimWorld install directory
    """
    import platform

    # Location 1: Ludeon Studios app data (most common)
    if platform.system() == "Windows":
        base = Path.home() / "AppData" / "LocalLow" / "Ludeon Studios"
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Ludeon Studios"
    else:
        base = Path.home() / ".config" / "unity3d" / "Ludeon Studios"

    for config_dir in base.glob("RimWorld*"):
        path = config_dir / "Config" / "ModsConfig.xml"
        if path.exists():
            return path

    # Location 2: RimWorld install directory
    local = rimworld_dir / "ModsConfig.xml"
    if local.exists():
        return local

    return None


def list_profiles() -> list[dict]:
    """List all saved profiles with metadata."""
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for f in sorted(PROFILES_DIR.glob("*.xml"), key=lambda p: p.stat().st_mtime, reverse=True):
        if not f.is_file():
            continue
        name = f.stem
        mod_count = _count_mods_in_xml(f)
        mtime = f.stat().st_mtime
        results.append(
            {
                "name": name,
                "mod_count": mod_count,
                "saved_at": datetime.fromtimestamp(mtime, tz=UTC).isoformat(),
                "size_kb": round(f.stat().st_size / 1024, 1),
            }
        )
    return results


def save_profile(name: str, source_path: Path | str, label: str = "") -> dict:
    """Save a ModsConfig.xml snapshot as a named profile.

    Args:
        name: Profile name (used as filename stem).
        source_path: Path to ModsConfig.xml, or XML string content.
        label: Optional human-readable description.

    Returns:
        {"ok": bool, "msg": str}
    """
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = safe_filename(name)
    dest = PROFILES_DIR / f"{safe_name}.xml"

    source = (
        Path(source_path)
        if isinstance(source_path, str) and not source_path.startswith("<")
        else source_path
    )

    try:
        if isinstance(source, Path) and source.exists():
            content = source.read_text(encoding="utf-8")
        else:
            content = str(source)
    except Exception as e:
        return {"ok": False, "msg": f"读取失败: {e}"}

    # Validate it's valid XML (basic check)
    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        return {"ok": False, "msg": f"无效的 XML: {e}"}

    dest.write_text(content, encoding="utf-8")
    mod_count = _count_mods_in_xml(dest)
    _log.info("保存 profile: %s (%d mods)", safe_name, mod_count)
    return {
        "ok": True,
        "msg": f"已保存 '{safe_name}'（{mod_count} 个 Mod）",
        "mod_count": mod_count,
    }


def restore_profile(name: str, target_path: Path) -> dict:
    """Restore a profile by copying it to the ModsConfig.xml location.

    Args:
        name: Profile name to restore.
        target_path: Where to write ModsConfig.xml.

    Returns:
        {"ok": bool, "msg": str}
    """
    safe_name = safe_filename(name)
    src = PROFILES_DIR / f"{safe_name}.xml"

    if not src.exists():
        return {"ok": False, "msg": f"Profile 不存在: {safe_name}"}

    try:
        # Backup existing ModsConfig.xml if present
        if target_path.exists():
            backup = target_path.with_suffix(".xml.rwmod.bak")
            target_path.rename(backup)
            _log.info("备份现有 ModsConfig.xml → %s", backup.name)

        content = src.read_text(encoding="utf-8")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        mod_count = _count_mods_in_xml(src)
        _log.info("恢复 profile: %s → %s (%d mods)", safe_name, target_path, mod_count)
        return {
            "ok": True,
            "msg": f"已恢复 '{safe_name}'（{mod_count} 个 Mod）",
            "mod_count": mod_count,
        }
    except Exception as e:
        return {"ok": False, "msg": f"恢复失败: {e}"}


def delete_profile(name: str) -> bool:
    """Delete a saved profile."""
    safe_name = safe_filename(name)
    path = PROFILES_DIR / f"{safe_name}.xml"
    if not path.exists():
        return False
    path.unlink()
    _log.info("删除 profile: %s", safe_name)
    return True


# ── internal helpers ───────────────────────────────────────────────


def _count_mods_in_xml(path: Path) -> int:
    """Count <li> elements under <activeMods> in a ModsConfig.xml."""
    try:
        root = ET.parse(path).getroot()
        active = root.find("activeMods")
        if active is not None:
            return len(active.findall("li"))
    except Exception:
        pass
    return 0


def _safe_filename(name: str) -> str:
    """Sanitize a profile name for use as a filename."""
    from rwmod.utils import safe_filename

    return safe_filename(name, allow_empty=False)

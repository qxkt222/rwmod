"""RimWorld version detection and mod compatibility checking.

Reads RimWorld version from Version.txt and compares against each
mod's <supportedVersions> in About.xml.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from rwmod.metadata import ModMeta

_log = logging.getLogger(__name__)


def detect_rimworld_version(rimworld_dir: Path) -> str | None:
    """Detect installed RimWorld version.

    Checks Version.txt (Steam installs) first, then looks for
    the Core mod's About.xml (non-Steam / DRM-free installs).
    """
    # Method 1: Version.txt (Steam)
    vfile = rimworld_dir / "Version.txt"
    if vfile.exists():
        raw = vfile.read_text(encoding="utf-8").strip()
        # Format: "1.5.4297 rev1117" → extract "1.5"
        m = re.search(r"(\d+\.\d+)", raw)
        if m:
            return m.group(1)

    # Method 2: Core mod About.xml
    core_about = rimworld_dir / "Data" / "Core" / "About" / "About.xml"
    if core_about.exists():
        try:
            import xml.etree.ElementTree as ET

            root = ET.parse(core_about).getroot()
            target = root.findtext("targetVersion", "")
            if target:
                return target
        except Exception:
            pass

    return None


def check_compatibility(
    metas: list[ModMeta],
    rimworld_version: str,
) -> dict[str, list[dict]]:
    """Check which mods are compatible with the given RimWorld version.

    Args:
        metas: Parsed mod metadata (with supported_versions).
        rimworld_version: Detected RimWorld version (e.g. "1.5").

    Returns:
        {
            "compatible": [{"folder": ..., "name": ..., "supported": [...]}],
            "incompatible": [...],
            "unknown": [...]  # mods that don't declare supportedVersions
        }
    """
    rw_major_minor = _normalize_version(rimworld_version)
    compatible: list[dict] = []
    incompatible: list[dict] = []
    unknown: list[dict] = []

    for m in metas:
        entry = {
            "folder": m.folder,
            "name": m.name,
            "workshop_id": m.workshop_id,
            "supported": m.supported_versions,
        }
        if not m.supported_versions:
            unknown.append(entry)
        elif any(_normalize_version(v) == rw_major_minor for v in m.supported_versions):
            compatible.append(entry)
        else:
            incompatible.append(entry)

    _log.info(
        "Compatibility: %d compatible, %d incompatible, %d unknown (RimWorld %s)",
        len(compatible),
        len(incompatible),
        len(unknown),
        rimworld_version,
    )
    return {"compatible": compatible, "incompatible": incompatible, "unknown": unknown}


def _normalize_version(v: str) -> str:
    """Extract major.minor from a version string like '1.5', '1.5.0', 'v1.5'."""
    m = re.search(r"(\d+\.\d+)", v.strip())
    return m.group(1) if m else v.strip()

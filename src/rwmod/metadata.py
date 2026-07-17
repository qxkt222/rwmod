"""Shared XML parsing utilities — avoid duplicate About.xml parsing."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

__all__ = ["read_mod_metadata", "ModMeta"]


class ModMeta:
    """Parsed metadata from a mod's About.xml."""

    __slots__ = ("folder", "name", "package_id", "workshop_id", "supported_versions")

    def __init__(
        self,
        folder: str,
        name: str = "?",
        package_id: str = "",
        workshop_id: str = "",
        supported_versions: list[str] | None = None,
    ):
        self.folder = folder
        self.name = name
        self.package_id = package_id
        self.workshop_id = workshop_id
        self.supported_versions = supported_versions or []


def read_mod_metadata(mod_dir: Path) -> ModMeta | None:
    """Read About.xml + PublishedFileId.txt from a mod directory.
    Returns None if the directory doesn't look like a valid mod.
    """
    if not mod_dir.is_dir():
        return None

    about = mod_dir / "About" / "About.xml"
    if not about.exists():
        return None

    name = "?"
    pkg = ""
    versions: list[str] = []
    try:
        root = ET.parse(about).getroot()
        name = root.findtext("name", "?") or "?"
        pkg = root.findtext("packageId", "") or ""
        sv = root.find("supportedVersions")
        if sv is not None:
            versions = [li.text or "" for li in sv.findall("li") if li.text]
    except Exception:
        pass

    pf = mod_dir / "About" / "PublishedFileId.txt"
    wid = pf.read_text(encoding="utf-8").strip() if pf.exists() else ""

    return ModMeta(
        folder=mod_dir.name, name=name, package_id=pkg, workshop_id=wid, supported_versions=versions
    )

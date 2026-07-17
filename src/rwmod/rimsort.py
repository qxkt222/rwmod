"""RimSort integration — generate ModsConfig.xml, compare, sync."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

__all__ = [
    "generate_modsconfig",
    "compare_modsconfig",
    "parse_modsconfig",
    "resolve_missing_workshop_ids",
]


def generate_modsconfig(mods_dir: Path, output_path: Path | None = None) -> str:
    """Generate a RimSort-compatible ModsConfig.xml from installed mods.

    Returns the XML string. If output_path is given, writes to disk.
    """
    root = ET.Element("ModsConfigData")

    ET.SubElement(root, "version").text = "1.0.0"
    ET.SubElement(root, "buildNumber").text = "0"

    active_mods = ET.SubElement(root, "activeMods")

    # Collect packageIds from installed mods
    package_ids: list[str] = []
    for d in sorted(mods_dir.iterdir()):
        if not d.is_dir():
            continue
        about = d / "About" / "About.xml"
        if about.exists():
            try:
                tree = ET.parse(about)
                pid = tree.getroot().findtext("packageId", "")
                if pid:
                    package_ids.append(pid)
            except Exception:
                pass

    for pid in package_ids:
        ET.SubElement(active_mods, "li").text = pid

    et = ET.ElementTree(root)
    ET.indent(et, space="  ")
    xml_str = ET.tostring(root, encoding="unicode")

    if output_path:
        output_path.write_text(xml_str, encoding="utf-8")

    return xml_str


def parse_modsconfig(path: Path) -> dict:
    """Parse a ModsConfig.xml and return its structure."""
    if not path.exists():
        return {"error": "file not found"}

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception as e:
        return {"error": str(e)}

    active_mods = root.find("activeMods")
    items: list[str] = []
    if active_mods is not None:
        for li in active_mods.findall("li"):
            if li.text:
                items.append(li.text.strip())

    return {
        "version": root.findtext("version", ""),
        "build_number": root.findtext("buildNumber", ""),
        "active_mods": items,
        "total": len(items),
    }


def compare_modsconfig(modsconfig_path: Path, mods_dir: Path) -> dict:
    """Compare ModsConfig.xml with installed mods.

    Returns: { installed: [...], missing: [...], extra: [...], load_order: [...] }
    """
    config_data = parse_modsconfig(modsconfig_path)
    if "error" in config_data:
        return config_data

    config_ids = set(config_data["active_mods"])
    installed_ids: set[str] = set()

    for d in mods_dir.iterdir():
        about = d / "About" / "About.xml"
        if about.exists():
            try:
                pid = ET.parse(about).getroot().findtext("packageId", "")
                if pid:
                    installed_ids.add(pid)
            except Exception:
                pass

    missing = [pid for pid in config_data["active_mods"] if pid not in installed_ids]
    extra = list(installed_ids - config_ids)
    installed_list = list(installed_ids & config_ids)

    return {
        "load_order": config_data["active_mods"],
        "total_in_config": len(config_data["active_mods"]),
        "installed": installed_list,
        "installed_count": len(installed_list),
        "missing": missing,
        "missing_count": len(missing),
        "extra": extra,
        "extra_count": len(extra),
    }


def resolve_missing_workshop_ids(missing_package_ids: list[str], mods_dir: Path) -> list[dict]:
    """For missing packageIds, try to resolve to workshop IDs from installed mods.

    This is a best-effort lookup — it works if the mod was previously installed
    and its PublishedFileId.txt exists elsewhere.
    """

    # Build packageId → workshopId map from ALL About.xml files
    pkg_to_wid: dict[str, str] = {}
    for d in mods_dir.iterdir():
        pf = d / "About" / "PublishedFileId.txt"
        about = d / "About" / "About.xml"
        if pf.exists() and about.exists():
            try:
                pid = ET.parse(about).getroot().findtext("packageId", "")
                wid = pf.read_text(encoding="utf-8").strip()
                if pid and wid:
                    pkg_to_wid[pid] = wid
            except Exception:
                pass

    results: list[dict] = []
    for pid in missing_package_ids:
        wid = pkg_to_wid.get(pid, "")
        results.append({"package_id": pid, "workshop_id": wid, "resolved": bool(wid)})
    return results

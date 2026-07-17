"""Parsers for mod lists, collections, and ModsConfig.xml."""

from __future__ import annotations

import json
import logging
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

_log = logging.getLogger(__name__)

__all__ = [
    "parse_modlist_file",
    "parse_collection_dir",
    "parse_mods_config",
    "get_installed_package_ids",
    "resolve_workshop_ids",
]


def parse_modlist_file(file_path: Path) -> list[str]:
    """Extract mod IDs from a text file, one per line, supports # comments and URLs."""
    ids: list[str] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = re.search(r"[?&]id=(\d+)", stripped)
        if m:
            ids.append(m.group(1))
        elif stripped.isdigit():
            ids.append(stripped)
    return ids


def parse_collection_dir(collection_path: Path) -> list[str]:
    """Parse a downloaded Steam collection directory to extract mod IDs.
    Supports legacy .bin format and JSON format.
    """
    ids: list[str] = []
    if not collection_path.exists():
        return ids

    # Try legacy binary format first (steam workshop collection)
    for f in collection_path.iterdir():
        if f.suffix == ".bin" or "_legacy" in f.name or f.suffix == "":
            try:
                data = f.read_bytes()
                parsed = _parse_legacy_collection(data)
                if parsed:
                    ids.extend(parsed)
            except OSError as e:
                _log.debug("跳过不可读文件 %s: %s", f.name, e)

    # Try JSON format as fallback
    for f in collection_path.iterdir():
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                _extract_ids_from_json(data, ids)
            except (OSError, json.JSONDecodeError) as e:
                _log.debug("跳过不可读 JSON %s: %s", f.name, e)

    return list(dict.fromkeys(ids))  # dedup, preserve order


def _parse_legacy_collection(data: bytes) -> list[str]:
    """Parse Steam legacy collection binary format.

    Format: 4-byte LE uint32 count, followed by N × 8-byte LE uint64 workshop IDs.
    Fallback: if count doesn't validate, try flat 8-byte sequence.
    """
    if len(data) < 4:
        return []

    # Try header format: 4-byte count + N × 8-byte IDs
    count = struct.unpack_from("<I", data, 0)[0]
    total_expected = 4 + count * 8
    if count > 0 and count < 10000 and len(data) >= total_expected:
        ids: list[str] = []
        for i in range(count):
            offset = 4 + i * 8
            wid = struct.unpack_from("<Q", data, offset)[0]
            if wid > 0:
                ids.append(str(wid))
        if ids:
            return ids

    # Fallback: raw 8-byte LE uint64 sequence (legacy format without count header)
    ids = []
    offset = 0
    while offset + 8 <= len(data):
        val = struct.unpack_from("<Q", data, offset)[0]
        offset += 8
        if 0 < val < 10_000_000_000:
            ids.append(str(val))
    return ids


def _extract_ids_from_json(data: object, ids: list[str]) -> None:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str) and item.isdigit():
                ids.append(item)
            elif isinstance(item, dict):
                _extract_from_dict(item, ids)
    elif isinstance(data, dict):
        _extract_from_dict(data, ids)


def _extract_from_dict(d: dict[str, object], ids: list[str]) -> None:
    for key in ("children", "items", "mods"):
        children = d.get(key, [])
        if isinstance(children, list):
            for item in children:
                if isinstance(item, dict):
                    mid = item.get("publishedfileid", "") or item.get("id", "")
                    if str(mid).isdigit():
                        ids.append(str(mid))
                elif isinstance(item, str) and item.isdigit():
                    ids.append(item)


def parse_mods_config(config_xml: Path) -> list[str]:
    """Extract mod packageIds from a RimSort ModsConfig.xml."""
    try:
        root = ET.parse(config_xml).getroot()
    except ET.ParseError as e:
        _log.error("无法解析 ModsConfig.xml: %s", e)
        return []
    ids: list[str] = []
    for li in root.findall(".//li"):
        if li.text:
            ids.append(li.text.strip())
    return ids


def get_installed_package_ids(mods_dir: Path) -> set[str]:
    """Collect packageId from every mod folder's About.xml."""
    result: set[str] = set()
    if not mods_dir.exists():
        return result
    for d in mods_dir.iterdir():
        about = d / "About" / "About.xml"
        if about.exists():
            try:
                pkg = ET.parse(about).getroot().findtext("packageId", "")
                if pkg:
                    result.add(pkg)
            except ET.ParseError as e:
                _log.debug("跳过损坏 About.xml %s: %s", d.name, e)
    return result


def resolve_workshop_ids(package_ids: list[str], mods_dir: Path) -> tuple[list[str], list[str]]:
    """Map packageIds → workshop IDs using installed mods as a lookup.
    Returns (known_ids, unknown_package_ids).
    """
    pkg_to_wid: dict[str, str] = {}
    for d in mods_dir.iterdir():
        pf = d / "About" / "PublishedFileId.txt"
        about = d / "About" / "About.xml"
        if pf.exists() and about.exists():
            try:
                pkg = ET.parse(about).getroot().findtext("packageId", "")
                wid = pf.read_text(encoding="utf-8").strip()
                if pkg and wid:
                    pkg_to_wid[pkg] = wid
            except (ET.ParseError, OSError) as e:
                _log.debug("跳过 %s: %s", d.name, e)

    known: list[str] = []
    unknown: list[str] = []
    for pid in package_ids:
        wid = pkg_to_wid.get(pid)
        if wid:
            known.append(wid)
        else:
            unknown.append(pid)
    return known, unknown

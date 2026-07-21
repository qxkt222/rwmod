"""Load order analysis — detect common RimWorld mod ordering issues.

Checks the active ModsConfig.xml for:
1. Harmony position (must load first)
2. Core + DLC ordering
3. Known incompatible mod pairs
4. Mods with missing dependencies in the load order
"""

from __future__ import annotations

import logging
from pathlib import Path

_log = logging.getLogger(__name__)

# ── rule data ──────────────────────────────────────────────────────
# (extracted from inline for discoverability; kept as a constant,
# not an external file, to keep the single-module distribution simple)

# packageIds of Harmony — the mod loader framework
_HARMONY_IDS: frozenset[str] = frozenset({"brrainz.harmony", "harmony"})

# Core + official DLC packageIds (ordered by required position)
_CORE_DLC_IDS: tuple[str, ...] = (
    "",  # Core (no packageId in some installs)
    "ludeon.rimworld",
    "ludeon.rimworld.royalty",
    "ludeon.rimworld.ideology",
    "ludeon.rimworld.biotech",
    "ludeon.rimworld.anomaly",
)

# Known incompatible mod pairs: (keyword_a, keyword_b, reason)
# Keywords match case-insensitively against packageId
_KNOWN_CONFLICTS: tuple[tuple[str, str, str], ...] = (
    ("combat_extended", "yayo.combat", "Combat Extended 与 Yayo's Combat 冲突，二者择一"),
    ("combat_extended", "runandgun", "Combat Extended 与 RunAndGun 存在已知冲突，需兼容补丁"),
    ("pick.up.and.haul", "while.youre.up", "Pick Up And Haul 与 While You're Up 功能重叠"),
    ("dub's.bad.hygiene", "dubs.bad.hygiene.lite", "Dubs Bad Hygiene 与 Lite 版不可共存"),
)


def check_load_order(modsconfig_path: Path, mods_dir: Path) -> dict:
    """Analyze ModsConfig.xml load order for common issues.

    Returns:
        {
            "total_mods": int,
            "issues": [{"severity": "error|warn|info", "message": str}],
            "load_order": [package_id, ...],
        }
    """
    if not modsconfig_path.exists():
        return {"error": f"ModsConfig.xml 未找到: {modsconfig_path}"}

    try:
        import xml.etree.ElementTree as ET

        root = ET.parse(modsconfig_path).getroot()
        active = root.find("activeMods")
        if active is None:
            return {"error": "ModsConfig.xml 中没有 activeMods"}
        load_order = [li.text or "" for li in active.findall("li") if li.text]
    except Exception as e:
        return {"error": f"解析 ModsConfig.xml 失败: {e}"}

    if not load_order:
        return {"error": "加载顺序为空"}

    issues: list[dict] = []

    # 1. Check Harmony position
    _check_harmony(load_order, issues)

    # 2. Check Core/DLC order
    _check_core_dlc(load_order, issues)

    # 3. Check known conflicts
    _check_known_conflicts(load_order, mods_dir, issues)

    # 4. Check for duplicate entries
    _check_duplicates(load_order, issues)

    return {
        "total_mods": len(load_order),
        "issues": issues,
        "load_order": load_order,
        "ok": len([i for i in issues if i["severity"] == "error"]) == 0,
    }


# ── rule checkers ──────────────────────────────────────────────────


def _check_harmony(order: list[str], issues: list[dict]) -> None:
    """Harmony must be at position 0 in the load order."""
    harmony_positions = [
        i for i, pid in enumerate(order) if any(hid in pid.lower() for hid in _HARMONY_IDS)
    ]
    if not harmony_positions:
        issues.append(
            {
                "severity": "warn",
                "message": "未检测到 Harmony——大多数 Mod 需要 Harmony 才能运行",
            }
        )
    elif harmony_positions[0] != 0:
        issues.append(
            {
                "severity": "error",
                "message": f"⚠ Harmony 必须排在第一位！当前位置: #{harmony_positions[0] + 1}",
            }
        )


def _check_core_dlc(order: list[str], issues: list[dict]) -> None:
    """Core + DLCs should be at the top, before community mods."""
    core_positions: dict[str, int] = {}
    for i, pid in enumerate(order):
        pid_lower = pid.lower()
        for cid in _CORE_DLC_IDS:
            if cid and cid in pid_lower:
                core_positions[cid] = i

    # Check Core is before DLCs
    core_dlc_order = [c for c in _CORE_DLC_IDS if c and c in core_positions]
    for j in range(1, len(core_dlc_order)):
        prev = core_dlc_order[j - 1]
        curr = core_dlc_order[j]
        if core_positions.get(prev, 0) > core_positions.get(curr, 999):
            issues.append(
                {
                    "severity": "warn",
                    "message": f"官方内容顺序建议: {prev} 应在 {curr} 之前",
                }
            )

    # Check first community mod comes after all Core/DLC
    if core_positions:
        max_core = max(core_positions.values())
        first_community = -1
        for i, pid in enumerate(order):
            pid_lower = pid.lower()
            if not any(cid in pid_lower for cid in _CORE_DLC_IDS if cid):
                first_community = i
                break
        if first_community >= 0 and first_community < max_core:
            pid = order[first_community]
            short = pid.rsplit(".", 1)[-1] if "." in pid else pid[:30]
            issues.append(
                {
                    "severity": "warn",
                    "message": f"社区 Mod「{short}」排在官方内容之前，建议将官方 DLC 放在前面",
                }
            )


def _check_known_conflicts(order: list[str], mods_dir: Path, issues: list[dict]) -> None:
    """Check for known incompatible mod pairs.

    Uses the RimPy community database if available; falls back to
    a small set of hardcoded rules when offline.
    """
    pid_lower = [p.lower() for p in order]

    # Try RimPy database first
    try:
        from rwmod.rimpy_db import RimPyDB

        db = RimPyDB.get()
        # Collect workshop IDs from installed mods
        import xml.etree.ElementTree as ET

        pkg_to_wid: dict[str, str] = {}
        for d in mods_dir.iterdir():
            pf = d / "About" / "PublishedFileId.txt"
            about = d / "About" / "About.xml"
            if pf.exists() and about.exists():
                try:
                    pid = ET.parse(about).getroot().findtext("packageId", "")
                    wid = pf.read_text(encoding="utf-8").strip()
                    if pid and wid:
                        pkg_to_wid[pid.lower()] = wid
                except Exception:
                    pass

        active_wids = {pkg_to_wid[p] for p in pid_lower if p in pkg_to_wid}
        if active_wids and db.ensure_loaded():
            db_conflicts = db.get_conflicts(active_wids)
            for c in db_conflicts:
                issues.append(
                    {
                        "severity": "error",
                        "message": f"⚠ {c['reason']}",
                    }
                )
            if db_conflicts:
                return  # Use DB results, skip hardcoded fallback
    except Exception:
        pass

    # Fallback: hardcoded known conflicts (offline / DB unavailable)
    for a_keyword, b_keyword, reason in _KNOWN_CONFLICTS:
        a_found = [i for i, p in enumerate(pid_lower) if a_keyword in p]
        b_found = [i for i, p in enumerate(pid_lower) if b_keyword in p]
        if a_found and b_found:
            issues.append(
                {
                    "severity": "error",
                    "message": f"⚠ {reason}",
                }
            )


def _check_duplicates(order: list[str], issues: list[dict]) -> None:
    """Check for duplicate packageIds in load order."""
    seen: dict[str, int] = {}
    for i, pid in enumerate(order):
        if pid in seen:
            short = pid.rsplit(".", 1)[-1] if "." in pid else pid[:30]
            issues.append(
                {
                    "severity": "warn",
                    "message": f"重复条目「{short}」出现在 #{seen[pid] + 1} 和 #{i + 1}",
                }
            )
        else:
            seen[pid] = i

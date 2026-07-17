"""Download + retry + copy-to-mods logic."""

from __future__ import annotations

import logging
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from rwmod.config import Config
from rwmod.steamcmd import SteamCMD

__all__ = ["download_one", "extract_mod_id", "_find_existing", "_pick_folder_name"]

_log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5


def extract_mod_id(raw: str) -> str | None:
    """Parse a mod ID from raw input: plain digits or workshop URL."""
    m = re.search(r"[?&]id=(\d+)", raw)
    if m:
        return m.group(1)
    if raw.strip().isdigit():
        return raw.strip()
    return None


def _find_existing(mods_dir: Path, mod_id: str) -> Path | None:
    for d in mods_dir.iterdir():
        if not d.is_dir():
            continue
        pf = d / "About" / "PublishedFileId.txt"
        if pf.exists() and pf.read_text(encoding="utf-8").strip() == mod_id:
            return d
    return None


def _read_about_field(mod_dir: Path, tag: str) -> str:
    about = mod_dir / "About" / "About.xml"
    if about.exists():
        try:
            return ET.parse(about).getroot().findtext(tag, "") or ""
        except Exception:
            pass
    return ""


def _pick_folder_name(workshop_path: Path, mod_id: str) -> str:
    pkg = _read_about_field(workshop_path, "packageId")
    if pkg:
        return re.sub(r'[<>:"/\\|?*]', "_", pkg)
    name = _read_about_field(workshop_path, "name")
    if name:
        return f"{re.sub(r'[<>:"/\\|?*]', '_', name)}_{mod_id}"
    return f"mod_{mod_id}"


def download_one(config: Config, mod_id: str, force: bool = False) -> bool:
    """Download a single mod. Returns True on success."""
    steamcmd = SteamCMD(config.steamcmd_path)

    existing = _find_existing(config.mods_dir, mod_id)
    if existing:
        if force:
            # Backup before overwriting — so user can rollback if update breaks something
            _log.info("覆盖前备份: %s", existing.name)
            try:
                from rwmod.backup import backup_mod

                backup_mod(config.mods_dir, mod_id, existing.name, config.backup_dir)
            except Exception as e:
                _log.warning("备份失败: %s", e)
            shutil.rmtree(existing)
        else:
            _log.info("已安装: %s", existing.name)
            return True

    for attempt in range(1, MAX_RETRIES + 1):
        _log.info("尝试 %s/%s...", attempt, MAX_RETRIES)
        rc, lines = steamcmd.workshop_download(mod_id)

        for line in lines:
            low = line.lower()
            if any(kw in low for kw in ("download", "success", "error", "fail", "item")):
                _log.info("  %s", line)

        if rc != 0:
            if attempt < MAX_RETRIES:
                _log.warning("SteamCMD 返回 %s，%ss 后重试...", rc, RETRY_DELAY)
                time.sleep(RETRY_DELAY)
            continue

        workshop_dir = steamcmd.workshop_content_dir / mod_id
        if not workshop_dir.exists():
            _log.warning("未找到下载内容: %s", mod_id)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            continue

        # Check if this is a collection (no About.xml → likely a collection)
        about = workshop_dir / "About" / "About.xml"
        if not about.exists():
            from rwmod.parser import parse_collection_dir

            collection_ids = parse_collection_dir(workshop_dir)
            if collection_ids:
                _log.info("检测到合集，包含 %s 个 Mod，逐个下载...", len(collection_ids))
                ok = 0
                for cid in collection_ids:
                    if download_one(config, cid, force=force):
                        ok += 1
                _log.info("合集下载完成: %s/%s", ok, len(collection_ids))
                return ok > 0
            _log.warning("下载的目录不是有效 Mod 也不是合集: %s", mod_id)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            continue

        folder_name = _pick_folder_name(workshop_dir, mod_id)
        dest = config.mods_dir / folder_name
        if dest.exists():
            if force:
                shutil.rmtree(dest)
            else:
                _log.info("目标已存在: %s", dest)
                return True

        shutil.copytree(workshop_dir, dest)
        _log.info("下载完成: %s", folder_name)

        # Store download timestamp for future update checks
        (dest / ".rwmod_last_updated").write_text(str(int(time.time())))

        # Auto-download dependencies
        try:
            from rwmod.workshop import fetch_item_dependencies

            deps = fetch_item_dependencies([mod_id])
            if mod_id in deps and deps[mod_id]:
                _log.info("检测到 %s 个依赖: %s", len(deps[mod_id]), deps[mod_id])
                for dep_id in deps[mod_id]:
                    if not _find_existing(config.mods_dir, dep_id):
                        _log.info("下载依赖: %s", dep_id)
                        download_one(config, dep_id, force=force)
        except Exception as e:
            _log.warning("依赖检测失败: %s", e)

        return True

    _log.error("下载失败 (%s 次重试后): %s，尝试 Skymods 备用源...", MAX_RETRIES, mod_id)

    # Skymods fallback
    from rwmod.skymods import try_skymods

    result = try_skymods(mod_id, config)
    if result:
        _log.info("Skymods 备用源下载成功: %s → %s", mod_id, result)
        return True
    _log.error("Skymods 备用源也失败: %s", mod_id)
    return False

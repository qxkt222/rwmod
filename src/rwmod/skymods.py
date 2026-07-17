"""Skymods fallback — download mods from smods.ru when SteamCMD fails."""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

__all__ = ["try_skymods"]

from rwmod.config import Config

_log = logging.getLogger(__name__)

SKYMODS_SEARCH = "https://catalogue.smods.ru/"
RIMWORLD_APP_ID = "294100"
_USER_AGENT = "rwmod/1.0"


def try_skymods(mod_id: str, config: Config) -> Path | None:
    """Try to download a mod from Skymods as fallback.

    Returns the path to the extracted mod folder on success, None on failure.
    """
    search_url = f"{SKYMODS_SEARCH}?s={mod_id}&app={RIMWORLD_APP_ID}"

    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except OSError as e:
        _log.warning("Skymods 搜索失败 (%s): %s", mod_id, e)
        return None

    download_url = _extract_download_url(html, mod_id)
    if not download_url:
        _log.info("Skymods 未找到下载链接: %s", mod_id)
        return None

    return _download_and_extract(download_url, mod_id, config)


def _extract_download_url(html: str, mod_id: str) -> str | None:
    """Extract the mod download URL from Skymods search results page."""
    # Method 1: Look for skymods-excerpt-btn link
    m = re.search(r'<a[^>]*class="[^"]*skymods-excerpt-btn[^"]*"[^>]*href="([^"]+)"', html)
    if m:
        return m.group(1)

    # Method 2: Look for generic download button
    m = re.search(r'<a[^>]*href="([^"]*modsbase[^"]*)"', html)
    if m:
        return m.group(1)

    # Method 3: Look for any link containing the mod_id and download-related text
    for pattern in [
        rf'href="([^"]*{mod_id}[^"]*)"[^>]*>.*?(?:download|скачать|Download)',
        r'href="(https://modsbase\.com[^"]+)"',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1)

    return None


def _download_and_extract(url: str, mod_id: str, config: Config) -> Path | None:
    """Download a zip from Skymods and extract to mods directory."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except OSError as e:
        _log.warning("Skymods 下载失败 (%s): %s", mod_id, e)
        return None

    if len(data) < 1024:
        return None

    # Save to temp file and extract
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        # Extract to temp directory first
        extract_dir = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(tmp_path, "r") as zf:
            zf.extractall(extract_dir)

        # Find the mod folder (usually the first subdirectory or the root with About.xml)
        mod_folder = _find_mod_folder(extract_dir)
        if not mod_folder:
            _log.warning("Skymods zip 中未找到 Mod 文件夹: %s", mod_id)
            return None

        # Copy to mods directory
        from rwmod.downloader import _pick_folder_name

        folder_name = _pick_folder_name(mod_folder, mod_id)
        dest = config.mods_dir / folder_name
        if dest.exists():
            dest = config.mods_dir / f"{folder_name}_skymods"
        shutil.copytree(mod_folder, dest)
        _log.info("Skymods 下载成功: %s → %s", mod_id, folder_name)
        return dest
    except (OSError, zipfile.BadZipFile) as e:
        _log.warning("Skymods 解压失败 (%s): %s", mod_id, e)
        return None
    finally:
        tmp_path.unlink(missing_ok=True)
        shutil.rmtree(extract_dir, ignore_errors=True)


def _find_mod_folder(extract_dir: Path) -> Path | None:
    """Find the actual mod folder inside extracted zip contents."""
    # Check if About.xml exists directly
    if (extract_dir / "About" / "About.xml").exists():
        return extract_dir

    # Check one level deep
    for d in extract_dir.iterdir():
        if d.is_dir() and (d / "About" / "About.xml").exists():
            return d

    # Check two levels deep
    for d in extract_dir.iterdir():
        if d.is_dir():
            for sub in d.iterdir():
                if sub.is_dir() and (sub / "About" / "About.xml").exists():
                    return sub

    # If no About.xml found, return the first subdirectory
    dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
    if dirs:
        return dirs[0]

    return None

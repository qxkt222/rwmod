"""Skymods fallback — download mods from smods.ru when SteamCMD fails."""

from __future__ import annotations

import gzip
import logging
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from contextlib import suppress
from pathlib import Path

__all__ = ["try_skymods"]

from rwmod.config import Config

_log = logging.getLogger(__name__)

SKYMODS_SEARCH = "https://catalogue.smods.ru/"
RIMWORLD_APP_ID = "294100"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


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
    """Download from Skymods and extract to mods directory.
    Handles redirects, gzip compression, and non-zip responses gracefully."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPRedirectHandler(),
        urllib.request.HTTPCookieProcessor(),
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with opener.open(req, timeout=60) as resp:
            content_type = resp.headers.get("Content-Type", "")
            data = resp.read()
    except OSError as e:
        _log.warning("Skymods 下载失败 (%s): %s", mod_id, e)
        return None

    if len(data) < 512:
        _log.warning("Skymods 响应内容过短 (%s): %s bytes", mod_id, len(data))
        return None

    # Detect HTML responses — likely a redirect page or error
    sniff = data[:512]
    if sniff.startswith(b"<!") or sniff.startswith(b"<html") or sniff.startswith(b"<HTML"):
        # Try to extract a download URL from the HTML redirect page
        text = data.decode("utf-8", errors="replace")
        redirect_url = _extract_download_url(text, mod_id)
        if redirect_url and redirect_url != url:
            _log.info("Skymods 重定向: %s → %s", url[:80], redirect_url[:80])
            return _download_and_extract(redirect_url, mod_id, config)
        _log.warning("Skymods 返回 HTML 而非 zip (%s): %s", mod_id, text[:200])
        return None

    # Try gzip decompression first (some CDNs apply gzip to zip files)
    if sniff[:2] == b"\x1f\x8b":
        with suppress(OSError):
            data = gzip.decompress(data)

    # Save to temp file
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)

        if not zipfile.is_zipfile(tmp_path):
            _log.warning(
                "Skymods 下载内容不是 zip (%s): 首字节 %s, 大小 %s",
                mod_id,
                sniff[:16].hex(),
                len(data),
            )
            tmp_path.unlink()
            return None

        # Extract to temp directory
        extract_dir = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(tmp_path, "r") as zf:
            zf.extractall(extract_dir)

        mod_folder = _find_mod_folder(extract_dir)
        if not mod_folder:
            _log.warning("Skymods zip 中未找到 Mod 文件夹: %s", mod_id)
            return None

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
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if "extract_dir" in locals() and extract_dir.exists():
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

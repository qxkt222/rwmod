"""Download + retry + copy-to-mods logic — with smart error handling."""

from __future__ import annotations

import logging
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from rwmod.config import Config
from rwmod.steamcmd import DownloadResult, ErrorKind, SteamCMD
from rwmod.utils import extract_mod_id, safe_filename


def _try_broadcast() -> None:
    """Notify WebSocket clients of queue changes, if server is running."""
    try:
        import asyncio

        from rwmod.server import broadcast_queue_update

        asyncio.create_task(broadcast_queue_update())
    except Exception:
        pass


__all__ = ["download_one", "extract_mod_id", "_find_existing", "_pick_folder_name"]

_log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5


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
        return safe_filename(pkg, allow_empty=False)
    name = _read_about_field(workshop_path, "name")
    if name:
        return f"{safe_filename(name, allow_empty=False)}_{mod_id}"
    return f"mod_{mod_id}"


def download_one(config: Config, mod_id: str, force: bool = False) -> bool:
    """Download a single mod. Returns True on success.

    Smart retry: only retries for transient errors (network issues).
    For permanent errors (removed, private, wrong game), skips to Skymods.

    Collection handling: detects collections via Steam Web API BEFORE
    attempting SteamCMD (which cannot download collections). For collections,
    fetches all child mod IDs and recursively downloads each one.
    """
    steamcmd = SteamCMD(config.steamcmd_path)

    existing = _find_existing(config.mods_dir, mod_id)
    if existing:
        if force:
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

    # ── collection detection (Web API, no SteamCMD needed) ──────────
    # SteamCMD cannot download collections — only individual mod files.
    # Detect collections via Steam Web API first and handle them separately.
    try:
        from rwmod.workshop import fetch_collection_children, is_collection

        if is_collection(mod_id):
            _log.info("检测到合集 ID: %s，获取子项...", mod_id)
            children = fetch_collection_children(mod_id)
            if not children:
                _log.warning("合集 %s 为空或无法获取子项", mod_id)
                return False
            _log.info("合集包含 %s 个 Mod，逐个下载...", len(children))
            ok = 0
            fail = 0
            for i, cid in enumerate(children, 1):
                _log.info("[%s/%s] 合集子项 %s", i, len(children), cid)
                if download_one(config, cid, force=force):
                    ok += 1
                else:
                    fail += 1
                _try_broadcast()
            _log.info("合集下载完成: %s 成功, %s 失败, %s 总计", ok, fail, len(children))
            return ok > 0
    except Exception as e:
        # If collection detection fails (network issue), fall through to
        # regular SteamCMD download — it will fail with a clear error too.
        _log.debug("合集检测失败（将尝试常规下载）: %s", e)

    last_result: DownloadResult | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        _log.info("尝试 %s/%s...", attempt, MAX_RETRIES)
        result = steamcmd.workshop_download(mod_id)
        last_result = result

        # Log relevant output lines
        for line in result.output_lines:
            low = line.lower()
            if any(kw in low for kw in ("download", "success", "error", "fail", "item")):
                _log.info("  %s", line)

        if result.success:
            break

        # Permanent errors → no point retrying
        if result.error_kind in ErrorKind.NON_RETRYABLE:
            _log.warning(
                "不可重试错误 [%s]: %s",
                result.error_kind,
                result.error_detail or ErrorKind.explain(result.error_kind),
            )
            break

        # Transient errors → retry
        if attempt < MAX_RETRIES:
            _log.warning("SteamCMD 错误 [%s]，%ss 后重试...", result.error_kind, RETRY_DELAY)
            time.sleep(RETRY_DELAY)

    # ── handle successful download ───────────────────────────────
    if last_result and last_result.success:
        workshop_dir = steamcmd.workshop_content_dir / mod_id
        if not workshop_dir.exists():
            _log.warning("未找到下载内容: %s", mod_id)
            return _skymods_fallback(config, mod_id)

        # Check if this is a collection
        about = workshop_dir / "About" / "About.xml"
        if not about.exists():
            _log.warning("Downloaded content is not a valid mod (no About.xml): %s", mod_id)
            return _skymods_fallback(config, mod_id)

        folder_name = _pick_folder_name(workshop_dir, mod_id)
        dest = config.mods_dir / folder_name
        if dest.exists() and not force:
            _log.info("目标已存在: %s", dest)
            return True
        if dest.exists() and force:
            shutil.rmtree(dest)

        shutil.copytree(workshop_dir, dest)
        _log.info("下载完成: %s", folder_name)
        (dest / ".rwmod_last_updated").write_text(str(int(time.time())))

        # Auto-download dependencies
        _auto_download_deps(config, mod_id, force)
        return True

    # ── handle failure ───────────────────────────────────────────
    if last_result:
        err_msg = last_result.error_detail or ErrorKind.explain(last_result.error_kind)
        _log.error("下载失败: %s — %s", mod_id, err_msg)

    # Only try Skymods if the error is potentially recoverable
    if last_result and last_result.error_kind not in ErrorKind.NON_RETRYABLE:
        return _skymods_fallback(config, mod_id)

    # For non-retryable errors, explain clearly and skip Skymods
    if last_result:
        _log.error(
            "❌ %s (%s): %s — 已跳过 Skymods（错误不可恢复）",
            mod_id,
            last_result.error_kind,
            err_msg,
        )
    else:
        _log.error("❌ %s: 下载失败", mod_id)
    return False


def _skymods_fallback(config: Config, mod_id: str) -> bool:
    """Try Skymods as fallback source."""
    _log.info("尝试 Skymods 备用源...")
    from rwmod.skymods import try_skymods

    result = try_skymods(mod_id, config)
    if result:
        _log.info("Skymods 备用源下载成功: %s → %s", mod_id, result)
        return True
    _log.error("Skymods 备用源也失败: %s", mod_id)
    return False


def _auto_download_deps(config: Config, mod_id: str, force: bool) -> None:
    """Auto-download dependencies for a freshly installed mod."""
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

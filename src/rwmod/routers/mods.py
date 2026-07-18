"""Mods router — listing, health, compatibility, export, collection-export."""

import time
from typing import Any

from fastapi import APIRouter, Depends

from rwmod.config import Config
from rwmod.deps import get_config
from rwmod.metadata import read_mod_metadata
from rwmod.mod_cache import get_cached_mods
from rwmod.workshop import check_mod_updates, fetch_item_details

router = APIRouter(prefix="/api/mods", tags=["mods"])

# ── lightweight in-memory cache ───────────────────────────────────
_mods_cache: dict[str, Any] = {}
_CACHE_TTL = 3  # seconds


def _cached_mod_list(cfg: Config) -> list[dict]:
    now = time.time()
    if _mods_cache and now - _mods_cache.get("_ts", 0) < _CACHE_TTL:
        return _mods_cache["data"]
    if not cfg.mods_dir.exists():
        return []
    metas = get_cached_mods(cfg.mods_dir)
    data = [
        {
            "folder": m.folder,
            "name": m.name,
            "package_id": m.package_id,
            "workshop_id": m.workshop_id,
        }
        for m in metas
    ]
    _mods_cache["data"] = data
    _mods_cache["_ts"] = now
    return data


@router.get("")
def list_mods(cfg: Config = Depends(get_config)):
    return _cached_mod_list(cfg)


@router.get("/check-updates")
def check_updates(cfg: Config = Depends(get_config)):
    return {"updates": check_mod_updates(str(cfg.mods_dir))}


# ── health cache (expensive — hits Steam API for 600+ mods) ───────
_health_cache: dict[str, Any] = {}
_HEALTH_CACHE_TTL = 60  # 1 minute — Steam API data changes slowly


@router.get("/health")
def mod_health(cfg: Config = Depends(get_config)):
    now = time.time()
    if _health_cache and now - _health_cache.get("_ts", 0) < _HEALTH_CACHE_TTL:
        return _health_cache["data"]

    if not cfg.mods_dir.exists():
        return {"mods": []}
    metas = [
        m
        for m in (read_mod_metadata(d) for d in sorted(cfg.mods_dir.iterdir()))
        if m and m.workshop_id
    ]
    all_ids = [m.workshop_id for m in metas]
    details = fetch_item_details(all_ids)
    results = []
    for meta in metas:
        remote = details.get(meta.workshop_id)
        if remote:
            age = (now - remote.get("time_updated", 0)) / 86400
            status = "maintained" if age < 90 else "stale" if age < 365 else "abandoned"
            last_updated = time.strftime("%Y-%m-%d", time.gmtime(remote["time_updated"]))
        else:
            status, last_updated = "removed", ""
        results.append(
            {
                "folder": meta.folder,
                "name": meta.name,
                "workshop_id": meta.workshop_id,
                "status": status,
                "last_updated": last_updated,
            }
        )
    data = {"mods": results}
    _health_cache["data"] = data
    _health_cache["_ts"] = now
    return data


@router.get("/export")
def export_mods(cfg: Config = Depends(get_config)):
    from datetime import datetime

    if not cfg.mods_dir.exists():
        return {"mods": []}
    mods = []
    for d in sorted(cfg.mods_dir.iterdir()):
        meta = read_mod_metadata(d)
        if meta:
            mods.append(
                {
                    "folder": meta.folder,
                    "name": meta.name,
                    "package_id": meta.package_id,
                    "workshop_id": meta.workshop_id,
                }
            )
    return {"exported_at": datetime.now().isoformat(), "total": len(mods), "mods": mods}


@router.get("/export-collection")
def export_collection(cfg: Config = Depends(get_config)):
    metas = get_cached_mods(cfg.mods_dir)
    mods = []
    ids_only: list[str] = []
    for m in metas:
        if m.workshop_id:
            url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={m.workshop_id}"
            mods.append({"workshop_id": m.workshop_id, "name": m.name, "url": url})
            ids_only.append(m.workshop_id)
    header = f"# RimWorld Mod 合集 — {len(mods)} 个 Mod"
    lines = [header, "", "## Workshop ID 列表", "", " ".join(ids_only), ""]
    return {"total": len(mods), "mods": mods, "ids": ids_only, "markdown": "\n".join(lines)}


@router.get("/compatibility")
def mod_compatibility(cfg: Config = Depends(get_config)):
    from rwmod.compatibility import check_compatibility, detect_rimworld_version

    rw_ver = detect_rimworld_version(cfg.rimworld_dir)
    if not rw_ver:
        return {"error": "未能检测到 RimWorld 版本", "rimworld_version": None, "groups": {}}
    metas = get_cached_mods(cfg.mods_dir)
    groups = check_compatibility(metas, rw_ver)
    return {"rimworld_version": rw_ver, "groups": groups}

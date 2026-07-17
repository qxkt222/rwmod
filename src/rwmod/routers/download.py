"""Download + import routers."""

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from rwmod.config import Config
from rwmod.database import record_download
from rwmod.deps import get_config
from rwmod.downloader import _find_existing, download_one, extract_mod_id
from rwmod.logger import get_log
from rwmod.parser import (
    get_installed_package_ids,
    parse_modlist_file,
    parse_mods_config,
    resolve_workshop_ids,
)
from rwmod.workshop import fetch_collection_children, is_collection

router = APIRouter(prefix="/api", tags=["download"])
_log = get_log("rwmod.server")


@router.post("/download")
async def download_mods(payload: dict, cfg: Config = Depends(get_config)):
    ids: list[str] = payload.get("ids", [])
    force: bool = payload.get("force", False)
    parsed = [mid for raw in ids if (mid := extract_mod_id(raw))]
    if not parsed:
        raise HTTPException(400, "没有有效的 Mod ID")
    cfg.validate()
    results: list[dict] = []
    for mid in parsed:
        ok = download_one(cfg, mid, force=force)
        results.append({"id": mid, "ok": ok})
        status = "success" if ok else "failed"
        record_download(mid, status)
        _log.info("download %s → %s", mid, status)
    return {"total": len(results), "results": results}


@router.get("/download/stream")
async def download_stream(id: str, force: bool = False, cfg: Config = Depends(get_config)):
    mid = extract_mod_id(id)
    if not mid:
        raise HTTPException(400, "无效的 Mod ID")
    cfg.validate()

    async def event_stream():
        yield f"data: {_sse_event('start', id=mid)}\n\n"
        if is_collection(mid):
            yield f"data: {_sse_event('info', msg='检测到合集，通过 Web API 获取内容...')}\n\n"
            collection_ids = fetch_collection_children(mid)
            if not collection_ids:
                yield f"data: {_sse_event('warn', msg='未能获取合集内容')}\n\n"
                yield f"data: {_sse_event('done', id=mid)}\n\n"
                return
            yield f"data: {_sse_event('info', msg=f'合集包含 {len(collection_ids)} 个 Mod，逐个下载中...')}\n\n"
            to_download: list[str] = []
            skip = 0
            for cid in collection_ids:
                existing = _find_existing(cfg.mods_dir, cid)
                if existing and not force:
                    yield f"data: {_sse_event('skip', msg=f'  {cid} — 已安装: {existing.name}')}\n\n"
                    skip += 1
                else:
                    to_download.append(cid)
            if skip:
                yield f"data: {_sse_event('info', msg=f'{skip} 个已安装，跳过；{len(to_download)} 个待下载')}\n\n"
            ok = 0
            fail = 0
            for i, cid in enumerate(to_download, 1):
                yield f"data: {_sse_event('info', msg=f'[{i}/{len(to_download)}] 下载 {cid}...')}\n\n"
                if download_one(cfg, cid, force=force):
                    ok += 1
                    yield f"data: {_sse_event('info', msg=f'  ✓ {cid}')}\n\n"
                else:
                    fail += 1
                    yield f"data: {_sse_event('warn', msg=f'  ✗ {cid} 失败')}\n\n"
                await asyncio.sleep(0)
            yield f"data: {_sse_event('ok', msg=f'合集完成: {ok} 下载, {skip} 跳过, {fail} 失败')}\n\n"
            yield f"data: {_sse_event('done', id=mid)}\n\n"
            return

        existing = _find_existing(cfg.mods_dir, mid)
        if existing and not force:
            yield f"data: {_sse_event('skip', msg=f'已安装: {existing.name}')}\n\n"
            yield f"data: {_sse_event('done', id=mid)}\n\n"
            return
        if existing and force:
            yield f"data: {_sse_event('info', msg=f'覆盖已有 mod: {existing.name}')}\n\n"
        ok = await asyncio.to_thread(download_one, cfg, mid, force=force)
        if ok:
            final = _find_existing(cfg.mods_dir, mid)
            name = final.name if final else mid
            yield f"data: {_sse_event('ok', msg=f'✓ {name}', id=mid)}\n\n"
            record_download(mid, "success", mod_name=name)
        else:
            yield f"data: {_sse_event('fail', msg='下载失败（含 Skymods 备用源）', id=mid)}\n\n"
            record_download(mid, "failed")
        yield f"data: {_sse_event('done', id=mid)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/import/file")
async def import_file(
    file: UploadFile = File(...), force: bool = False, cfg: Config = Depends(get_config)
):
    cfg.validate()
    content = (await file.read()).decode("utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    try:
        ids = parse_modlist_file(Path(tmp))
        results = [{"id": mid, "ok": download_one(cfg, mid, force=force)} for mid in ids]
        return {"total": len(results), "results": results}
    finally:
        Path(tmp).unlink(missing_ok=True)


@router.post("/import/collection")
async def import_collection_api(payload: dict, cfg: Config = Depends(get_config)):
    raw_id = payload.get("collection_id", "")
    collection_id = extract_mod_id(raw_id)
    force: bool = payload.get("force", False)
    if not collection_id:
        raise HTTPException(400, f"无效的合集 ID: {raw_id}")
    cfg.validate()
    mod_ids = fetch_collection_children(collection_id)
    if not mod_ids:
        raise HTTPException(404, "未能获取合集内容")
    _log.info("合集 %s 包含 %s 个 Mod", collection_id, len(mod_ids))
    results = [{"id": mid, "ok": download_one(cfg, mid, force=force)} for mid in mod_ids]
    return {"total": len(results), "results": results}


@router.post("/import/sort")
async def import_sort_api(
    file: UploadFile = File(...), force: bool = False, cfg: Config = Depends(get_config)
):
    cfg.validate()
    content = await file.read()
    with tempfile.NamedTemporaryFile("wb", suffix=".xml", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        package_ids = parse_mods_config(Path(tmp))
        installed = get_installed_package_ids(cfg.mods_dir)
        missing = [pid for pid in package_ids if pid not in installed]
        known, unknown = resolve_workshop_ids(missing, cfg.mods_dir)
        results = [{"id": mid, "ok": download_one(cfg, mid, force=force)} for mid in known]
        return {
            "total_packages": len(package_ids),
            "missing": len(missing),
            "unknown": unknown,
            "downloaded": len(results),
            "results": results,
        }
    finally:
        Path(tmp).unlink(missing_ok=True)


def _sse_event(event: str, **kwargs) -> str:
    import json

    return json.dumps({"event": event, **kwargs}, ensure_ascii=False)

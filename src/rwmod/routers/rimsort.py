"""RimSort router."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from rwmod.config import Config
from rwmod.deps import get_config
from rwmod.rimsort import compare_modsconfig, generate_modsconfig, resolve_missing_workshop_ids

router = APIRouter(prefix="/api/rimsort", tags=["rimsort"])


@router.post("/generate")
def rimsort_generate(cfg: Config = Depends(get_config)):
    return {"modsconfig_xml": generate_modsconfig(cfg.mods_dir)}


@router.post("/compare")
def rimsort_compare(payload: dict, cfg: Config = Depends(get_config)):
    xml_content = payload.get("xml", "")
    if not xml_content.strip():
        raise HTTPException(400, "需要提供 ModsConfig.xml 内容")
    with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
        f.write(xml_content)
        tmp = f.name
    try:
        result = compare_modsconfig(Path(tmp), cfg.mods_dir)
        if result.get("missing"):
            result["missing_details"] = resolve_missing_workshop_ids(
                result["missing"], cfg.mods_dir
            )
        return result
    finally:
        Path(tmp).unlink(missing_ok=True)


@router.post("/compare-file")
async def rimsort_compare_file(file: UploadFile = File(...), cfg: Config = Depends(get_config)):
    content = await file.read()
    with tempfile.NamedTemporaryFile("wb", suffix=".xml", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        result = compare_modsconfig(Path(tmp), cfg.mods_dir)
        if result.get("missing"):
            result["missing_details"] = resolve_missing_workshop_ids(
                result["missing"], cfg.mods_dir
            )
        return result
    finally:
        Path(tmp).unlink(missing_ok=True)


@router.get("/check-order")
def check_load_order(cfg: Config = Depends(get_config)):
    from rwmod.load_order import check_load_order as _check
    from rwmod.profile import resolve_modsconfig_path

    path = resolve_modsconfig_path(cfg.rimworld_dir) or (cfg.rimworld_dir / "ModsConfig.xml")
    return _check(path, cfg.mods_dir)

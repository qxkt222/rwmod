"""Save file analysis router \u2014 parse .rws files to detect mod requirements."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from rwmod.config import Config
from rwmod.deps import get_config
from rwmod.parser import get_installed_package_ids
from rwmod.save_parser import analyze_save, find_save_files, parse_save_mods

router = APIRouter(prefix="/api/saves", tags=["saves"])


@router.get("")
def list_saves(cfg: Config = Depends(get_config)):
    """List all found save files with basic analysis."""
    saves = find_save_files(cfg.rimworld_dir)
    installed = get_installed_package_ids(cfg.mods_dir)
    results = []
    for sp in saves[:50]:
        analysis = analyze_save(sp, installed)
        results.append({
            "name": analysis["name"],
            "game_version": analysis["game_version"],
            "total_mods": analysis["total_mods"],
            "missing_count": len(analysis["missing_mods"]),
            "loadable": analysis["loadable"],
            "completeness": analysis["completeness"],
        })
    return {"saves": results}


@router.get("/{save_name}")
def save_detail(save_name: str, cfg: Config = Depends(get_config)):
    """Analyze a specific save file in detail."""
    saves = find_save_files(cfg.rimworld_dir)
    target = next((sp for sp in saves if sp.stem == save_name or sp.name == save_name), None)
    if target is None:
        return {"error": f"Save not found: {save_name}"}
    installed = get_installed_package_ids(cfg.mods_dir)
    return analyze_save(target, installed)


@router.post("/analyze")
async def api_upload_and_analyze(file: UploadFile):
    """Upload a .rws save file and get its mod requirements."""
    try:
        content = (await file.read()).decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(400, f"Cannot read file: {e}") from e
    try:
        mods = parse_save_mods(content)
        return {"filename": file.filename, "mods": mods, "mod_count": len(mods)}
    except Exception as e:
        raise HTTPException(400, f"Failed to parse save: {e}") from e

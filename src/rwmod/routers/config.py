"""Config router."""

from fastapi import APIRouter, Depends

from rwmod.config import Config
from rwmod.deps import get_config

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
def get_config_route(cfg: Config = Depends(get_config)):
    return {
        "steamcmd_path": str(cfg.steamcmd_path),
        "mods_dir": str(cfg.mods_dir),
        "rimworld_dir": str(cfg.rimworld_dir),
        "backup_dir": str(cfg.backup_dir),
        "steamcmd_exists": cfg.steamcmd_path.exists(),
        "mods_dir_exists": cfg.mods_dir.exists(),
    }


@router.post("/config")
def update_config(payload: dict, cfg: Config = Depends(get_config)):
    if "steamcmd_path" in payload:
        cfg.steamcmd_path = Path(payload["steamcmd_path"])
    if "mods_dir" in payload:
        cfg.mods_dir = Path(payload["mods_dir"])
    if "rimworld_dir" in payload:
        cfg.rimworld_dir = Path(payload["rimworld_dir"])
    if "backup_dir" in payload:
        cfg.backup_dir = Path(payload["backup_dir"])
    cfg.save()
    return {"ok": True}


from pathlib import Path

"""Profiles router."""

from fastapi import APIRouter, Depends, HTTPException

from rwmod.config import Config
from rwmod.deps import get_config

router = APIRouter(prefix="/api", tags=["profiles"])


@router.get("/profiles")
def list_profiles(cfg: Config = Depends(get_config)):
    from rwmod.profile import list_profiles as _list
    from rwmod.profile import resolve_modsconfig_path

    return {
        "profiles": _list(),
        "modsconfig_path": str(path)
        if (path := resolve_modsconfig_path(cfg.rimworld_dir))
        else None,
    }


@router.post("/profiles/save")
def save_profile(payload: dict, cfg: Config = Depends(get_config)):
    name: str = payload.get("name", "").strip()
    if not name:
        raise HTTPException(400, "需要提供 profile 名称")
    from rwmod.profile import resolve_modsconfig_path
    from rwmod.profile import save_profile as _save

    source = resolve_modsconfig_path(cfg.rimworld_dir)
    if not source:
        from rwmod.rimsort import generate_modsconfig

        return _save(name, generate_modsconfig(cfg.mods_dir))
    return _save(name, source)


@router.post("/profiles/{name}/restore")
def restore_profile(name: str, cfg: Config = Depends(get_config)):
    from rwmod.profile import resolve_modsconfig_path
    from rwmod.profile import restore_profile as _restore

    target = resolve_modsconfig_path(cfg.rimworld_dir) or (cfg.rimworld_dir / "ModsConfig.xml")
    return _restore(name, target)


@router.delete("/profiles/{name}")
def delete_profile(name: str):
    from rwmod.profile import delete_profile as _delete

    return {"ok": _delete(name)}

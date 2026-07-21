"""Tags router \u2014 API for managing mod tags/categories."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from rwmod.tags import (
    add_tag,
    get_mods_by_tag,
    get_tags,
    list_all_tags,
    remove_all_tags,
    remove_tag,
)

router = APIRouter(prefix="/api", tags=["tags"])


@router.get("/tags")
def api_list_all_tags():
    """List all tags with mod counts."""
    return {"tags": list_all_tags()}


@router.get("/tags/by-tag/{tag}")
def api_get_mods_by_tag(tag: str):
    """List all mods with a given tag."""
    return {"tag": tag, "folders": get_mods_by_tag(tag)}


@router.get("/tags/{mod_folder}")
def api_get_mod_tags(mod_folder: str):
    """Get all tags for a specific mod folder."""
    return {"folder": mod_folder, "tags": get_tags(mod_folder)}


@router.post("/tags/{mod_folder}")
def api_add_tag(mod_folder: str, payload: dict):
    """Add a tag to a mod."""
    tag = payload.get("tag", "").strip()
    if not tag:
        raise HTTPException(400, "Tag is required")
    ok = add_tag(mod_folder, tag)
    return {"ok": ok, "tag": tag, "folder": mod_folder}


@router.delete("/tags/{mod_folder}/{tag}")
def api_remove_tag(mod_folder: str, tag: str):
    """Remove a tag from a mod."""
    ok = remove_tag(mod_folder, tag)
    return {"ok": ok}


@router.delete("/tags/{mod_folder}")
def api_remove_all_tags(mod_folder: str):
    """Remove all tags from a mod."""
    count = remove_all_tags(mod_folder)
    return {"ok": True, "removed": count}

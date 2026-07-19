"""Pydantic response/request models — shared across all routers.

All schemas live here. models/__init__.py re-exports for backward compat.
"""

from __future__ import annotations

from pydantic import BaseModel

# ── generic ────────────────────────────────────────────────────────


class OkResponse(BaseModel):
    ok: bool = True


class ErrorResponse(BaseModel):
    detail: str


# ── config ─────────────────────────────────────────────────────────


class ConfigResponse(BaseModel):
    steamcmd_path: str
    mods_dir: str
    rimworld_dir: str
    backup_dir: str
    steamcmd_exists: bool
    mods_dir_exists: bool


# ── download ───────────────────────────────────────────────────────


class DownloadRequest(BaseModel):
    ids: list[str]
    force: bool = False


class DownloadResultItem(BaseModel):
    id: str
    ok: bool

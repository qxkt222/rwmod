"""Pydantic models — shared request/response schemas for all routers.

Replaces raw dict returns with typed, documented models.
FastAPI auto-generates OpenAPI docs from these.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── generic ────────────────────────────────────────────────────────


class OkResponse(BaseModel):
    """Generic success response."""

    ok: bool = True


class ErrorResponse(BaseModel):
    """Generic error response."""

    detail: str


# ── config ─────────────────────────────────────────────────────────


class ConfigResponse(BaseModel):
    steamcmd_path: str
    mods_dir: str
    rimworld_dir: str
    backup_dir: str
    steamcmd_exists: bool
    mods_dir_exists: bool


class ConfigUpdateRequest(BaseModel):
    steamcmd_path: str | None = None
    mods_dir: str | None = None
    rimworld_dir: str | None = None
    backup_dir: str | None = None


# ── mods ───────────────────────────────────────────────────────────


class ModEntry(BaseModel):
    folder: str
    name: str
    package_id: str = ""
    workshop_id: str = ""


class ModHealthEntry(BaseModel):
    folder: str
    name: str
    workshop_id: str
    status: str  # maintained | stale | abandoned | removed
    last_updated: str = ""


class ModHealthResponse(BaseModel):
    mods: list[ModHealthEntry]


class ModExportEntry(BaseModel):
    folder: str
    name: str
    package_id: str
    workshop_id: str


class ModExportResponse(BaseModel):
    exported_at: str
    total: int
    mods: list[ModExportEntry]


class ModCollectionExportResponse(BaseModel):
    total: int
    ids: list[str]
    markdown: str


class CompatibilityEntry(BaseModel):
    folder: str
    name: str
    workshop_id: str
    supported: list[str] = Field(default_factory=list)


class CompatibilityResponse(BaseModel):
    rimworld_version: str | None
    groups: dict[str, list[CompatibilityEntry]]


class ModCheckUpdatesResponse(BaseModel):
    updates: list[dict]


# ── download ───────────────────────────────────────────────────────


class DownloadRequest(BaseModel):
    ids: list[str]
    force: bool = False


class DownloadResultItem(BaseModel):
    id: str
    ok: bool


class DownloadResponse(BaseModel):
    total: int
    results: list[DownloadResultItem]


class CollectionImportRequest(BaseModel):
    collection_id: str
    force: bool = False


class SortImportResponse(BaseModel):
    total_packages: int
    missing: int
    unknown: list[str]
    downloaded: int
    results: list[DownloadResultItem]


# ── dashboard ──────────────────────────────────────────────────────


class RecentActivityEntry(BaseModel):
    workshop_id: str
    mod_name: str = ""
    status: str
    created_at: str = ""


class DashboardResponse(BaseModel):
    mods_count: int
    updates_pending: int
    disk_usage_mb: float
    recent_activity: list[RecentActivityEntry]


# ── queue ──────────────────────────────────────────────────────────


class QueueItemResponse(BaseModel):
    id: str
    name: str = ""
    status: str  # pending | downloading | done | failed | cancelled
    progress: float = 0.0
    msg: str = ""


class QueueSnapshotResponse(BaseModel):
    items: list[QueueItemResponse]


class QueueAddRequest(BaseModel):
    ids: list[str]


class QueueAddResponse(BaseModel):
    added: int


class QueueClearResponse(BaseModel):
    ok: bool = True


# ── workshop ───────────────────────────────────────────────────────


class WorkshopSearchResult(BaseModel):
    id: str
    title: str
    author: str
    description: str = ""
    preview_url: str = ""
    installed: bool = False


class SearchResponse(BaseModel):
    results: list[WorkshopSearchResult]


class DependencyItem(BaseModel):
    id: str
    name: str
    installed: bool


class DependenciesRequest(BaseModel):
    ids: list[str]


class DependenciesResponse(BaseModel):
    deps: dict[str, list[DependencyItem]]


class CollectionPreviewResponse(BaseModel):
    collection_id: str
    total: int
    installed_count: int
    new_count: int
    failed_count: int
    installed: list[dict]
    new_mods: list[str]
    failed_before: list[str]


# ── auth ───────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int = 604800


class AuthVerifyResponse(BaseModel):
    user: str
    valid: bool


# ── auto-update ────────────────────────────────────────────────────


class AutoUpdateStatusResponse(BaseModel):
    running: bool


class AutoUpdateResultResponse(BaseModel):
    updates: list[dict]


class AutoUpdateRunResponse(BaseModel):
    checked: int
    outdated: int
    queued: int


# ── history ────────────────────────────────────────────────────────


class HistoryItem(BaseModel):
    id: int
    workshop_id: str
    mod_name: str = ""
    status: str
    msg: str = ""
    created_at: str = ""


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class HistoryStatsResponse(BaseModel):
    total: int
    success: int
    failed: int


# ── backups ────────────────────────────────────────────────────────


class BackupEntry(BaseModel):
    filename: str
    workshop_id: str
    folder_name: str
    timestamp: str = ""
    size_mb: float = 0.0


class BackupListResponse(BaseModel):
    backups: list[BackupEntry]


# ── profiles ───────────────────────────────────────────────────────


class ProfileEntry(BaseModel):
    name: str
    mod_count: int = 0
    saved_at: str = ""
    size_kb: float = 0.0


class ProfileListResponse(BaseModel):
    profiles: list[ProfileEntry]
    modsconfig_path: str | None = None


class ProfileSaveRequest(BaseModel):
    name: str


# ── status ─────────────────────────────────────────────────────────


class StatusResponse(BaseModel):
    online: bool
    last_check_ago_sec: float = 0

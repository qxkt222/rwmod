"""Pydantic response/request models — shared across all routers.

Legacy models kept for backward compatibility. New schemas in schemas.py.
All schemas are re-exported via __all__ so linters recognize them as public API.
"""

from __future__ import annotations

from pydantic import BaseModel

from rwmod.models.schemas import (
    AuthVerifyResponse,
    AutoUpdateRunResponse,
    AutoUpdateStatusResponse,
    BackupEntry,
    BackupListResponse,
    CollectionImportRequest,
    CollectionPreviewResponse,
    CompatibilityResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    DashboardResponse,
    DependenciesRequest,
    DependenciesResponse,
    DownloadRequest,
    DownloadResponse,
    DownloadResultItem,
    HistoryResponse,
    LoginRequest,
    LoginResponse,
    ModCheckUpdatesResponse,
    ModCollectionExportResponse,
    ModEntry,
    ModExportResponse,
    ModHealthEntry,
    ModHealthResponse,
    ProfileListResponse,
    ProfileSaveRequest,
    QueueAddRequest,
    QueueAddResponse,
    QueueClearResponse,
    QueueItemResponse,
    QueueSnapshotResponse,
    SearchResponse,
    SortImportResponse,
    StatusResponse,
)

# ── legacy models (used by existing code) ──────────────────────────


class OkResponse(BaseModel):
    ok: bool = True


class ErrorResponse(BaseModel):
    detail: str


__all__ = [
    # legacy
    "OkResponse",
    "ErrorResponse",
    # config
    "ConfigResponse",
    "ConfigUpdateRequest",
    # mods
    "ModEntry",
    "ModHealthEntry",
    "ModHealthResponse",
    "ModExportResponse",
    "ModCollectionExportResponse",
    "CompatibilityResponse",
    "ModCheckUpdatesResponse",
    # download
    "DownloadRequest",
    "DownloadResponse",
    "DownloadResultItem",
    "CollectionImportRequest",
    "SortImportResponse",
    # dashboard
    "DashboardResponse",
    # queue
    "QueueItemResponse",
    "QueueSnapshotResponse",
    "QueueAddRequest",
    "QueueAddResponse",
    "QueueClearResponse",
    # workshop
    "SearchResponse",
    "DependenciesRequest",
    "DependenciesResponse",
    "CollectionPreviewResponse",
    # auth
    "LoginRequest",
    "LoginResponse",
    "AuthVerifyResponse",
    # auto-update
    "AutoUpdateStatusResponse",
    "AutoUpdateRunResponse",
    # history
    "HistoryResponse",
    # backups
    "BackupEntry",
    "BackupListResponse",
    # profiles
    "ProfileListResponse",
    "ProfileSaveRequest",
    # status
    "StatusResponse",
]

"""Unified exception hierarchy for rwmod.

All business-logic exceptions inherit from RwmodError.
The global error middleware in server.py maps them to HTTP status codes.
"""

from __future__ import annotations


class RwmodError(Exception):
    """Base exception for all rwmod errors."""

    status_code: int = 500
    detail: str = "内部错误"


class ConfigError(RwmodError):
    """Configuration validation failure."""

    status_code = 400
    detail = "配置错误"


class SteamCmdError(RwmodError):
    """SteamCMD execution failure."""

    status_code = 502
    detail = "SteamCMD 执行失败"


class WorkshopError(RwmodError):
    """Steam Workshop API failure or invalid data."""

    status_code = 502
    detail = "Workshop API 错误"


class ModNotFoundError(RwmodError):
    """Mod not found (workshop or local)."""

    status_code = 404
    detail = "Mod 未找到"


class DownloadError(RwmodError):
    """Mod download failure after all retries and fallbacks."""

    status_code = 502
    detail = "下载失败"


class ValidationError(RwmodError):
    """Invalid input or request payload."""

    status_code = 400
    detail = "输入无效"


class ConflictError(RwmodError):
    """Resource conflict (e.g., already running, duplicate)."""

    status_code = 409
    detail = "资源冲突"

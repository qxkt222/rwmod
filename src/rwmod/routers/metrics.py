"""Prometheus metrics — exposes /metrics endpoint for Grafana dashboards.

Tracks: request counts by endpoint, latencies, error rates, queue depth,
mod count, and Steam API connectivity. All metrics use the Prometheus
text exposition format for direct Grafana consumption.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["metrics"])

# ── metrics state ──────────────────────────────────────────────────
_start_time = time.time()

# Per-endpoint: { "GET /api/mods": {"count": N, "total_ms": float, "errors": N} }
_request_stats: dict[str, dict] = defaultdict(lambda: {"count": 0, "total_ms": 0.0, "errors": 0})

# Active operations
_active_downloads: int = 0
_mod_count: int = 0
_disk_usage_mb: float = 0.0
_steam_online: bool = True
_queue_depth: int = 0


def record_request(request: Request, status_code: int, elapsed_ms: float) -> None:
    """Record request metrics. Called from server middleware."""
    key = f"{request.method} {request.url.path}"
    stats = _request_stats[key]
    stats["count"] += 1
    stats["total_ms"] += elapsed_ms
    if status_code >= 400:
        stats["errors"] += 1


def set_gauge(key: str, value: float | bool | int) -> None:
    """Set gauge values from app modules."""
    global _active_downloads, _mod_count, _disk_usage_mb, _steam_online, _queue_depth
    if key == "active_downloads":
        _active_downloads = int(value)
    elif key == "mod_count":
        _mod_count = int(value)
    elif key == "disk_usage_mb":
        _disk_usage_mb = float(value)
    elif key == "steam_online":
        _steam_online = bool(value)
    elif key == "queue_depth":
        _queue_depth = int(value)


@router.get("/metrics")
def metrics():
    """Prometheus-compatible metrics endpoint."""
    uptime = time.time() - _start_time
    lines = [
        "# HELP rwmod_uptime_seconds Server uptime in seconds",
        "# TYPE rwmod_uptime_seconds gauge",
        f"rwmod_uptime_seconds {uptime:.1f}",
        "",
        "# HELP rwmod_requests_total Total requests by endpoint",
        "# TYPE rwmod_requests_total counter",
    ]
    for key, stats in sorted(_request_stats.items()):
        method, path = key.split(" ", 1)
        lines.append(f'rwmod_requests_total{{method="{method}",path="{path}"}} {stats["count"]}')

    lines.extend(
        [
            "",
            "# HELP rwmod_request_duration_ms_total Total request duration by endpoint",
            "# TYPE rwmod_request_duration_ms_total counter",
        ]
    )
    for key, stats in sorted(_request_stats.items()):
        method, path = key.split(" ", 1)
        lines.append(
            f'rwmod_request_duration_ms_total{{method="{method}",path="{path}"}} {stats["total_ms"]:.0f}'
        )

    lines.extend(
        [
            "",
            "# HELP rwmod_errors_total Error responses (4xx/5xx) by endpoint",
            "# TYPE rwmod_errors_total counter",
        ]
    )
    for key, stats in sorted(_request_stats.items()):
        if stats["errors"] > 0:
            method, path = key.split(" ", 1)
            lines.append(f'rwmod_errors_total{{method="{method}",path="{path}"}} {stats["errors"]}')

    lines.extend(
        [
            "",
            "# HELP rwmod_active_downloads Currently active downloads",
            "# TYPE rwmod_active_downloads gauge",
            f"rwmod_active_downloads {_active_downloads}",
            "",
            "# HELP rwmod_mod_count Installed mod count",
            "# TYPE rwmod_mod_count gauge",
            f"rwmod_mod_count {_mod_count}",
            "",
            "# HELP rwmod_disk_usage_mb Mod directory disk usage in MB",
            "# TYPE rwmod_disk_usage_mb gauge",
            f"rwmod_disk_usage_mb {_disk_usage_mb:.1f}",
            "",
            "# HELP rwmod_queue_depth Pending + downloading queue items",
            "# TYPE rwmod_queue_depth gauge",
            f"rwmod_queue_depth {_queue_depth}",
            "",
            "# HELP rwmod_steam_api_up Steam API reachable (1=yes, 0=no)",
            "# TYPE rwmod_steam_api_up gauge",
            f"rwmod_steam_api_up {1 if _steam_online else 0}",
        ]
    )

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")

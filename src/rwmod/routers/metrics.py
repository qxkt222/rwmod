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



def record_request(request: Request, status_code: int, elapsed_ms: float) -> None:
    """Record request metrics. Called from server middleware."""
    key = f"{request.method} {request.url.path}"
    stats = _request_stats[key]
    stats["count"] += 1
    stats["total_ms"] += elapsed_ms
    if status_code >= 400:
        stats["errors"] += 1


_GAUGE_TYPES = {
    "active_downloads": int,
    "mod_count": int,
    "disk_usage_mb": float,
    "steam_online": bool,
    "queue_depth": int,
}

_GAUGE_STORE: dict[str, float | bool | int] = {
    "active_downloads": 0,
    "mod_count": 0,
    "disk_usage_mb": 0.0,
    "steam_online": True,
    "queue_depth": 0,
}


def set_gauge(key: str, value: float | bool | int) -> None:
    """Set gauge values from app modules."""
    if cast := _GAUGE_TYPES.get(key):
        _GAUGE_STORE[key] = cast(value)


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

    gauges = [
        ("rwmod_active_downloads", "Currently active downloads", "gauge", _GAUGE_STORE["active_downloads"]),
        ("rwmod_mod_count", "Installed mod count", "gauge", _GAUGE_STORE["mod_count"]),
        ("rwmod_disk_usage_mb", "Mod directory disk usage in MB", "gauge", f"{_GAUGE_STORE['disk_usage_mb']:.1f}"),
        ("rwmod_queue_depth", "Pending + downloading queue items", "gauge", _GAUGE_STORE["queue_depth"]),
        ("rwmod_steam_api_up", "Steam API reachable (1=yes, 0=no)", "gauge", 1 if _GAUGE_STORE["steam_online"] else 0),
    ]
    for name, help_text, mtype, value in gauges:
        lines.extend(["", f"# HELP {name} {help_text}", f"# TYPE {name} {mtype}", f"{name} {value}"])

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")

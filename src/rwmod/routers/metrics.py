"""Prometheus metrics — exposes /metrics endpoint for Grafana dashboards."""

from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["metrics"])

# In-memory counters (thread-safe for single-worker uvicorn)
_start_time = time.time()
_request_count: dict[str, int] = {}
_last_error: dict[str, str] = {}


def record_request(method: str, path: str, status: int, elapsed_ms: float) -> None:
    """Called from server middleware to track metrics."""
    key = f"{method} {path}"
    _request_count[key] = _request_count.get(key, 0) + 1
    if status >= 500:
        _last_error[key] = f"{status} ({elapsed_ms:.0f}ms)"


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
    for key, count in _request_count.items():
        method, path = key.split(" ", 1)
        lines.append(f'rwmod_requests_total{{method="{method}",path="{path}"}} {count}')

    if _last_error:
        lines.append("")
        lines.append("# HELP rwmod_last_error Last 5xx error per endpoint")
        lines.append("# TYPE rwmod_last_error gauge")
        for key, err in _last_error.items():
            method, path = key.split(" ", 1)
            lines.append(f'rwmod_last_error{{method="{method}",path="{path}",error="{err}"}} 1')

    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain")

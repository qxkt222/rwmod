"""rwmod Web Server — FastAPI app factory.

This is the top-level entry point. All routes are organized in
src/rwmod/routers/ by domain concern (mods, downloads, backups, etc.).
Dependencies (config, DB, queue) are injected via src/rwmod/deps.py.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from rwmod.database import close_db, init_db
from rwmod.deps import get_autoupdate
from rwmod.errors import RwmodError
from rwmod.logger import get_log, init_logging
from rwmod.queue import get_queue

# ── routers ────────────────────────────────────────────────────────
from rwmod.routers.auth import router as auth_router
from rwmod.routers.auto_update import router as autoupdate_router
from rwmod.routers.backups import router as backups_router
from rwmod.routers.config import router as config_router
from rwmod.routers.dashboard import router as dashboard_router
from rwmod.routers.download import router as download_router
from rwmod.routers.health import router as health_router
from rwmod.routers.history import router as history_router
from rwmod.routers.metrics import record_request, set_gauge
from rwmod.routers.metrics import router as metrics_router
from rwmod.routers.mods import router as mods_router
from rwmod.routers.profiles import router as profiles_router
from rwmod.routers.queue import router as queue_router
from rwmod.routers.rimsort import router as rimsort_router
from rwmod.routers.saves import router as saves_router
from rwmod.routers.tags import router as tags_router
from rwmod.routers.workshop import router as workshop_router

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

init_logging()
_log = get_log("rwmod.server")
_log.info("Server starting — log: %s", Path.home() / ".rwmod.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    au = get_autoupdate()
    await au.start_background()
    set_gauge("steam_online", True)
    # Seed app state (future: migrate singletons here)
    from rwmod.app_state import AppState
    app.state.rwmod = AppState()
    yield
    await au.stop_background()
    close_db()


app = FastAPI(
    title="rwmod Web",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# ── middleware ─────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_tracing(request: Request, call_next):
    """Add X-Request-ID + log timing + record metrics."""
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = req_id

    flag = " ⚠ SLOW" if elapsed_ms > 500 else ""
    _log.info(
        "[%s] %s %s → %s (%sms)%s",
        req_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        flag,
    )

    record_request(request, response.status_code, elapsed_ms)
    return response


# ── global error handler ───────────────────────────────────────────


@app.exception_handler(RwmodError)
async def rwmod_error_handler(request: Request, exc: RwmodError):
    """Map all RwmodError subclasses to structured JSON responses."""
    _log.warning("%s %s → %s: %s", request.method, request.url.path, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def catchall_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions — log full traceback, return 500."""
    _log.error("未处理异常: %s %s — %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "InternalError", "detail": "内部服务器错误"},
    )


# ── routers ────────────────────────────────────────────────────────
# Order: auth first (login doesn't need auth), then functional routes
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(config_router)
app.include_router(dashboard_router)
app.include_router(mods_router)
app.include_router(download_router)
app.include_router(workshop_router)
app.include_router(queue_router)
app.include_router(backups_router)
app.include_router(profiles_router)
app.include_router(rimsort_router)
app.include_router(history_router)
app.include_router(autoupdate_router)
app.include_router(metrics_router)
app.include_router(tags_router)
app.include_router(saves_router)


# ── static files ───────────────────────────────────────────────────
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ── WebSocket ─────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """WebSocket for real-time status updates to frontend."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "msg": "invalid json"})
                continue

            cmd = msg.get("cmd", "ping")
            if cmd == "ping":
                pending = _queue_pending_count()
                set_gauge("queue_depth", pending)
                await ws.send_json({"type": "pong", "queue_pending": pending})
            elif cmd == "subscribe":
                await ws.send_json({"type": "subscribed", "topic": msg.get("topic", "all")})
            else:
                await ws.send_json({"type": "echo", "cmd": cmd})
    except WebSocketDisconnect:
        pass


def _queue_pending_count() -> int:
    try:
        items = get_queue().snapshot()
        return sum(1 for i in items if i["status"] in ("pending", "downloading"))
    except Exception:
        return 0


if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("rwmod.server:app", host="0.0.0.0", port=8000, reload=False)

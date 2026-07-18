"""Application state container — replaces module-level singletons.

All shared state (config, DB, queue, autoupdate, metrics) lives here.
FastAPI lifespan creates one AppState instance, stored in app.state.
Routes access it via Depends(get_app_state).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rwmod.autoupdate import AutoUpdateManager
from rwmod.config import Config
from rwmod.queue import DownloadQueue, get_queue


@dataclass
class AppState:
    """Single source of truth for all application-wide state.

    Created once during app startup (lifespan), stored in app.state.rwmod.
    Eliminates module-level singletons and makes testing trivial.
    """

    config: Config = field(default_factory=Config.load)
    queue: DownloadQueue = field(default_factory=get_queue)
    autoupdate: AutoUpdateManager = field(default_factory=AutoUpdateManager)

    # Mutable state ONLY accessible through the AppState instance:
    # - Router-level caches are now keyed here instead of module globals
    mods_cache: dict = field(default_factory=dict)
    health_cache: dict = field(default_factory=dict)
    dashboard_cache: dict = field(default_factory=dict)

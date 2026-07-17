"""Shared test fixtures — TestClient, temp config, temp mods dir."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rwmod.config import Config
from rwmod.database import close_db


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Return a TestClient with an isolated config and temp DB."""
    # Override Config.CONFIG_PATH and DB_PATH
    import rwmod.config as cfg_mod
    import rwmod.database as db_mod

    orig_config = cfg_mod.Config.CONFIG_PATH
    orig_db = db_mod.DB_PATH

    cfg_mod.Config.CONFIG_PATH = tmp_path / ".rwmod_test.toml"
    db_mod.DB_PATH = tmp_path / ".rwmod_test.db"

    # Reset singleton queue
    import rwmod.queue as q_mod

    q_mod._queue = None

    # Reset autoupdate singleton
    import rwmod.deps as deps_mod

    deps_mod._autoupdate = None

    # Write a minimal valid config
    cfg = Config(steamcmd_path=tmp_path / "steamcmd" / "steamcmd.exe")
    (tmp_path / "steamcmd").mkdir()
    (tmp_path / "steamcmd" / "steamcmd.exe").touch()
    cfg.mods_dir = tmp_path / "Mods"
    cfg.rimworld_dir = tmp_path / "RimWorld"
    cfg.mods_dir.mkdir()
    cfg.rimworld_dir.mkdir()
    cfg.save()

    from rwmod.server import app

    with TestClient(app) as tc:
        yield tc

    # Cleanup
    cfg_mod.Config.CONFIG_PATH = orig_config
    db_mod.DB_PATH = orig_db
    close_db()

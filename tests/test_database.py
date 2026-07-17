"""Test database: SQLite CRUD for download history."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from rwmod.database import (
    clear_history,
    close_db,
    get_download_history,
    get_download_stats,
    init_db,
    record_download,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    """Use temp SQLite DB instead of production DB."""
    db_path = tmp_path / "test.db"
    with patch("rwmod.database.DB_PATH", db_path):
        init_db()
        yield
        close_db()  # close before unlink — WAL mode holds file lock on Windows
    db_path.unlink(missing_ok=True)


class TestHistory:
    def test_record_and_retrieve(self, temp_db):
        record_download("123", "success", mod_name="Test Mod")
        record_download("456", "failed", msg="SteamCMD error")
        history = get_download_history()
        assert len(history) == 2
        assert history[0]["status"] == "failed"  # newest first
        assert history[1]["status"] == "success"
        assert history[1]["mod_name"] == "Test Mod"

    def test_filter_by_status(self, temp_db):
        record_download("111", "success")
        record_download("222", "failed")
        record_download("333", "success")
        assert len(get_download_history(status="success")) == 2
        assert len(get_download_history(status="failed")) == 1

    def test_stats(self, temp_db):
        record_download("a", "success")
        record_download("b", "success")
        record_download("c", "failed")
        stats = get_download_stats()
        assert stats["total"] == 3
        assert stats["success"] == 2
        assert stats["failed"] == 1

    def test_clear(self, temp_db):
        record_download("1", "success")
        record_download("2", "success")
        clear_history()
        assert get_download_history() == []
        assert get_download_stats()["total"] == 0

    def test_limit(self, temp_db):
        for i in range(10):
            record_download(str(i), "success")
        assert len(get_download_history(limit=3)) == 3

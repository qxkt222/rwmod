"""Tests for backup.py — zip-based mod backup/restore."""

from __future__ import annotations

import zipfile
from pathlib import Path

from rwmod.backup import backup_mod, delete_backup, list_backups, restore_mod


class TestBackupMod:
    def test_backup_creates_zip(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        mod_dir = mods_dir / "test_mod"
        mod_dir.mkdir()
        (mod_dir / "About").mkdir()
        (mod_dir / "About" / "About.xml").write_text("<ModMetaData><name>Test</name></ModMetaData>")

        backup_dir = tmp_path / "backups"
        zip_path = backup_mod(mods_dir, "123", "test_mod", backup_dir)

        assert zip_path is not None
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"
        assert "123__" in zip_path.name
        assert zipfile.is_zipfile(zip_path)

    def test_backup_missing_mod_returns_none(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        backup_dir = tmp_path / "backups"

        result = backup_mod(mods_dir, "999", "nonexistent", backup_dir)
        assert result is None

    def test_restore_latest_backup(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        mod_dir = mods_dir / "test_mod"
        mod_dir.mkdir()
        (mod_dir / "About").mkdir()
        (mod_dir / "About" / "About.xml").write_text(
            "<ModMetaData><name>Original</name></ModMetaData>"
        )

        backup_dir = tmp_path / "backups"
        backup_mod(mods_dir, "123", "test_mod", backup_dir)

        # Simulate update: delete old version
        import shutil

        shutil.rmtree(mod_dir)

        result = restore_mod(mods_dir, "123", backup_dir)
        assert result["ok"]
        assert (mods_dir / "test_mod" / "About" / "About.xml").exists()

    def test_restore_nonexistent_backup(self, tmp_path: Path):
        result = restore_mod(tmp_path / "Mods", "000", tmp_path / "backups")
        assert not result["ok"]

    def test_list_backups(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        mod_dir = mods_dir / "my_mod"
        mod_dir.mkdir()
        (mod_dir / "About").mkdir()
        (mod_dir / "About" / "About.xml").write_text("<ModMetaData/>")

        backup_dir = tmp_path / "backups"
        backup_mod(mods_dir, "123", "my_mod", backup_dir)

        backups = list_backups(backup_dir)
        assert len(backups) == 1
        assert backups[0]["workshop_id"] == "123"
        assert backups[0]["folder_name"] == "my_mod"

    def test_delete_backup(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        mod_dir = mods_dir / "mod"
        mod_dir.mkdir()
        (mod_dir / "About").mkdir()
        (mod_dir / "About" / "About.xml").write_text("<ModMetaData/>")

        backup_dir = tmp_path / "backups"
        zip_path = backup_mod(mods_dir, "456", "mod", backup_dir)
        assert zip_path is not None

        ok = delete_backup(backup_dir, zip_path.name)
        assert ok
        assert not zip_path.exists()

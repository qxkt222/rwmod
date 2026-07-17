"""Test config management: load, save, auto-migrate to built-in SteamCMD."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from rwmod.config import Config


class TestConfigDefaults:
    def test_default_steamcmd_exists(self):
        # When built-in steamcmd.exe exists, it should be the default
        with patch.object(Path, "exists", return_value=True):
            cfg = Config()
            assert "steamcmd" in str(cfg.steamcmd_path).lower()

    def test_fallback_when_builtin_missing(self):
        with patch.object(Path, "exists", return_value=False):
            # The fallback is D:/steamcmd/steamcmd.exe (returned by _default_steamcmd_path)
            import rwmod.config as cfg_module

            with patch.object(
                cfg_module.Config,
                "_default_steamcmd_path",
                return_value=Path("D:/steamcmd/steamcmd.exe"),
            ):
                c = Config()
                assert str(c.steamcmd_path).replace("\\", "/") == "D:/steamcmd/steamcmd.exe"

    def test_backup_dir_defaults_to_mods_subdir(self):
        cfg = Config(mods_dir=Path("D:/RimWorld/Mods"))
        assert cfg.backup_dir == Path("D:/RimWorld/Mods/_backups")

    def test_explicit_backup_dir(self):
        cfg = Config(backup_dir=Path("E:/Backups"))
        assert cfg.backup_dir == Path("E:/Backups")


class TestConfigLoad:
    def test_load_nonexistent_creates_defaults(self, tmp_path: Path):
        with patch.object(Config, "CONFIG_PATH", tmp_path / "nonexistent.toml"):
            cfg = Config.load()
            assert cfg.mods_dir == Path("D:/RimWorld/Mods")

    def test_load_existing(self, tmp_path: Path):
        f = tmp_path / ".rwmod.toml"
        f.write_text(
            'steamcmd_path = "D:/steamcmd/steamcmd.exe"\n'
            'mods_dir = "E:/MyMods"\n'
            'rimworld_dir = "E:/RimWorld"\n'
            'backup_dir = "F:/Backups"\n'
        )
        with patch.object(Config, "CONFIG_PATH", f):
            with patch.object(
                Path, "exists", lambda self: self != Path("D:/steamcmd/steamcmd.exe")
            ):
                cfg = Config.load()
                assert cfg.mods_dir == Path("E:/MyMods")
                assert cfg.backup_dir == Path("F:/Backups")

    def test_auto_prefers_builtin(self, tmp_path: Path):
        f = tmp_path / ".rwmod.toml"
        f.write_text(
            'steamcmd_path = "D:/old/steamcmd.exe"\n'
            'mods_dir = "D:/RimWorld/Mods"\n'
            'rimworld_dir = "D:/RimWorld"\n'
        )
        with patch.object(Config, "CONFIG_PATH", f):
            with patch.object(Path, "exists", return_value=True):
                cfg = Config.load()
                assert "steamcmd" in str(cfg.steamcmd_path).lower()


class TestConfigSave:
    def test_save_and_reload(self, tmp_path: Path):
        f = tmp_path / "save_test.toml"
        with patch.object(Config, "CONFIG_PATH", f):
            cfg = Config(mods_dir=Path("Z:/Test"))
            cfg.save()
            assert f.exists()
            content = f.read_text()
            assert 'mods_dir = "Z:/Test"' in content

"""Configuration management — reads/writes ~/.rwmod.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

__all__ = ["Config"]


class ConfigError(Exception):
    """Raised when configuration validation fails."""


class Config:
    """Persisted in ~/.rwmod.toml, defaults to D: drive paths."""

    CONFIG_PATH = Path.home() / ".rwmod.toml"

    @staticmethod
    def _default_steamcmd_path() -> Path:
        """Lazily resolve built-in steamcmd path (avoid class-load-time I/O)."""
        p = Path(__file__).resolve().parent.parent.parent / "steamcmd" / "steamcmd.exe"
        return p if p.exists() else Path("D:/steamcmd/steamcmd.exe")

    def __init__(
        self,
        steamcmd_path: Path | None = None,
        mods_dir: Path = Path("D:/RimWorld/Mods"),
        rimworld_dir: Path = Path("D:/RimWorld"),
        backup_dir: Path | None = None,
    ) -> None:
        if steamcmd_path is None:
            steamcmd_path = Config._default_steamcmd_path()
        self.steamcmd_path = steamcmd_path
        self.mods_dir = mods_dir
        self.rimworld_dir = rimworld_dir
        self.backup_dir = backup_dir or (mods_dir / "_backups")

    @classmethod
    def load(cls) -> Config:
        builtin = cls._default_steamcmd_path()

        if cls.CONFIG_PATH.exists():
            data = tomllib.loads(cls.CONFIG_PATH.read_text(encoding="utf-8"))
            sc = Path(data.get("steamcmd_path", str(builtin)))
            # Always prefer built-in if it exists
            if builtin.exists():
                sc = builtin
            return cls(
                steamcmd_path=sc,
                mods_dir=Path(data.get("mods_dir", "D:/RimWorld/Mods")),
                rimworld_dir=Path(data.get("rimworld_dir", "D:/RimWorld")),
                backup_dir=Path(data["backup_dir"]) if "backup_dir" in data else None,
            )
        return cls(steamcmd_path=builtin)

    def save(self) -> None:
        """Persist config as TOML with proper string escaping."""
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        parts: list[str] = [
            f'steamcmd_path = "{_esc(self.steamcmd_path.as_posix())}"',
            f'mods_dir = "{_esc(self.mods_dir.as_posix())}"',
            f'rimworld_dir = "{_esc(self.rimworld_dir.as_posix())}"',
        ]
        if self.backup_dir:
            parts.append(f'backup_dir = "{_esc(self.backup_dir.as_posix())}"')
        self.CONFIG_PATH.write_text("\n".join(parts) + "\n", encoding="utf-8")

    def validate(self) -> None:
        errors: list[str] = []
        if not self.steamcmd_path.exists():
            errors.append(f"SteamCMD 未找到: {self.steamcmd_path}")
        if not self.rimworld_dir.exists():
            errors.append(f"RimWorld 目录未找到: {self.rimworld_dir}")
        if errors:
            raise ConfigError("\n".join(errors))
        self.mods_dir.mkdir(parents=True, exist_ok=True)


def _esc(s: str) -> str:
    """Escape a string for TOML basic string (double-quoted).
    Handles backslash and double-quote — the only special chars that
    appear in Windows file paths.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"')

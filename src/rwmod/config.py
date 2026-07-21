"""Configuration management - reads/writes ~/.rwmod.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

from rwmod.errors import ConfigError

__all__ = ["Config"]


class Config:
    """Persisted in ~/.rwmod.toml, defaults to D: drive paths."""

    CONFIG_PATH = Path.home() / ".rwmod.toml"

    @classmethod
    def _default_steamcmd_path(cls) -> Path:
        """Lazily resolve built-in steamcmd path."""
        p = Path(__file__).resolve().parent.parent.parent / "steamcmd" / "steamcmd.exe"
        return p if p.exists() else Path("D:/steamcmd/steamcmd.exe")

    def __init__(
        self,
        steamcmd_path: Path | None = None,
        mods_dir: Path = Path("D:/RimWorld/Mods"),
        rimworld_dir: Path = Path("D:/RimWorld"),
        backup_dir: Path | None = None,
        steam_api_key: str = "",
    ) -> None:
        if steamcmd_path is None:
            steamcmd_path = Config._default_steamcmd_path()
        self.steamcmd_path = steamcmd_path
        self.mods_dir = mods_dir
        self.rimworld_dir = rimworld_dir
        self.backup_dir = backup_dir or (mods_dir / "_backups")
        self.steam_api_key = steam_api_key

    @classmethod
    def load(cls) -> "Config":
        builtin = cls._default_steamcmd_path()
        if cls.CONFIG_PATH.exists():
            data = tomllib.loads(cls.CONFIG_PATH.read_text(encoding="utf-8"))
            sc = Path(data.get("steamcmd_path", str(builtin)))
            if builtin.exists():
                sc = builtin
            return cls(
                steamcmd_path=sc,
                mods_dir=Path(data.get("mods_dir", "D:/RimWorld/Mods")),
                rimworld_dir=Path(data.get("rimworld_dir", "D:/RimWorld")),
                backup_dir=Path(data["backup_dir"]) if "backup_dir" in data else None,
                steam_api_key=data.get("steam_api_key", ""),
            )
        return cls(steamcmd_path=builtin)

    def save(self) -> None:
        self.CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f'steamcmd_path = "{_esc(self.steamcmd_path.as_posix())}"',
            f'mods_dir = "{_esc(self.mods_dir.as_posix())}"',
            f'rimworld_dir = "{_esc(self.rimworld_dir.as_posix())}"',
        ]
        if self.backup_dir:
            lines.append(f'backup_dir = "{_esc(self.backup_dir.as_posix())}"')
        if self.steam_api_key:
            lines.append(f'steam_api_key = "{_esc(self.steam_api_key)}"')
        self.CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def validate(self) -> None:
        errors = []
        if not self.steamcmd_path.exists():
            errors.append(f"SteamCMD not found: {self.steamcmd_path}")
        if not self.rimworld_dir.exists():
            errors.append(f"RimWorld dir not found: {self.rimworld_dir}")
        if errors:
            raise ConfigError("\n".join(errors))
        self.mods_dir.mkdir(parents=True, exist_ok=True)


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')

"""Thin subprocess wrapper around SteamCMD."""

from __future__ import annotations

import subprocess
from pathlib import Path

__all__ = ["SteamCMD"]


class SteamCMD:
    """Run SteamCMD commands and stream output."""

    STEAM_APP_ID = "294100"
    _TIMEOUT_MINUTES = 10  # max wait for SteamCMD to finish

    def __init__(self, steamcmd_path: Path) -> None:
        self.exe = str(steamcmd_path)
        self.steam_dir = steamcmd_path.parent

    def workshop_download(self, mod_id: str) -> tuple[int, list[str]]:
        """Download a workshop item, return (returncode, lines). Times out after 5 min."""
        cmd = [
            self.exe,
            "+login",
            "anonymous",
            "+workshop_download_item",
            self.STEAM_APP_ID,
            mod_id,
            "+quit",
        ]
        lines: list[str] = []

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(self.steam_dir),
            )

            if proc.stdout is None:
                return -1, lines

            try:
                for raw in proc.stdout:
                    line = raw.rstrip("\n")
                    if line:
                        lines.append(line)
                proc.wait(timeout=self._TIMEOUT_MINUTES * 60)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                lines.append("ERROR! Timeout — SteamCMD hung, forcefully killed.")
                return -1, lines

            return proc.returncode, lines
        except OSError as e:
            return -1, [f"ERROR! Failed to start SteamCMD: {e}"]

    @property
    def workshop_content_dir(self) -> Path:
        """Directory where SteamCMD stores downloaded workshop content."""
        return self.steam_dir / "steamapps" / "workshop" / "content" / self.STEAM_APP_ID

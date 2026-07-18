"""Thin subprocess wrapper around SteamCMD — with structured error reporting."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["SteamCMD", "DownloadResult", "ErrorKind"]

# ── error taxonomy ──────────────────────────────────────────────────
# SteamCMD workshop_log.txt records the real reason for every failure.
# We parse it so the downloader can skip pointless retries.


class ErrorKind:
    """SteamCMD error categories from workshop_log.txt."""

    OK = "ok"
    FAILURE = "failure"  # depot/manifest error — mod exists but can't download
    FILE_NOT_FOUND = "file_not_found"  # mod removed from workshop
    ACCESS_DENIED = "access_denied"  # private/hidden mod
    NO_MATCH = "no_match"  # wrong game AppID
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

    # Errors that will NEVER succeed on retry → skip retry + Skymods
    NON_RETRYABLE = {FAILURE, FILE_NOT_FOUND, ACCESS_DENIED, NO_MATCH}

    _HUMAN: dict[str, str] = {
        OK: "下载成功",
        FAILURE: "Mod 存在但文件不可用（可能已被作者删除或设为私密）",
        FILE_NOT_FOUND: "Mod 不存在（已从创意工坊移除）",
        ACCESS_DENIED: "Mod 为私密/隐藏状态，无法匿名下载",
        NO_MATCH: "不是 RimWorld 的 Mod（属于其他游戏）",
        TIMEOUT: "SteamCMD 超时无响应",
        UNKNOWN: "未知错误",
    }

    @classmethod
    def explain(cls, kind: str) -> str:
        return cls._HUMAN.get(kind, f"未知错误类型: {kind}")


@dataclass
class DownloadResult:
    """Structured download result with error classification."""

    success: bool
    mod_id: str
    error_kind: str = ErrorKind.UNKNOWN
    error_detail: str = ""
    output_lines: list[str] = field(default_factory=list)


class SteamCMD:
    """Run SteamCMD commands with structured error parsing."""

    STEAM_APP_ID = "294100"
    _TIMEOUT_MINUTES = 10  # max wait for SteamCMD to finish

    def __init__(self, steamcmd_path: Path) -> None:
        self.exe = str(steamcmd_path)
        self.steam_dir = steamcmd_path.parent

    @property
    def workshop_log(self) -> Path:
        """Path to workshop_log.txt where SteamCMD writes error details."""
        return self.steam_dir / "logs" / "workshop_log.txt"

    @property
    def workshop_content_dir(self) -> Path:
        """Directory where SteamCMD stores downloaded workshop content."""
        return self.steam_dir / "steamapps" / "workshop" / "content" / self.STEAM_APP_ID

    def workshop_download(self, mod_id: str) -> DownloadResult:
        """Download a workshop item, return structured result with error classification."""
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
                return DownloadResult(
                    success=False,
                    mod_id=mod_id,
                    error_kind=ErrorKind.UNKNOWN,
                    error_detail="无法读取 SteamCMD 输出",
                )

            try:
                for raw in proc.stdout:
                    line = raw.rstrip("\n")
                    if line:
                        lines.append(line)
                proc.wait(timeout=self._TIMEOUT_MINUTES * 60)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                return DownloadResult(
                    success=False,
                    mod_id=mod_id,
                    error_kind=ErrorKind.TIMEOUT,
                    error_detail="SteamCMD 超时无响应",
                    output_lines=lines,
                )

        except OSError as e:
            return DownloadResult(
                success=False,
                mod_id=mod_id,
                error_kind=ErrorKind.UNKNOWN,
                error_detail=f"无法启动 SteamCMD: {e}",
            )

        # ── parse workshop_log.txt for the real error reason ──────
        error_kind, error_detail = self._parse_workshop_error(mod_id)

        if error_kind == ErrorKind.OK:
            # Double-check the content actually exists
            content_dir = self.workshop_content_dir / mod_id
            if content_dir.exists():
                return DownloadResult(
                    success=True,
                    mod_id=mod_id,
                    error_kind=ErrorKind.OK,
                    output_lines=lines,
                )
            # SteamCMD said OK but file not on disk → treat as failure
            error_kind = ErrorKind.FAILURE
            error_detail = "SteamCMD 返回成功但未找到下载内容"

        return DownloadResult(
            success=False,
            mod_id=mod_id,
            error_kind=error_kind,
            error_detail=error_detail,
            output_lines=lines,
        )

    def _parse_workshop_error(self, mod_id: str) -> tuple[str, str]:
        """Parse workshop_log.txt to extract the real error reason.

        Workshop log records look like:
          [AppID 294100] Download item 3565275325 result : Failure
          [AppID 294100] Get details for item 3565275325 failed : File Not Found
          [AppID 294100] Download item 3565275325 result : OK
        """
        log_path = self.workshop_log
        if not log_path.exists():
            return ErrorKind.UNKNOWN, "workshop_log.txt 不存在"

        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ErrorKind.UNKNOWN, "无法读取 workshop_log.txt"

        # ── extract the *last* result line for this mod ID ────────
        # Pattern: [AppID 294100] Download item {mod_id} result : {reason}
        result_pattern = (
            rf"\[AppID {self.STEAM_APP_ID}\] Download item {re.escape(mod_id)} result : (.+)"
        )
        result_matches = list(re.finditer(result_pattern, text))

        # Pattern: [AppID 294100] Get details for item {mod_id} failed : {reason}
        detail_pattern = (
            rf"\[AppID {self.STEAM_APP_ID}\] Get details for item {re.escape(mod_id)} failed : (.+)"
        )
        detail_matches = list(re.finditer(detail_pattern, text))

        error_kind = ErrorKind.OK
        error_detail = ""

        # Parse the last result line
        if result_matches:
            raw_reason = result_matches[-1].group(1).strip()
            error_kind = self._classify_reason(raw_reason)
            error_detail = f"SteamCMD: {raw_reason}"

        # Detail lines give more specific info (e.g. "Wrong AppID 241100")
        if detail_matches:
            raw_detail = detail_matches[-1].group(1).strip()
            if raw_detail and raw_detail != error_kind.replace("_", " ").title():
                error_detail = f"SteamCMD: {raw_detail}"

        return error_kind, error_detail

    @staticmethod
    def _classify_reason(reason: str) -> str:
        """Map SteamCMD result strings to our ErrorKind taxonomy."""
        r = reason.strip().lower()
        if r == "ok":
            return ErrorKind.OK
        if "file not found" in r:
            return ErrorKind.FILE_NOT_FOUND
        if "access denied" in r:
            return ErrorKind.ACCESS_DENIED
        if "no match" in r:
            return ErrorKind.NO_MATCH
        if "failure" in r:
            return ErrorKind.FAILURE
        return ErrorKind.UNKNOWN

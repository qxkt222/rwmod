"""Test SteamCMD error parsing — the core of error handling logic.

Tests the _parse_workshop_error and _classify_reason logic
without needing actual SteamCMD installed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from rwmod.steamcmd import ErrorKind, SteamCMD


@pytest.fixture
def steamcmd(tmp_path: Path):
    """Create a SteamCMD instance pointing at a temp directory."""
    exe = tmp_path / "steamcmd.exe"
    exe.touch()
    return SteamCMD(exe)


class TestClassifyReason:
    def test_ok(self):
        assert SteamCMD._classify_reason("OK") == ErrorKind.OK
        assert SteamCMD._classify_reason("Ok") == ErrorKind.OK
        # _classify_reason does .lower() first — case-insensitive
        assert SteamCMD._classify_reason("ok") == ErrorKind.OK

    def test_failure(self):
        assert SteamCMD._classify_reason("Failure") == ErrorKind.FAILURE

    def test_file_not_found(self):
        assert SteamCMD._classify_reason("File Not Found") == ErrorKind.FILE_NOT_FOUND

    def test_access_denied(self):
        assert SteamCMD._classify_reason("Access Denied") == ErrorKind.ACCESS_DENIED

    def test_no_match(self):
        assert SteamCMD._classify_reason("No Match") == ErrorKind.NO_MATCH

    def test_timeout(self):
        # Note: TIMEOUT is set by the subprocess exception handler,
        # NOT by _classify_reason (which has no timeout branch).
        # _classify_reason returns UNKNOWN for unrecognized strings.
        assert SteamCMD._classify_reason("Download timed out") == ErrorKind.UNKNOWN

    def test_unknown(self):
        assert SteamCMD._classify_reason("SomeWeirdError") == ErrorKind.UNKNOWN
        assert SteamCMD._classify_reason("") == ErrorKind.UNKNOWN


class TestErrorKind:
    def test_explain(self):
        assert "下载成功" in ErrorKind.explain(ErrorKind.OK)
        assert "文件不可用" in ErrorKind.explain(ErrorKind.FAILURE)
        assert "已从创意工坊移除" in ErrorKind.explain(ErrorKind.FILE_NOT_FOUND)
        assert "私密" in ErrorKind.explain(ErrorKind.ACCESS_DENIED)
        assert "不是 RimWorld" in ErrorKind.explain(ErrorKind.NO_MATCH)
        assert "超时" in ErrorKind.explain(ErrorKind.TIMEOUT)
        assert "未知" in ErrorKind.explain(ErrorKind.UNKNOWN)

    def test_non_retryable(self):
        assert ErrorKind.FAILURE in ErrorKind.NON_RETRYABLE
        assert ErrorKind.FILE_NOT_FOUND in ErrorKind.NON_RETRYABLE
        assert ErrorKind.ACCESS_DENIED in ErrorKind.NON_RETRYABLE
        assert ErrorKind.NO_MATCH in ErrorKind.NON_RETRYABLE
        assert ErrorKind.OK not in ErrorKind.NON_RETRYABLE
        assert ErrorKind.TIMEOUT not in ErrorKind.NON_RETRYABLE
        assert ErrorKind.UNKNOWN not in ErrorKind.NON_RETRYABLE


class TestParseWorkshopError:
    def test_no_log_file(self, steamcmd: SteamCMD):
        kind, detail = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.UNKNOWN
        assert "workshop_log.txt 不存在" in detail

    def test_ok_result(self, steamcmd: SteamCMD, tmp_path: Path):
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Download item 12345 result : OK\n"
        )
        kind, _ = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.OK

    def test_failure_result(self, steamcmd: SteamCMD, tmp_path: Path):
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Download item 12345 result : Failure\n"
        )
        kind, _ = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.FAILURE

    def test_file_not_found_result(self, steamcmd: SteamCMD, tmp_path: Path):
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Get details for item 12345 failed : File Not Found\n"
            "[AppID 294100] Download item 12345 result : Failure\n"
        )
        kind, detail = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.FAILURE
        assert "File Not Found" in detail

    def test_wrong_appid(self, steamcmd: SteamCMD, tmp_path: Path):
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Get details for item 12345 failed : Wrong AppID 241100\n"
        )
        kind, detail = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.OK  # no result line → default OK
        assert "Wrong AppID" in detail

    def test_access_denied_result(self, steamcmd: SteamCMD, tmp_path: Path):
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Download item 12345 result : Access Denied\n"
        )
        kind, _ = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.ACCESS_DENIED

    def test_last_result_wins(self, steamcmd: SteamCMD, tmp_path: Path):
        """Multiple lines for the same mod — last result wins."""
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Download item 12345 result : Failure\n"
            "[AppID 294100] Download item 12345 result : OK\n"
        )
        kind, _ = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.OK

    def test_different_mod_not_matched(self, steamcmd: SteamCMD, tmp_path: Path):
        log = steamcmd.steam_dir / "logs" / "workshop_log.txt"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(
            "[AppID 294100] Download item 99999 result : OK\n"
        )
        kind, _ = steamcmd._parse_workshop_error("12345")
        assert kind == ErrorKind.OK  # no result for 12345 → default OK


class TestSteamCMDProperties:
    def test_workshop_log_path(self, steamcmd: SteamCMD):
        assert steamcmd.workshop_log.name == "workshop_log.txt"
        assert "logs" in str(steamcmd.workshop_log)

    def test_workshop_content_dir(self, steamcmd: SteamCMD):
        assert "294100" in str(steamcmd.workshop_content_dir)
        assert "workshop" in str(steamcmd.workshop_content_dir)

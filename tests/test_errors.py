"""Test errors: unified exception hierarchy and detail propagation."""

from __future__ import annotations

import pytest

from rwmod.errors import (
    RwmodError,
    ConfigError,
    SteamCmdError,
    WorkshopError,
    ModNotFoundError,
    DownloadError,
    ValidationError,
    ConflictError,
)


class TestRwmodError:
    def test_default_values(self):
        exc = RwmodError()
        assert exc.status_code == 500
        assert exc.detail == "内部错误"

    def test_custom_detail(self):
        exc = RwmodError("自定义错误消息")
        assert exc.detail == "自定义错误消息"
        assert exc.status_code == 500

    def test_str_repr(self):
        exc = RwmodError("test")
        assert str(exc) == "test"


class TestConfigError:
    def test_has_correct_status(self):
        exc = ConfigError()
        assert exc.status_code == 400

    def test_custom_detail(self):
        exc = ConfigError("SteamCMD 未找到")
        assert exc.detail == "SteamCMD 未找到"


class TestSteamCmdError:
    def test_has_correct_status(self):
        exc = SteamCmdError()
        assert exc.status_code == 502


class TestWorkshopError:
    def test_has_correct_status(self):
        exc = WorkshopError()
        assert exc.status_code == 502


class TestModNotFoundError:
    def test_has_correct_status(self):
        exc = ModNotFoundError()
        assert exc.status_code == 404

    def test_custom_detail(self):
        exc = ModNotFoundError("Mod 1234567890 不存在")
        assert exc.detail == "Mod 1234567890 不存在"


class TestDownloadError:
    def test_has_correct_status(self):
        exc = DownloadError()
        assert exc.status_code == 502


class TestValidationError:
    def test_has_correct_status(self):
        exc = ValidationError()
        assert exc.status_code == 400


class TestConflictError:
    def test_has_correct_status(self):
        exc = ConflictError()
        assert exc.status_code == 409


class TestExceptionInheritance:
    def test_all_inherit_from_rwmod_error(self):
        for cls in [ConfigError, SteamCmdError, WorkshopError, ModNotFoundError, DownloadError, ValidationError, ConflictError]:
            assert issubclass(cls, RwmodError)

    def test_is_catchable_as_rwmod_error(self):
        """Any subclass should be catchable as RwmodError."""
        exc = ConfigError("test")
        assert isinstance(exc, RwmodError)

    def test_is_catchable_as_exception(self):
        exc = ModNotFoundError("test")
        assert isinstance(exc, Exception)

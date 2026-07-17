"""Tests for compatibility.py — version detection and mod compatibility."""

from __future__ import annotations

from pathlib import Path

from rwmod.compatibility import (
    _normalize_version,
    check_compatibility,
    detect_rimworld_version,
)
from rwmod.metadata import ModMeta


class TestDetectRimWorldVersion:
    def test_version_txt(self, tmp_path: Path):
        (tmp_path / "Version.txt").write_text("1.5.4297 rev1117")
        v = detect_rimworld_version(tmp_path)
        assert v == "1.5"

    def test_version_txt_with_prefix(self, tmp_path: Path):
        (tmp_path / "Version.txt").write_text("v1.4.3901")
        v = detect_rimworld_version(tmp_path)
        assert v == "1.4"

    def test_no_version_file(self, tmp_path: Path):
        v = detect_rimworld_version(tmp_path)
        assert v is None


class TestCheckCompatibility:
    def test_compatible(self):
        metas = [
            ModMeta("mod1", "A", "a.b", "111", supported_versions=["1.4", "1.5"]),
            ModMeta("mod2", "B", "c.d", "222", supported_versions=["1.5"]),
        ]
        result = check_compatibility(metas, "1.5")
        assert len(result["compatible"]) == 2
        assert len(result["incompatible"]) == 0

    def test_incompatible(self):
        metas = [
            ModMeta("old", "Old Mod", "old.pkg", "999", supported_versions=["1.3", "1.4"]),
        ]
        result = check_compatibility(metas, "1.5")
        assert len(result["incompatible"]) == 1
        assert len(result["compatible"]) == 0

    def test_unknown_no_versions(self):
        metas = [
            ModMeta("mystery", "Mystery Mod", "", "", supported_versions=[]),
        ]
        result = check_compatibility(metas, "1.5")
        assert len(result["unknown"]) == 1
        assert len(result["incompatible"]) == 0

    def test_mixed(self):
        metas = [
            ModMeta("a", "A", "a", "1", supported_versions=["1.5"]),
            ModMeta("b", "B", "b", "2", supported_versions=["1.4"]),
            ModMeta("c", "C", "c", "3", supported_versions=[]),
        ]
        result = check_compatibility(metas, "1.5")
        assert len(result["compatible"]) == 1
        assert len(result["incompatible"]) == 1
        assert len(result["unknown"]) == 1


class TestNormalizeVersion:
    def test_simple(self):
        assert _normalize_version("1.5") == "1.5"

    def test_with_patch(self):
        assert _normalize_version("1.5.4297") == "1.5"

    def test_with_prefix(self):
        assert _normalize_version("v1.4") == "1.4"

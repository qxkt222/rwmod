"""Test downloader — mod ID parsing, folder naming, existing mod detection.

Tests core logic paths that don't require SteamCMD network calls.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from rwmod.downloader import (
    _find_existing,
    _pick_folder_name,
    download_one,
    extract_mod_id,
)


class TestExtractModId:
    def test_plain_number(self):
        assert extract_mod_id("2009463077") == "2009463077"

    def test_workshop_url(self):
        url = "https://steamcommunity.com/sharedfiles/filedetails/?id=2009463077"
        assert extract_mod_id(url) == "2009463077"

    def test_url_with_other_params(self):
        url = "https://steamcommunity.com/sharedfiles/filedetails/?id=123456&searchtext=foo"
        assert extract_mod_id(url) == "123456"

    def test_invalid_input(self):
        assert not extract_mod_id("not_a_number")
        assert not extract_mod_id("https://example.com")
        assert not extract_mod_id("")

    def test_whitespace_only(self):
        assert not extract_mod_id("   ")

    def test_whitespace_number(self):
        # Numbers with whitespace are stripped and considered valid
        assert extract_mod_id("  123456  ") == "123456"


class TestFindExisting:
    def test_finds_by_published_file_id(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        mod_folder = mods_dir / "SomeMod"
        mod_folder.mkdir()
        about = mod_folder / "About"
        about.mkdir()
        (about / "PublishedFileId.txt").write_text("2009463077")

        result = _find_existing(mods_dir, "2009463077")
        assert result is not None
        assert result.name == "SomeMod"

    def test_not_found(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        assert _find_existing(mods_dir, "99999") is None

    def test_empty_mods_dir(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        assert _find_existing(mods_dir, "2009463077") is None

    def test_ignores_non_dirs(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        (mods_dir / "some_file.txt").write_text("hello")
        assert _find_existing(mods_dir, "2009463077") is None

    def test_multiple_mods_finds_correct_one(self, tmp_path: Path):
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()
        for i, wid in enumerate(["111", "222", "333"]):
            folder = mods_dir / f"mod_{i}"
            folder.mkdir()
            about = folder / "About"
            about.mkdir()
            (about / "PublishedFileId.txt").write_text(wid)

        result = _find_existing(mods_dir, "222")
        assert result is not None
        assert result.name == "mod_1"


class TestPickFolderName:
    def test_from_package_id(self, tmp_path: Path):
        workshop_path = tmp_path / "workshop"
        workshop_path.mkdir()
        about = workshop_path / "About"
        about.mkdir()
        (about / "About.xml").write_text(
            "<ModMetaData><packageId>author.somecoolmod</packageId></ModMetaData>"
        )
        name = _pick_folder_name(workshop_path, "12345")
        assert name == "author.somecoolmod"

    def test_fallback_to_name(self, tmp_path: Path):
        workshop_path = tmp_path / "workshop"
        workshop_path.mkdir()
        about = workshop_path / "About"
        about.mkdir()
        (about / "About.xml").write_text(
            "<ModMetaData><name>My Cool Mod</name></ModMetaData>"
        )
        name = _pick_folder_name(workshop_path, "12345")
        assert "My Cool Mod" in name
        assert "12345" in name

    def test_fallback_to_mod_id(self, tmp_path: Path):
        workshop_path = tmp_path / "workshop"
        workshop_path.mkdir()
        about = workshop_path / "About"
        about.mkdir()
        (about / "About.xml").write_text("<ModMetaData></ModMetaData>")
        name = _pick_folder_name(workshop_path, "12345")
        assert name == "mod_12345"

    def test_sanitize_special_chars(self, tmp_path: Path):
        workshop_path = tmp_path / "workshop"
        workshop_path.mkdir()
        about = workshop_path / "About"
        about.mkdir()
        (about / "About.xml").write_text(
            "<ModMetaData><packageId>evil:hack<foo>bar</packageId></ModMetaData>"
        )
        name = _pick_folder_name(workshop_path, "12345")
        assert ":" not in name
        assert "<" not in name
        assert ">" not in name

    def test_no_about_xml(self, tmp_path: Path):
        workshop_path = tmp_path / "workshop"
        workshop_path.mkdir()
        name = _pick_folder_name(workshop_path, "12345")
        assert name == "mod_12345"

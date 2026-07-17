"""Test downloader: mod ID extraction, existing detection, folder naming."""

from __future__ import annotations

from pathlib import Path

from rwmod.downloader import _find_existing, _pick_folder_name, extract_mod_id


class TestExtractModId:
    def test_plain_number(self):
        assert extract_mod_id("2009463077") == "2009463077"

    def test_workshop_url(self):
        assert (
            extract_mod_id("https://steamcommunity.com/sharedfiles/filedetails/?id=2009463077")
            == "2009463077"
        )

    def test_url_with_other_params(self):
        assert (
            extract_mod_id(
                "https://steamcommunity.com/sharedfiles/filedetails/?id=123&searchtext=test"
            )
            == "123"
        )

    def test_invalid(self):
        assert extract_mod_id("not_a_mod") is None
        assert extract_mod_id("") is None

    def test_whitespace_only(self):
        assert extract_mod_id("   ") is None


class TestPickFolderName:
    def test_from_package_id(self, tmp_path: Path):
        (tmp_path / "About").mkdir()
        (tmp_path / "About" / "About.xml").write_text(
            "<ModMetaData><packageId>author.modname</packageId><name>Fancy Mod</name></ModMetaData>"
        )
        assert _pick_folder_name(tmp_path, "123456") == "author.modname"

    def test_fallback_to_name(self, tmp_path: Path):
        (tmp_path / "About").mkdir()
        (tmp_path / "About" / "About.xml").write_text(
            "<ModMetaData><name>Super Mod</name></ModMetaData>"
        )
        assert _pick_folder_name(tmp_path, "123456") == "Super Mod_123456"

    def test_fallback_to_mod_id(self, tmp_path: Path):
        assert _pick_folder_name(tmp_path, "999") == "mod_999"

    def test_sanitize_special_chars(self, tmp_path: Path):
        (tmp_path / "About").mkdir()
        (tmp_path / "About" / "About.xml").write_text(
            "<ModMetaData><packageId>test:mod<name></packageId></ModMetaData>"
        )
        name = _pick_folder_name(tmp_path, "1")
        assert ":" not in name
        assert "<" not in name


class TestFindExisting:
    def test_finds_by_published_file_id(self, tmp_path: Path):
        mod_dir = tmp_path / "some_mod"
        mod_dir.mkdir()
        (mod_dir / "About").mkdir()
        (mod_dir / "About" / "PublishedFileId.txt").write_text("2009463077")
        result = _find_existing(tmp_path, "2009463077")
        assert result == mod_dir

    def test_not_found(self, tmp_path: Path):
        assert _find_existing(tmp_path, "nonexistent") is None

    def test_ignores_non_dirs(self, tmp_path: Path):
        (tmp_path / "readme.txt").write_text("hello")
        result = _find_existing(tmp_path, "2009463077")
        assert result is None

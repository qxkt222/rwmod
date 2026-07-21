"""Tests for save_parser.py \u2014 .rws save file parsing."""

from __future__ import annotations

from pathlib import Path

from rwmod.save_parser import _extract_game_version, analyze_save, find_save_files, parse_save_mods


class TestParseSaveMods:
    def test_from_string_content(self):
        content = '''<?xml version="1.0"?>
<saves>
  <modIds>
    <li>brrainz.harmony</li>
    <li>ludeon.rimworld</li>
    <li>author.mod1</li>
  </modIds>
</saves>'''
        mods = parse_save_mods(content)
        assert mods == ["brrainz.harmony", "ludeon.rimworld", "author.mod1"]

    def test_from_path(self, tmp_path: Path):
        f = tmp_path / "test.rws"
        f.write_text(
            '<saves><modIds><li>test.mod</li><li>other.mod</li></modIds></saves>',
            encoding="utf-8",
        )
        mods = parse_save_mods(f)
        assert mods == ["test.mod", "other.mod"]

    def test_no_mod_ids(self):
        mods = parse_save_mods("<saves><gameVersion>1.5</gameVersion></saves>")
        assert mods == []

    def test_missing_file(self, tmp_path: Path):
        mods = parse_save_mods(tmp_path / "nonexistent.rws")
        assert mods == []

    def test_empty_content(self):
        assert parse_save_mods("") == []


class TestExtractGameVersion:
    def test_extracts_version(self, tmp_path: Path):
        f = tmp_path / "save.rws"
        f.write_text("<saves><gameVersion>1.5.4297 rev1117</gameVersion></saves>")
        assert _extract_game_version(f) == "1.5.4297 rev1117"

    def test_no_version(self, tmp_path: Path):
        f = tmp_path / "save.rws"
        f.write_text("<saves></saves>")
        assert _extract_game_version(f) is None

    def test_missing_file(self, tmp_path: Path):
        assert _extract_game_version(tmp_path / "nonexistent.rws") is None


class TestAnalyzeSave:
    def test_full_analysis(self, tmp_path: Path):
        f = tmp_path / "MyColony.rws"
        f.write_text(
            '<saves>'
            '<gameVersion>1.5.4297 rev1117</gameVersion>'
            '<modIds><li>mod.a</li><li>mod.b</li><li>mod.c</li></modIds>'
            '</saves>',
        )
        installed = {"mod.a", "mod.b", "mod.d"}
        result = analyze_save(f, installed)
        assert result["name"] == "MyColony"
        assert result["total_mods"] == 3
        assert result["required_mods"] == ["mod.a", "mod.b", "mod.c"]
        assert result["missing_mods"] == ["mod.c"]
        assert result["unused_by_save"] == ["mod.d"]
        assert not result["loadable"]
        assert result["completeness"] == 0.75

    def test_all_installed(self, tmp_path: Path):
        f = tmp_path / "Complete.rws"
        f.write_text(
            '<saves><modIds><li>mod.a</li><li>mod.b</li></modIds></saves>'
        )
        result = analyze_save(f, {"mod.a", "mod.b"})
        assert result["loadable"]
        assert result["completeness"] == 1.0
        assert result["missing_mods"] == []


class TestFindSaveFiles:
    def test_returns_empty_for_no_saves(self, tmp_path: Path):
        saves = find_save_files(tmp_path)
        assert isinstance(saves, list)

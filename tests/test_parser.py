"""Test parsers: mod list files, collection binary format, ModsConfig.xml."""

from __future__ import annotations

import json
import struct
from pathlib import Path

from rwmod.parser import (
    _parse_legacy_collection,
    get_installed_package_ids,
    parse_collection_dir,
    parse_modlist_file,
    parse_mods_config,
    resolve_workshop_ids,
)


class TestModListFile:
    def test_simple_ids(self, tmp_path: Path):
        f = tmp_path / "list.txt"
        f.write_text("2009463077\n1234567890\n")
        assert parse_modlist_file(f) == ["2009463077", "1234567890"]

    def test_urls(self, tmp_path: Path):
        f = tmp_path / "list.txt"
        f.write_text(
            "https://steamcommunity.com/sharedfiles/filedetails/?id=2009463077\n1234567890\n"
        )
        assert parse_modlist_file(f) == ["2009463077", "1234567890"]

    def test_comments_and_blanks(self, tmp_path: Path):
        f = tmp_path / "list.txt"
        f.write_text("# comment line\n\n2009463077\n  \n# another comment\n")
        assert parse_modlist_file(f) == ["2009463077"]

    def test_empty_file(self, tmp_path: Path):
        f = tmp_path / "list.txt"
        f.write_text("")
        assert parse_modlist_file(f) == []


class TestLegacyCollection:
    def test_header_format(self):
        # 4-byte count (2) + 2 × 8-byte IDs
        count = struct.pack("<I", 2)
        id1 = struct.pack("<Q", 1111111111)
        id2 = struct.pack("<Q", 2222222222)
        data = count + id1 + id2
        assert _parse_legacy_collection(data) == ["1111111111", "2222222222"]

    def test_flat_sequence(self):
        # Flat sequence of 8-byte IDs (no count header)
        data = struct.pack("<Q", 1111111111) + struct.pack("<Q", 2222222222)
        assert _parse_legacy_collection(data) == ["1111111111", "2222222222"]

    def test_empty_data(self):
        assert _parse_legacy_collection(b"") == []
        assert _parse_legacy_collection(b"\x00\x00\x00") == []

    def test_filters_out_of_range(self):
        data = struct.pack("<Q", 99999999999)  # > 10 billion, should be filtered
        assert _parse_legacy_collection(data) == []


class TestParseCollectionDir:
    def test_legacy_bin(self, tmp_path: Path):
        d = tmp_path / "collection_123"
        d.mkdir()
        count = struct.pack("<I", 1)
        wid = struct.pack("<Q", 2009463077)
        (d / "something_legacy.bin").write_bytes(count + wid)
        assert parse_collection_dir(d) == ["2009463077"]

    def test_json_format(self, tmp_path: Path):
        d = tmp_path / "collection_123"
        d.mkdir()
        (d / "collection.json").write_text(
            json.dumps({"children": [{"publishedfileid": "2009463077"}]})
        )
        assert parse_collection_dir(d) == ["2009463077"]


class TestParseModsConfig:
    def test_basic(self, tmp_path: Path):
        f = tmp_path / "ModsConfig.xml"
        f.write_text(
            "<ModsConfigData><activeMods><li>author.mod1</li><li>author.mod2</li></activeMods></ModsConfigData>"
        )
        assert parse_mods_config(f) == ["author.mod1", "author.mod2"]


class TestInstalledPackageIds:
    def test_extracts_from_about_xml(self, tmp_path: Path):
        d = tmp_path / "some_mod"
        d.mkdir()
        (d / "About").mkdir()
        (d / "About" / "About.xml").write_text(
            "<ModMetaData><packageId>author.mod1</packageId></ModMetaData>"
        )
        assert get_installed_package_ids(tmp_path) == {"author.mod1"}


class TestResolveWorkshopIds:
    def test_resolves_known_ids(self, tmp_path: Path):
        d = tmp_path / "mod1"
        d.mkdir()
        (d / "About").mkdir()
        (d / "About" / "About.xml").write_text(
            "<ModMetaData><packageId>author.mod1</packageId></ModMetaData>"
        )
        (d / "About" / "PublishedFileId.txt").write_text("2009463077")
        known, unknown = resolve_workshop_ids(["author.mod1", "unknown.mod"], tmp_path)
        assert known == ["2009463077"]
        assert unknown == ["unknown.mod"]

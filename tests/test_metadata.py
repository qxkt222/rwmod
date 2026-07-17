"""Test metadata: shared XML parsing across server and downloader."""

from __future__ import annotations

from pathlib import Path

from rwmod.metadata import read_mod_metadata


class TestReadModMetadata:
    def test_full_metadata(self, tmp_path: Path):
        d = tmp_path / "test_mod"
        d.mkdir()
        (d / "About").mkdir()
        (d / "About" / "About.xml").write_text(
            "<ModMetaData><name>Test Mod</name><packageId>author.test</packageId></ModMetaData>"
        )
        (d / "About" / "PublishedFileId.txt").write_text("123456")
        meta = read_mod_metadata(d)
        assert meta is not None
        assert meta.name == "Test Mod"
        assert meta.package_id == "author.test"
        assert meta.workshop_id == "123456"
        assert meta.folder == "test_mod"

    def test_missing_about_xml(self, tmp_path: Path):
        d = tmp_path / "empty_mod"
        d.mkdir()
        assert read_mod_metadata(d) is None

    def test_not_a_directory(self, tmp_path: Path):
        f = tmp_path / "some_file.txt"
        f.write_text("not a mod")
        assert read_mod_metadata(f) is None

    def test_missing_published_file_id(self, tmp_path: Path):
        d = tmp_path / "mod_no_wid"
        d.mkdir()
        (d / "About").mkdir()
        (d / "About" / "About.xml").write_text(
            "<ModMetaData><name>No WID Mod</name><packageId>no.wid</packageId></ModMetaData>"
        )
        meta = read_mod_metadata(d)
        assert meta is not None
        assert meta.workshop_id == ""

    def test_malformed_xml(self, tmp_path: Path):
        d = tmp_path / "bad_mod"
        d.mkdir()
        (d / "About").mkdir()
        (d / "About" / "About.xml").write_text("<<<not xml>>>")
        meta = read_mod_metadata(d)
        assert meta is not None
        assert meta.name == "?"  # fallback on parse error

"""Tests for load_order.py — mod ordering analysis."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from rwmod.load_order import check_load_order


def _write_modsconfig(path: Path, active_mods: list[str]) -> None:
    root = ET.Element("ModsConfigData")
    ET.SubElement(root, "version").text = "1.0"
    am = ET.SubElement(root, "activeMods")
    for pid in active_mods:
        ET.SubElement(am, "li").text = pid
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    path.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")


class TestCheckLoadOrder:
    def test_harmony_not_first(self, tmp_path: Path):
        cfg = tmp_path / "ModsConfig.xml"
        _write_modsconfig(cfg, ["some.mod", "brrainz.harmony", "other.mod"])
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()

        result = check_load_order(cfg, mods_dir)
        assert not result.get("ok")
        assert any("Harmony" in i["message"] for i in result["issues"])

    def test_harmony_first_is_ok(self, tmp_path: Path):
        cfg = tmp_path / "ModsConfig.xml"
        _write_modsconfig(cfg, ["brrainz.harmony", "some.mod"])
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()

        result = check_load_order(cfg, mods_dir)
        assert result["ok"]

    def test_duplicate_detected(self, tmp_path: Path):
        cfg = tmp_path / "ModsConfig.xml"
        _write_modsconfig(cfg, ["brrainz.harmony", "mod.a", "mod.a"])
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()

        result = check_load_order(cfg, mods_dir)
        assert any("重复" in i["message"] for i in result["issues"])

    def test_missing_config(self, tmp_path: Path):
        result = check_load_order(tmp_path / "nonexistent.xml", tmp_path / "Mods")
        assert "error" in result

    def test_known_conflict(self, tmp_path: Path):
        cfg = tmp_path / "ModsConfig.xml"
        _write_modsconfig(cfg, ["brrainz.harmony", "combat_extended", "yayo.combat"])
        mods_dir = tmp_path / "Mods"
        mods_dir.mkdir()

        result = check_load_order(cfg, mods_dir)
        assert any("冲突" in i["message"] for i in result["issues"])

"""CLI entry point — all commands live here."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import typer

from rwmod.config import Config
from rwmod.downloader import download_one, extract_mod_id
from rwmod.parser import (
    get_installed_package_ids,
    parse_collection_dir,
    parse_modlist_file,
    parse_mods_config,
    resolve_workshop_ids,
)
from rwmod.steamcmd import SteamCMD

app = typer.Typer(help="RimWorld Mod CLI — SteamCMD-powered, zero GUI")


# ── setup ──────────────────────────────────────────────────────────


@app.command()
def setup() -> None:
    """交互式设置 SteamCMD 路径、Mods 目录和游戏目录."""
    config = Config.load()

    sc = typer.prompt("SteamCMD 路径 (steamcmd.exe)", default=str(config.steamcmd_path))
    md = typer.prompt("RimWorld Mods 目录", default=str(config.mods_dir))
    rd = typer.prompt("RimWorld 游戏目录 (用于 import-sort)", default=str(config.rimworld_dir))

    config.steamcmd_path = Path(sc)
    config.mods_dir = Path(md)
    config.rimworld_dir = Path(rd)
    config.save()

    typer.echo()
    typer.echo(f"✓ 配置已保存 → {Config.CONFIG_PATH}")


# ── config ─────────────────────────────────────────────────────────


@app.command(name="config")
def show_config() -> None:
    """显示当前配置."""
    cfg = Config.load()
    typer.echo(f"配置文件:  {Config.CONFIG_PATH}")
    typer.echo(f"SteamCMD:   {cfg.steamcmd_path}")
    typer.echo(f"Mods 目录:  {cfg.mods_dir}")
    typer.echo(f"游戏目录:   {cfg.rimworld_dir}")


# ── download ───────────────────────────────────────────────────────


@app.command()
def download(
    ids: list[str] = typer.Argument(..., help="Mod ID(s) 或 Steam Workshop URL(s)"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的 mod"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="只输出结果，不显示详细日志"),
) -> None:
    """下载 Mod(s) 并复制到 Mods 目录."""
    cfg = Config.load()
    cfg.validate()

    parsed: list[str] = []
    for raw in ids:
        mid = extract_mod_id(raw)
        if mid:
            parsed.append(mid)
        else:
            typer.echo(f"⚠ 跳过无效输入: {raw}", err=True)

    if not parsed:
        typer.echo("没有可下载的 Mod ID", err=True)
        raise typer.Exit(1)

    ok = 0
    total = len(parsed)
    for i, mid in enumerate(parsed, 1):
        if quiet:
            typer.echo(f"[{i}/{total}] {mid} ... ", nl=False)
        else:
            typer.echo(f"\n{'─' * 50}")
            typer.echo(f"[{i}/{total}] Mod {mid}")
        if download_one(cfg, mid, force=force):
            ok += 1
            if quiet:
                typer.echo("✓")
        elif quiet:
            typer.echo("✗")

    typer.echo(f"\n完成: {ok}/{total} 成功")


# ── import ─────────────────────────────────────────────────────────


@app.command(name="import")
def import_cmd(
    file: Path = typer.Argument(..., help="Mod ID 列表文件 (每行一个 ID 或 URL)"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的 mod"),
) -> None:
    """从文件批量下载 Mod."""
    cfg = Config.load()
    cfg.validate()

    if not file.exists():
        typer.echo(f"文件不存在: {file}", err=True)
        raise typer.Exit(1)

    mod_ids = parse_modlist_file(file)
    if not mod_ids:
        typer.echo("未找到有效 Mod ID")
        raise typer.Exit(1)

    _batch_download(cfg, mod_ids, force)


# ── import-collection ──────────────────────────────────────────────


@app.command(name="import-collection")
def import_collection(
    collection_id: str = typer.Argument(..., help="Steam 合集 ID"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的 mod"),
) -> None:
    """下载整个 Steam 合集（先通过 SteamCMD 下载合集元数据再解析）."""
    cfg = Config.load()
    cfg.validate()

    steamcmd = SteamCMD(cfg.steamcmd_path)

    typer.echo(f"正在获取合集 {collection_id} 的元数据...")
    rc, lines = steamcmd.workshop_download(collection_id)
    for line in lines:
        low = line.lower()
        if any(kw in low for kw in ("download", "success", "error", "fail")):
            typer.echo(f"  {line}")

    if rc != 0:
        typer.echo("获取合集元数据失败", err=True)
        raise typer.Exit(1)

    col_dir = steamcmd.workshop_content_dir / collection_id
    mod_ids = parse_collection_dir(col_dir)
    if not mod_ids:
        typer.echo("未能解析合集内容（可能格式不支持）", err=True)
        raise typer.Exit(1)

    typer.echo(f"合集包含 {len(mod_ids)} 个 Mod")
    _batch_download(cfg, mod_ids, force)


# ── import-sort ────────────────────────────────────────────────────


@app.command(name="import-sort")
def import_sort(
    mods_config_xml: Path = typer.Argument(..., help="RimSort ModsConfig.xml 路径"),
    force: bool = typer.Option(False, "--force", "-f", help="覆盖已存在的 mod"),
) -> None:
    """解析 ModsConfig.xml，下载缺失的 mod."""
    cfg = Config.load()
    cfg.validate()

    if not mods_config_xml.exists():
        typer.echo(f"文件不存在: {mods_config_xml}", err=True)
        raise typer.Exit(1)

    package_ids = parse_mods_config(mods_config_xml)
    if not package_ids:
        typer.echo("ModsConfig.xml 中未找到 mod 列表")
        raise typer.Exit(1)

    installed = get_installed_package_ids(cfg.mods_dir)
    missing = [pid for pid in package_ids if pid not in installed]

    if not missing:
        typer.echo("所有 mod 已安装 ✓")
        return

    typer.echo(f"缺失 {len(missing)} 个 Mod (共 {len(package_ids)} 个)")
    known, unknown = resolve_workshop_ids(missing, cfg.mods_dir)

    if unknown:
        typer.echo(f"  ⚠ {len(unknown)} 个 PackageId 无法解析为 Workshop ID，跳过")
        for pid in unknown:
            typer.echo(f"    - {pid}")

    if known:
        _batch_download(cfg, known, force)
    else:
        typer.echo("没有可下载的 Mod（所有缺失项的 Workshop ID 均无法解析）")


# ── list ───────────────────────────────────────────────────────────


@app.command(name="list")
def list_mods() -> None:
    """列出已安装的 Mod."""
    cfg = Config.load()
    if not cfg.mods_dir.exists():
        typer.echo(f"Mods 目录不存在: {cfg.mods_dir}")
        return

    entries: list[tuple[str, str, str]] = []
    for d in sorted(cfg.mods_dir.iterdir()):
        if not d.is_dir():
            continue
        about = d / "About" / "About.xml"
        name = "?"
        pkg = ""
        if about.exists():
            try:
                root = ET.parse(about).getroot()
                name = root.findtext("name", "?") or "?"
                pkg = root.findtext("packageId", "") or ""
            except Exception:
                pass

        pf = d / "About" / "PublishedFileId.txt"
        wid = pf.read_text(encoding="utf-8").strip() if pf.exists() else ""
        entries.append((d.name, name, pkg, wid))

    typer.echo(f"\n已安装 Mod ({len(entries)} 个):\n")
    for folder, name, pkg, wid in entries:
        typer.echo(f"  {folder}")
        typer.echo(f"    名称:       {name}")
        if pkg:
            typer.echo(f"    PackageId:  {pkg}")
        if wid:
            typer.echo(f"    Workshop:   {wid}")
        typer.echo()


# ── profile ────────────────────────────────────────────────────────


@app.command(name="profile-save")
def profile_save(
    name: str = typer.Argument(..., help="Profile 名称（如：原版、中世纪）"),
) -> None:
    """保存当前 ModsConfig.xml 为命名 profile."""
    cfg = Config.load()
    from rwmod.profile import resolve_modsconfig_path, save_profile

    source = resolve_modsconfig_path(cfg.rimworld_dir)
    if not source:
        typer.echo("未找到 ModsConfig.xml，从已安装 Mod 生成中...")
        from rwmod.rimsort import generate_modsconfig

        xml_str = generate_modsconfig(cfg.mods_dir)
        result = save_profile(name, xml_str)
    else:
        result = save_profile(name, source)
    typer.echo(result["msg"])


@app.command(name="profile-list")
def profile_list() -> None:
    """列出所有保存的 profile."""
    from rwmod.profile import list_profiles

    profiles = list_profiles()
    if not profiles:
        typer.echo("暂无存档 profile")
        return
    typer.echo(f"\n已保存的 Profile ({len(profiles)} 个):\n")
    for p in profiles:
        typer.echo(
            f"  💾 {p['name']}  —  {p['mod_count']} Mod  ·  {p['saved_at'][:16].replace('T', ' ')}  ·  {p['size_kb']} KB"
        )


@app.command(name="profile-restore")
def profile_restore(
    name: str = typer.Argument(..., help="Profile 名称"),
) -> None:
    """恢复指定 profile 到 ModsConfig.xml."""
    cfg = Config.load()
    from rwmod.profile import resolve_modsconfig_path, restore_profile

    target = resolve_modsconfig_path(cfg.rimworld_dir) or (cfg.rimworld_dir / "ModsConfig.xml")
    result = restore_profile(name, target)
    typer.echo(result["msg"])


@app.command(name="profile-delete")
def profile_delete(
    name: str = typer.Argument(..., help="Profile 名称"),
) -> None:
    """删除指定 profile."""
    from rwmod.profile import delete_profile

    ok = delete_profile(name)
    typer.echo("已删除" if ok else "Profile 不存在")


# ── backup ─────────────────────────────────────────────────────────


@app.command(name="backup-list")
def backup_list(
    mod_id: str = typer.Option("", "--mod", "-m", help="按 Workshop ID 过滤"),
) -> None:
    """列出所有 Mod 备份."""
    cfg = Config.load()
    from rwmod.backup import list_backups

    backups = list_backups(cfg.backup_dir, workshop_id=mod_id if mod_id.strip() else None)
    if not backups:
        typer.echo("暂无备份")
        return
    typer.echo(f"\nMod 备份 ({len(backups)} 个):\n")
    for b in backups:
        typer.echo(
            f"  💾 {b['folder_name']}  ·  {b['workshop_id']}  ·  {b['timestamp'][:16].replace('T', ' ')}  ·  {b['size_mb']} MB"
        )


@app.command(name="backup-restore")
def backup_restore(
    mod_id: str = typer.Argument(..., help="Workshop ID"),
) -> None:
    """恢复 Mod 的最新备份."""
    cfg = Config.load()
    from rwmod.backup import restore_mod

    result = restore_mod(cfg.mods_dir, mod_id, cfg.backup_dir)
    typer.echo(result["msg"])


@app.command(name="backup-cleanup")
def backup_cleanup(
    keep: int = typer.Option(5, "--keep", "-k", help="每个 Mod 保留几个备份"),
) -> None:
    """清理旧备份，每个 Mod 只保留最近 N 个."""
    cfg = Config.load()
    from rwmod.backup import cleanup_backups

    deleted = cleanup_backups(cfg.backup_dir, keep_per_mod=keep)
    typer.echo(f"已清理 {deleted} 个旧备份（每个 Mod 保留 {keep} 个）")


# ── compatibility ──────────────────────────────────────────────────


@app.command(name="compat")
def compat_check() -> None:
    """检查 Mod 版本兼容性."""
    cfg = Config.load()
    from rwmod.compatibility import check_compatibility, detect_rimworld_version
    from rwmod.mod_cache import get_cached_mods

    rw_ver = detect_rimworld_version(cfg.rimworld_dir)
    if not rw_ver:
        typer.echo("未能检测到 RimWorld 版本", err=True)
        return

    metas = get_cached_mods(cfg.mods_dir)
    groups = check_compatibility(metas, rw_ver)

    typer.echo(f"\nRimWorld {rw_ver}\n")
    typer.echo(f"  ✅ 兼容:  {len(groups['compatible'])}")
    typer.echo(f"  ❌ 不兼容: {len(groups['incompatible'])}")
    typer.echo(f"  ❓ 未知:   {len(groups['unknown'])}")

    if groups["incompatible"]:
        typer.echo("\n⚠ 不兼容的 Mod:")
        for m in groups["incompatible"]:
            vers = ", ".join(m["supported"]) if m["supported"] else "无"
            typer.echo(f"  - {m['name']} (支持: {vers})")


# ── load-order ─────────────────────────────────────────────────────


@app.command(name="check-order")
def check_load_order() -> None:
    """分析 ModsConfig.xml 加载顺序，检测常见问题."""
    cfg = Config.load()
    from rwmod.load_order import check_load_order as _check
    from rwmod.profile import resolve_modsconfig_path

    path = resolve_modsconfig_path(cfg.rimworld_dir) or (cfg.rimworld_dir / "ModsConfig.xml")
    result = _check(path, cfg.mods_dir)

    if "error" in result:
        typer.echo(result["error"], err=True)
        return

    typer.echo(f"\n排序分析 — {result['total_mods']} 个 Mod\n")
    issues = result.get("issues", [])
    if not issues:
        typer.echo("  ✅ 未发现排序问题")
    for i in issues:
        icon = {"error": "🔴", "warn": "🟡", "info": "🔵"}.get(i["severity"], "")
        typer.echo(f"  {icon} {i['message']}")


# ── helpers ────────────────────────────────────────────────────────


def _batch_download(cfg: Config, mod_ids: list[str], force: bool) -> None:
    ok = 0
    total = len(mod_ids)
    for i, mid in enumerate(mod_ids, 1):
        typer.echo(f"\n[{i}/{total}] Mod {mid}")
        if download_one(cfg, mid, force=force):
            ok += 1

    typer.echo(f"\n{'=' * 50}")
    typer.echo(f"批量完成: {ok}/{total} 成功")


if __name__ == "__main__":
    app()

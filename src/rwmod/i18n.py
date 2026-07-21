"""i18n — lightweight internationalization for rwmod.

Uses JSON translation files in src/rwmod/i18n/.
Falls back to zh-CN when a key is missing in the active language.

Usage:
    from rwmod.i18n import t, set_locale
    set_locale("en")
    print(t("mods.title"))  # "Mods" or "Mod 列表"
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["t", "set_locale", "get_locale", "AVAILABLE_LOCALES"]

_I18N_DIR = Path(__file__).resolve().parent / "i18n"
_DEFAULT_LOCALE = "zh-CN"
_current_locale = _DEFAULT_LOCALE
_translations: dict[str, dict[str, str]] = {}
_fallback: dict[str, str] = {}
_loaded_locales: set[str] = set()

AVAILABLE_LOCALES = {"zh-CN": "简体中文", "en": "English"}


def set_locale(locale: str) -> None:
    """Switch to the given locale. Loads translations lazily."""
    global _current_locale
    if locale in AVAILABLE_LOCALES:
        _current_locale = locale
        _ensure_loaded(locale)
        _ensure_loaded(_DEFAULT_LOCALE)


def get_locale() -> str:
    """Return the currently active locale code."""
    return _current_locale


def t(key: str, **kwargs) -> str:
    """Translate a key to the current locale. Supports format placeholders.

    Args:
        key: Dot-notation key like 'mods.count'.
        **kwargs: Values for format placeholders, e.g. count=5.

    Returns:
        Translated string, or the key itself if not found.
    """
    _ensure_loaded(_current_locale)

    # Try current locale first, then fallback
    text = _translations.get(_current_locale, {}).get(key)
    if text is None and _current_locale != _DEFAULT_LOCALE:
        text = _translations.get(_DEFAULT_LOCALE, {}).get(key)

    if text is None:
        return key

    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


def _ensure_loaded(locale: str) -> None:
    if locale in _loaded_locales:
        return

    # Load translations from built-in dicts (keeps single-file distribution)
    if locale not in _translations:
        _translations[locale] = _get_builtin(locale)
    _loaded_locales.add(locale)


def _get_builtin(locale: str) -> dict[str, str]:
    """Return built-in translations for a locale.

    For production, these could be loaded from JSON files.
    For distribution simplicity, they're inline.
    """
    if locale == "en":
        return {
            "ui.title": "rwmod · RimWorld Mod Manager",
            "ui.dashboard": "Dashboard",
            "ui.download": "Download",
            "ui.collection": "Collection",
            "ui.import": "Import",
            "ui.mods": "Mods",
            "ui.search": "Search",
            "ui.queue": "Queue",
            "ui.updates": "Updates",
            "ui.rimsort": "RimSort",
            "ui.profiles": "Profiles",
            "ui.history": "History",
            "ui.backups": "Backups",
            "ui.config": "Settings",
            "ui.saves": "Saves",
            "ui.tags": "Tags",
            "ui.refresh": "Refresh",
            "ui.dark_mode": "Dark Mode",
            "ui.online": "Online",
            "ui.offline": "Offline",
            "mods.count": "{count} mods",
            "mods.no_mods": "No mods installed",
            "mods.compatible": "Compatible",
            "mods.incompatible": "Incompatible",
            "mods.unknown": "Unknown version",
            "download.success": "Download complete",
            "download.failed": "Download failed",
            "download.skipped": "Already installed",
            "queue.empty": "Queue is empty",
            "queue.processing": "Processing {n} items",
            "backup.created": "Backup created",
            "backup.restored": "Backup restored",
            "save.loadable": "Loadable",
            "save.missing_mods": "Missing {n} mod(s)",
            "save.unused_mods": "{n} unused mod(s)",
        }
    # zh-CN (default)
    return {
        "ui.title": "rwmod · RimWorld Mod 管理器",
        "ui.dashboard": "首页",
        "ui.download": "下载",
        "ui.collection": "合集",
        "ui.import": "导入",
        "ui.mods": "Mods",
        "ui.search": "搜索",
        "ui.queue": "队列",
        "ui.updates": "更新",
        "ui.rimsort": "RimSort",
        "ui.profiles": "配置档案",
        "ui.history": "历史",
        "ui.backups": "备份",
        "ui.config": "设置",
        "ui.saves": "存档",
        "ui.tags": "标签",
        "ui.refresh": "刷新",
        "ui.dark_mode": "深色模式",
        "ui.online": "在线",
        "ui.offline": "离线",
        "mods.count": "{count} 个 Mod",
        "mods.no_mods": "没有安装的 Mod",
        "mods.compatible": "兼容",
        "mods.incompatible": "不兼容",
        "mods.unknown": "未知版本",
        "download.success": "下载完成",
        "download.failed": "下载失败",
        "download.skipped": "已安装",
        "queue.empty": "队列为空",
        "queue.processing": "正在处理 {n} 项",
        "backup.created": "备份已创建",
        "backup.restored": "备份已恢复",
        "save.loadable": "可加载",
        "save.missing_mods": "缺少 {n} 个 Mod",
        "save.unused_mods": "{n} 个未使用的 Mod",
    }

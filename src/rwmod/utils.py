from __future__ import annotations

import re

"""Shared utilities - mod ID extraction, safe filenames, and common helpers.

All modules that need extract_mod_id or safe_filename should import from here
instead of duplicating the logic across backup.py, profile.py, and downloader.py.
"""

__all__ = ["extract_mod_id", "safe_filename"]


def extract_mod_id(raw: str) -> str:
    """Extract a numeric workshop/mod ID from a URL or raw string.

    Handles:
        - Raw IDs: "2009463077"
        - Steam URLs: "https://steamcommunity.com/sharedfiles/filedetails/?id=2009463077"
        - Workshop URLs: "https://steamcommunity.com/workshop/filedetails/?id=2009463077"

    Returns the numeric ID string, or empty string if not parseable.
    """
    raw = raw.strip()
    if not raw:
        return ""
    m = re.search(r"[?&]id=(\d+)", raw)
    if m:
        return m.group(1)
    if raw.isdigit():
        return raw
    return ""


def safe_filename(name: str, allow_empty: bool = False) -> str:
    r"""Replace filesystem-unfriendly characters in a name.

    Removes characters that are invalid in Windows/Unix filenames:
    < > : " / \ | ? *
    Also strips leading/trailing dots and spaces.

    Args:
        name: The raw name to sanitize.
        allow_empty: If False, returns "unnamed" when the result is empty
                     after sanitization. If True, returns the empty string.

    Returns:
        A safe filename string.
    """
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name.strip()).strip("._")
    if not sanitized and not allow_empty:
        sanitized = "unnamed"
    return sanitized

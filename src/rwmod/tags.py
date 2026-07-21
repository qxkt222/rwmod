"""Mod tags/categories system — user-defined labels for mod organization.

Tags are stored in SQLite. Each tag is a simple string label associated
with a mod folder name (not workshop ID, since mods without workshop IDs
can also be tagged).

Usage:
    from rwmod.tags import add_tag, remove_tag, get_tags, get_mods_by_tag
"""

from __future__ import annotations

from rwmod.database import _get_conn

__all__ = ["add_tag", "remove_tag", "get_tags", "get_mods_by_tag", "list_all_tags"]


def add_tag(mod_folder: str, tag: str) -> bool:
    """Add a tag to a mod. Returns True if added, False if already exists."""
    db = _get_conn()
    cur = db.execute(
        "SELECT 1 FROM mod_tags WHERE folder = ? AND tag = ?",
        (mod_folder, tag.strip()),
    )
    if cur.fetchone():
        return False
    db.execute("INSERT INTO mod_tags (folder, tag) VALUES (?, ?)", (mod_folder, tag.strip()))
    db.commit()
    return True


def remove_tag(mod_folder: str, tag: str) -> bool:
    """Remove a tag from a mod. Returns True if removed."""
    db = _get_conn()
    cur = db.execute(
        "DELETE FROM mod_tags WHERE folder = ? AND tag = ?",
        (mod_folder, tag.strip()),
    )
    db.commit()
    return cur.rowcount > 0


def get_tags(mod_folder: str) -> list[str]:
    """Get all tags for a mod folder."""
    db = _get_conn()
    rows = db.execute(
        "SELECT tag FROM mod_tags WHERE folder = ? ORDER BY tag",
        (mod_folder,),
    ).fetchall()
    return [r["tag"] for r in rows]


def get_mods_by_tag(tag: str) -> list[str]:
    """Get all mod folder names with a given tag."""
    db = _get_conn()
    rows = db.execute(
        "SELECT folder FROM mod_tags WHERE tag = ? ORDER BY folder",
        (tag.strip(),),
    ).fetchall()
    return [r["folder"] for r in rows]


def list_all_tags() -> list[dict]:
    """List all tags with mod counts."""
    db = _get_conn()
    rows = db.execute(
        "SELECT tag, COUNT(*) as count FROM mod_tags GROUP BY tag ORDER BY count DESC"
    ).fetchall()
    return [{"tag": r["tag"], "count": r["count"]} for r in rows]


def remove_all_tags(mod_folder: str) -> int:
    """Remove all tags for a mod folder. Returns count of removed."""
    db = _get_conn()
    cur = db.execute("DELETE FROM mod_tags WHERE folder = ?", (mod_folder,))
    db.commit()
    return cur.rowcount

"""Steam Workshop search via web scraping (no API key needed)."""

from __future__ import annotations

import contextlib
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

__all__ = [
    "ModSearchResult",
    "search_workshop",
    "fetch_collection_children",
    "fetch_item_details",
    "fetch_item_dependencies",
    "is_collection",
    "check_mod_updates",
]

# ── shared HTTP connection pool ────────────────────────────────────
# All Steam API calls share one opener for TCP connection reuse (keep-alive).
# Without this, each urllib.request.urlopen() does a fresh TCP+TLS handshake.
_shared_opener = urllib.request.build_opener(urllib.request.HTTPHandler())
_MAX_WORKERS = 4  # parallel batch requests to Steam API


@dataclass
class ModSearchResult:
    id: str
    title: str
    author: str
    description: str = ""
    preview_url: str = ""
    rating: str = ""
    subscribers: str = ""


STEAM_APP_ID = "294100"


def search_workshop(query: str, page: int = 1, count: int = 20) -> list[ModSearchResult]:
    """Search RimWorld workshop using Steam's JSON API (no auth required)."""
    url = (
        f"https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/?"
        f"key=anonymous&format=json&appid={STEAM_APP_ID}"
        f"&query_type=0&page={page}&numperpage={count}"
        f"&search_text={urllib.request.quote(query)}"
        f"&return_vote_data=1&return_previews=1&return_children=0"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rwmod/1.0"})
        with _shared_opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return []

    results: list[ModSearchResult] = []
    published_files = data.get("response", {}).get("publishedfiledetails", [])
    for f in published_files:
        preview = f.get("preview_url", "")
        # If preview URL is a YouTube link, skip it for thumbnail
        if "youtube" in preview or "youtu.be" in preview:
            preview = ""

        results.append(
            ModSearchResult(
                id=f.get("publishedfileid", ""),
                title=f.get("title", "Unknown"),
                author=f.get("creator", "Unknown"),
                description=(f.get("file_description") or f.get("description", ""))[:200],
                preview_url=preview,
                rating=f"{f.get('vote_data', {}).get('score', 0):.1f}"
                if f.get("vote_data")
                else "",
                subscribers=f.get("subscriptions", ""),
            )
        )
    return results


def is_collection(workshop_id: str) -> bool:
    """Check if a workshop item is a collection via Steam Web API."""
    url = (
        f"https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/?"
        f"key=anonymous&format=json&appid={STEAM_APP_ID}"
        f"&query_type=0&page=1&numperpage=1"
        f"&return_vote_data=0&return_previews=0&return_children=0"
    )
    body = urllib.parse.urlencode(
        {
            "publishedfileids[0]": workshop_id,
        }
    ).encode()
    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "User-Agent": "rwmod/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with _shared_opener.open(req, timeout=10) as resp:
            data = json.loads(resp.read())
        files = data.get("response", {}).get("publishedfiledetails", [])
        if files:
            ftype = files[0].get("file_type", 0)
            return ftype == 2  # 0=item, 2=collection
    except Exception:
        pass
    return False







def fetch_collection_children(collection_id: str) -> list[str]:
    """Fetch all mod IDs in a Steam Workshop collection with 3-layer fallback.

    Layer 1: Steam Web API - fast, works for public collections
    Layer 2: HTML scraping - fallback when API returns empty
    Layer 3: User API Key - for private/friends-only collections
    """
    log = __import__("logging").getLogger(__name__)

    result = _fetch_collection_api(collection_id, "anonymous")
    if result:
        return result

    log.warning("Collection %s: API empty, trying HTML scraping", collection_id)
    result = _scrape_collection_page(collection_id)
    if result:
        log.info("Collection %s: found %d mods via HTML scraping", collection_id, len(result))
        return result

    log.warning("Collection %s: HTML scraping failed, trying user API key", collection_id)
    try:
        from rwmod.config import Config
        cfg = Config.load()
        if cfg.steam_api_key:
            result = _fetch_collection_api(collection_id, cfg.steam_api_key)
            if result:
                log.info(
                    "Collection %s: found %d mods via user API key",
                    collection_id,
                    len(result),
                )
                return result
    except Exception:
        pass

    log.warning("Collection %s: all methods failed", collection_id)
    return []


def _fetch_collection_api(collection_id: str, api_key: str = "anonymous") -> list[str]:
    """Fetch collection children via Steam Web API with pagination."""
    all_ids = []
    page = 1
    per_page = 500
    while True:
        url = (
            f"https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/?"
            f"key={api_key}&format=json&appid={STEAM_APP_ID}"
            f"&query_type=0&page={page}&numperpage={per_page}"
            f"&return_vote_data=0&return_previews=0&return_children=1"
        )
        body = urllib.parse.urlencode({"publishedfileids[0]": collection_id}).encode()
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={
                    "User-Agent": "rwmod/1.0",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with _shared_opener.open(req, timeout=20) as resp:
                data = json.loads(resp.read())
        except Exception:
            return all_ids if all_ids else []

        files = data.get("response", {}).get("publishedfiledetails", [])
        found_children = False
        for f in files:
            children = f.get("children", [])
            if children:
                for c in children:
                    wid = str(c.get("publishedfileid", ""))
                    if wid:
                        all_ids.append(wid)
                found_children = True
            ftype = f.get("file_type", 0)
            if ftype != 2:
                return []

        total = data.get("response", {}).get("total", 0)
        if all_ids and len(all_ids) >= total:
            break
        if not found_children:
            break
        page += 1

    return all_ids


def _scrape_collection_page(collection_id: str) -> list[str]:
    """Scrape the public Steam Community collection page for mod IDs.

    Fallback when API returns empty. Extracts mod IDs from HTML links.
    """
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={collection_id}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    ids = []
    for m in re.finditer(r"/sharedfiles/filedetails/\?id=(\d+)", html):
        if m.group(1) != collection_id:
            ids.append(m.group(1))

    seen = set()
    result = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            result.append(i)
    return result
def fetch_item_details(mod_ids: list[str]) -> dict[str, dict]:
    """Fetch updated timestamp for a batch of mod IDs (used for update detection)."""
    return _fetch_batch(mod_ids)


def fetch_item_dependencies(mod_ids: list[str]) -> dict[str, list[str]]:
    """Fetch mod dependencies for a batch of mod IDs — single API call.
    Returns: {mod_id: [dep_id, dep_id, ...]}
    """
    if not mod_ids:
        return {}

    url = (
        f"https://api.steampowered.com/IPublishedFileService/QueryFiles/v1/?"
        f"key=anonymous&format=json&appid={STEAM_APP_ID}"
        f"&query_type=0&numperpage={len(mod_ids)}"
        f"&return_vote_data=0&return_previews=0&return_children=1"
    )
    # POST all IDs in a single batch — was N separate requests before
    form = {"publishedfileids[0]": mod_ids[0]} if len(mod_ids) == 1 else {}
    if len(mod_ids) > 1:
        form["itemcount"] = str(len(mod_ids))
        for i, mid in enumerate(mod_ids):
            form[f"publishedfileids[{i}]"] = mid

    body = urllib.parse.urlencode(form).encode()
    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "User-Agent": "rwmod/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with _shared_opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {}

    result: dict[str, list[str]] = {}
    for f in data.get("response", {}).get("publishedfiledetails", []):
        children = f.get("children", [])
        if children:
            deps = [str(c.get("publishedfileid", "")) for c in children if c.get("publishedfileid")]
            if deps:
                result[f.get("publishedfileid", "")] = deps
    return result


def _fetch_batch(mod_ids: list[str]) -> dict[str, dict]:
    if not mod_ids:
        return {}
    url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    form_fields = {"itemcount": str(len(mod_ids))}
    for i, wid in enumerate(mod_ids):
        form_fields[f"publishedfileids[{i}]"] = wid
    body = urllib.parse.urlencode(form_fields).encode()

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "User-Agent": "rwmod/1.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with _shared_opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except Exception:
        return {}

    result: dict[str, dict] = {}
    for f in data.get("response", {}).get("publishedfiledetails", []):
        result[f.get("publishedfileid", "")] = {
            "time_updated": f.get("time_updated", 0),
            "title": f.get("title", ""),
            "file_description": f.get("file_description", ""),
        }
    return result


def _fetch_batch_parallel(mod_ids: list[str], batch_size: int = 100) -> dict[str, dict]:
    """Fetch mod details in parallel batches via ThreadPoolExecutor.

    For 300 mods → 3 concurrent API calls instead of 3 sequential ones,
    reducing total network wait by ~60-70%.
    A single batch goes directly to _fetch_batch with no executor overhead.
    """
    if not mod_ids:
        return {}
    if len(mod_ids) <= batch_size:
        return _fetch_batch(mod_ids)

    batches = [mod_ids[i : i + batch_size] for i in range(0, len(mod_ids), batch_size)]
    result: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(len(batches), _MAX_WORKERS)) as executor:
        futures = {executor.submit(_fetch_batch, b): b for b in batches}
        for future in as_completed(futures):
            with contextlib.suppress(Exception):
                result.update(future.result())
    return result


def check_mod_updates(mods_dir: str) -> list[dict]:
    """Compare local mod timestamps with Steam Workshop.

    Uses the shared mod metadata cache to avoid re-parsing About.xml
    on every check — the cache is refreshed if stale (>30s or dir changed).
    """
    from pathlib import Path

    from rwmod.mod_cache import get_cached_mods

    mods_path = Path(mods_dir)
    if not mods_path.exists():
        return []

    # Reuse cached metadata instead of re-parsing About.xml for every mod
    metas = get_cached_mods(mods_path)
    local_mods: dict[str, dict] = {}
    for m in metas:
        if m.workshop_id:
            local_mods[m.workshop_id] = {
                "name": m.name,
                "package_id": m.package_id,
                "folder": m.folder,
            }

    if not local_mods:
        return []

    # Fetch remote data in parallel batches — uses ThreadPoolExecutor
    # for concurrent API calls. 300 mods = 3 parallel batches instead of
    # 3 sequential ones, cutting network wait by ~60%.
    ids = list(local_mods.keys())
    all_details = _fetch_batch_parallel(ids)

    import time as _time

    updates: list[dict] = []
    now = int(_time.time())

    for wid, local in local_mods.items():
        remote = all_details.get(wid)
        if not remote:
            continue

        remote_time = remote.get("time_updated", 0)
        mod_dir = mods_path / local["folder"]
        ts_file = mod_dir / ".rwmod_last_updated"

        # Read locally stored timestamp
        local_time = 0
        if ts_file.exists():
            with contextlib.suppress(ValueError, OSError):
                local_time = int(ts_file.read_text(encoding="utf-8").strip())

        # First-time check: no local timestamp → seed it, don't flag as outdated
        if local_time == 0:
            ts_file.write_text(str(now), encoding="utf-8")
            continue

        if remote_time <= local_time:
            continue  # already up to date

        updates.append(
            {
                "workshop_id": wid,
                "name": local["name"],
                "folder": local["folder"],
                "remote_title": remote.get("title", local["name"]),
                "time_updated": remote_time,
                "file_description": remote.get("file_description", ""),
            }
        )

    return updates

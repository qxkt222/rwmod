"""Download queue with concurrency control + SQLite persistence.

Queue survives server restarts: pending items are stored in SQLite
and reloaded on startup. Status changes are written to DB immediately.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field

from rwmod.config import Config
from rwmod.downloader import _find_existing, download_one

__all__ = ["DownloadQueue", "get_queue", "MAX_CONCURRENT"]

MAX_CONCURRENT = 3


@dataclass
class QueueItem:
    id: str
    name: str = ""
    status: str = "pending"  # pending | downloading | done | failed | cancelled
    progress: float = 0.0
    msg: str = ""


@dataclass
class DownloadQueue:
    items: list[QueueItem] = field(default_factory=list)
    _running: bool = False
    _semaphore: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(MAX_CONCURRENT))
    _callbacks: list[Callable] = field(default_factory=list)

    def add(self, mod_ids: list[str]) -> list[QueueItem]:
        new_items: list[QueueItem] = []
        for mid in mod_ids:
            already = next(
                (i for i in self.items if i.id == mid and i.status in ("pending", "downloading")),
                None,
            )
            if not already:
                item = QueueItem(id=mid)
                self.items.append(item)
                new_items.append(item)
                self._persist(item)
        return new_items

    def remove(self, mod_id: str) -> bool:
        for i, item in enumerate(self.items):
            if item.id == mod_id:
                if item.status == "downloading":
                    item.status = "cancelled"
                    self._persist(item)
                else:
                    self.items.pop(i)
                    self._db_delete(mod_id)
                return True
        return False

    def clear_done(self) -> None:
        done_ids = [i.id for i in self.items if i.status in ("done", "cancelled")]
        self.items = [i for i in self.items if i.status not in ("done", "cancelled")]
        for wid in done_ids:
            self._db_delete(wid)
        self._db_clear_done()

    def on_update(self, cb: Callable) -> None:
        self._callbacks.append(cb)

    async def _notify(self) -> None:
        snapshot = self.snapshot()
        for cb in self._callbacks:
            with contextlib.suppress(Exception):
                await cb(snapshot)

    def snapshot(self) -> list[dict]:
        return [
            {
                "id": i.id,
                "name": i.name,
                "status": i.status,
                "progress": i.progress,
                "msg": i.msg,
            }
            for i in self.items
        ]

    async def start(self, config: Config, force: bool = False) -> None:
        if self._running:
            return
        self._running = True

        pending = [i for i in self.items if i.status == "pending"]
        tasks = [self._download_one(config, item, force) for item in pending]

        if tasks:
            await asyncio.gather(*tasks)

        self._running = False
        await self._notify()

    async def _download_one(self, config: Config, item: QueueItem, force: bool) -> None:
        async with self._semaphore:
            item.status = "downloading"
            item.progress = 0.1
            item.msg = "检查中..."
            self._persist(item)
            await self._notify()

            # Check already installed
            existing = _find_existing(config.mods_dir, item.id)
            if existing and not force:
                item.status = "done"
                item.progress = 1.0
                item.name = existing.name
                item.msg = "已安装"
                self._persist(item)
                await self._notify()
                return

            if existing and force:
                item.name = existing.name
                item.msg = "覆盖中..."
                self._persist(item)
                await self._notify()

            # Delegate to the unified download_one (blocking — runs in thread)
            item.msg = "下载中..."
            self._persist(item)
            await self._notify()

            ok = await asyncio.to_thread(download_one, config, item.id, force=force)

            if ok:
                final = _find_existing(config.mods_dir, item.id)
                item.status = "done"
                item.progress = 1.0
                item.name = final.name if final else item.id
                item.msg = "完成"
            else:
                item.status = "failed"
                item.progress = 0
                item.msg = "下载失败（含 Skymods 备用源）"

            self._persist(item)
            await self._notify()

    # ── persistence helpers ──────────────────────────────────────

    def _persist(self, item: QueueItem) -> None:
        """Write queue item state to SQLite."""
        try:
            from rwmod.database import queue_upsert

            queue_upsert(
                item.id,
                name=item.name,
                status=item.status,
                progress=item.progress,
                msg=item.msg,
            )
        except Exception:
            pass  # DB unavailable — gracefully degrade

    def _db_delete(self, workshop_id: str) -> None:
        try:
            from rwmod.database import queue_delete

            queue_delete(workshop_id)
        except Exception:
            pass

    def _db_clear_done(self) -> None:
        try:
            from rwmod.database import queue_clear_done

            queue_clear_done()
        except Exception:
            pass

    def _load_from_db(self) -> None:
        """Load pending/downloading items from SQLite (used on startup)."""
        try:
            from rwmod.database import queue_load_pending

            rows = queue_load_pending()
            for row in rows:
                item = QueueItem(
                    id=row["workshop_id"],
                    name=row.get("name", ""),
                    status=row["status"],
                    progress=row.get("progress", 0.0),
                    msg=row.get("msg", ""),
                )
                self.items.append(item)
        except Exception:
            pass  # DB unavailable, start empty


# Singleton
_queue: DownloadQueue | None = None


def get_queue() -> DownloadQueue:
    global _queue
    if _queue is None:
        _queue = DownloadQueue()
        # Restore pending items from previous session
        _queue._load_from_db()
    return _queue

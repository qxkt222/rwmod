"""Download queue with concurrency control — delegates to downloader.download_one."""

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
        return new_items

    def remove(self, mod_id: str) -> bool:
        for i, item in enumerate(self.items):
            if item.id == mod_id:
                if item.status == "downloading":
                    item.status = "cancelled"
                else:
                    self.items.pop(i)
                return True
        return False

    def clear_done(self) -> None:
        self.items = [i for i in self.items if i.status not in ("done", "cancelled")]

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
            await self._notify()

            # Check already installed
            existing = _find_existing(config.mods_dir, item.id)
            if existing and not force:
                item.status = "done"
                item.progress = 1.0
                item.name = existing.name
                item.msg = "已安装"
                await self._notify()
                return

            if existing and force:
                item.name = existing.name
                item.msg = "覆盖中..."
                await self._notify()

            # Delegate to the unified download_one (blocking — runs in thread)
            item.msg = "下载中..."
            await self._notify()

            ok = await asyncio.to_thread(download_one, config, item.id, force=force)

            if ok:
                # Resolve final folder name after download
                final = _find_existing(config.mods_dir, item.id)
                item.status = "done"
                item.progress = 1.0
                item.name = final.name if final else item.id
                item.msg = "完成"
            else:
                item.status = "failed"
                item.progress = 0
                item.msg = "下载失败（含 Skymods 备用源）"

            await self._notify()


# Singleton
_queue: DownloadQueue | None = None


def get_queue() -> DownloadQueue:
    global _queue
    if _queue is None:
        _queue = DownloadQueue()
    return _queue

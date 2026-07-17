"""Auto-update manager — encapsulates background check + manual trigger state."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from rwmod.config import Config

_log = logging.getLogger(__name__)


class AutoUpdateManager:
    """Manages background update polling and manual check trigger.
    Replaces the 4 module-level globals previously scattered in server.py.
    """

    def __init__(self, interval_hours: int = 24) -> None:
        self._interval: int = interval_hours
        self._check_result: list[dict] = []
        self._running: bool = False
        self._bg_task: asyncio.Task[None] | None = None

    # ── public API ─────────────────────────────────────────────────

    @property
    def last_result(self) -> list[dict]:
        return list(self._check_result)

    def clear_result(self) -> None:
        self._check_result.clear()

    @property
    def is_running(self) -> bool:
        return self._running

    async def start_background(self) -> None:
        if self._bg_task is None or self._bg_task.done():
            self._bg_task = asyncio.create_task(self._loop())

    async def stop_background(self) -> None:
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._bg_task

    async def run_check(self) -> dict:
        """Manually trigger an update check and queue outdated mods."""
        if self._running:
            return {"ok": False, "msg": "已在运行中"}

        self._running = True
        try:
            cfg = Config.load()
            from rwmod.workshop import check_mod_updates

            updates = check_mod_updates(str(cfg.mods_dir))

            self._check_result.clear()
            self._check_result.extend(updates)

            outdated_ids = [u["workshop_id"] for u in updates]
            if outdated_ids:
                from rwmod.queue import get_queue

                queue = get_queue()
                queue.add(outdated_ids)
                # force=True: 更新场景必须覆盖现有 Mod，否则 _download_one 会跳过
                await queue.start(cfg, force=True)

            return {
                "checked": len(updates),
                "outdated": len(outdated_ids),
                "queued": len(outdated_ids),
            }
        finally:
            self._running = False

    # ── internal ───────────────────────────────────────────────────

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval * 3600)
            try:
                _log.info("后台更新检查开始...")
                cfg = Config.load()
                from rwmod.workshop import check_mod_updates

                updates = check_mod_updates(str(cfg.mods_dir))
                if updates:
                    _log.info("发现 %s 个可用更新", len(updates))
                    self._check_result.clear()
                    self._check_result.extend(updates)
                else:
                    _log.info("所有 Mod 均为最新")
            except Exception as e:
                _log.error("后台更新检查失败: %s", e)

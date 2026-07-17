/**
 * Backup panel — manage mod backups, restore previous versions.
 * Backups are created automatically when updating mods with force=true.
 */
import { toast } from "../toast";

interface BackupEntry {
  filename: string;
  workshop_id: string;
  folder_name: string;
  timestamp: string;
  size_mb: number;
}

export function initBackupPanel() {
  document.getElementById("btn-backup-refresh")?.addEventListener("click", refreshBackups);
  document.getElementById("btn-backup-cleanup")?.addEventListener("click", cleanupBackups);
  refreshBackups();
}

async function refreshBackups() {
  const container = document.getElementById("backup-list")!;
  container.innerHTML = '<span style="color:var(--gray-text)">加载中...</span>';

  try {
    const resp = await fetch("/api/backups");
    const data = await resp.json();

    if (!data.backups.length) {
      container.innerHTML = '<div style="padding:16px;text-align:center;color:var(--gray-text)">暂无备份。更新 Mod 时会自动创建备份。</div>';
      return;
    }

    const groupLabel = document.getElementById("backup-group-label");
    if (groupLabel) groupLabel.textContent = `备份目录: ${data.backup_dir}`;

    renderBackupList(data.backups, container);
  } catch (e: any) {
    container.innerHTML = `<span style="color:var(--red)">加载失败: ${e.message}</span>`;
  }
}

function renderBackupList(backups: BackupEntry[], container: HTMLElement) {
  // Group by workshop_id
  const groups: Record<string, BackupEntry[]> = {};
  for (const b of backups) {
    (groups[b.workshop_id] ??= []).push(b);
  }

  const parts: string[] = [];
  for (const [wid, items] of Object.entries(groups)) {
    const latest = items[0]; // sorted by mtime desc from API
    const ts = formatTs(latest.timestamp);
    parts.push(/* html */ `
      <div class="mod-row backup-group">
        <div class="mod-icon">💾</div>
        <div class="mod-info">
          <div class="mod-name">${esc(latest.folder_name)}</div>
          <div class="mod-meta">
            <span>ID: ${wid}</span>
            <span>${items.length} 个版本</span>
            <span>最新: ${ts}</span>
            <span>${latest.size_mb} MB</span>
          </div>
        </div>
        <div style="display:flex;gap:4px;align-items:center">
          <button class="btn btn-primary btn-sm" data-restore="${wid}">↩ 回滚</button>
          <button class="btn btn-ghost btn-sm" data-versions="${wid}">📋 ${items.length}版</button>
        </div>
      </div>
      <div class="backup-versions" id="versions-${wid}" style="display:none;padding:0 16px 12px">
        ${items.map((b, i) => /* html */ `
          <div class="queue-item" style="padding:4px 8px;font-size:11px">
            <span style="color:var(--gray-text)">${formatTs(b.timestamp)}</span>
            <span>${b.size_mb} MB</span>
            <span style="margin-left:auto;display:flex;gap:4px">
              <button class="btn btn-ghost btn-sm" data-restore-id="${b.filename}">↩</button>
              <button class="btn btn-ghost btn-sm" data-delete="${b.filename}">✕</button>
            </span>
          </div>
        `).join("")}
      </div>
    `);
  }
  container.innerHTML = parts.join("");

  // Event: restore latest
  container.querySelectorAll("[data-restore]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const wid = (btn as HTMLElement).dataset.restore!;
      await doRestore(wid);
    });
  });

  // Event: restore specific version
  container.querySelectorAll("[data-restore-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const filename = (btn as HTMLElement).dataset["restoreId"]!;
      const wid = filename.split("__")[0];
      await doRestore(wid, filename);
    });
  });

  // Event: delete backup
  container.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const filename = (btn as HTMLElement).dataset.delete!;
      if (!confirm(`删除备份: ${filename}？`)) return;
      try {
        await fetch(`/api/backups/${encodeURIComponent(filename)}`, { method: "DELETE" });
        toast("已删除", "success");
        refreshBackups();
      } catch (e: any) {
        toast(`失败: ${e.message}`, "error");
      }
    });
  });

  // Event: toggle version list
  container.querySelectorAll("[data-versions]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const wid = (btn as HTMLElement).dataset.versions!;
      const el = document.getElementById(`versions-${wid}`);
      if (el) el.style.display = el.style.display === "none" ? "" : "none";
    });
  });
}

async function doRestore(workshopId: string, filename?: string) {
  const label = filename
    ? `恢复 ${filename}？当前版本将被覆盖。`
    : `恢复到 ${workshopId} 的最新备份？当前版本将被覆盖。`;

  if (!confirm(label)) return;

  try {
    const body = filename ? { filename } : {};
    const resp = await fetch(`/api/backups/${workshopId}/restore`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await resp.json();
    if (data.ok) {
      toast(`已恢复: ${data.restored_folder}`, "success");
    } else {
      toast(data.msg, "error");
    }
  } catch (e: any) {
    toast(`回滚失败: ${e.message}`, "error");
  }
}

async function cleanupBackups() {
  const keep = prompt("每个 Mod 保留几个备份？", "5");
  if (!keep) return;
  try {
    const resp = await fetch("/api/backups/cleanup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keep: parseInt(keep) }),
    });
    const data = await resp.json();
    toast(`已清理 ${data.deleted} 个旧备份`, "success");
    refreshBackups();
  } catch (e: any) {
    toast(`清理失败: ${e.message}`, "error");
  }
}

function formatTs(iso: string): string {
  try {
    return new Date(iso).toLocaleString("zh-CN");
  } catch {
    return iso;
  }
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

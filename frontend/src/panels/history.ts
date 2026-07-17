/**
 * History panel — download history and stats.
 */
import { toast } from "../toast";

interface HistoryItem {
  id: number;
  workshop_id: string;
  mod_name: string;
  package_id: string;
  status: string;
  msg: string;
  created_at: string;
}

interface Stats {
  total: number;
  success: number;
  failed: number;
}

export function initHistoryPanel() {
  document.getElementById("btn-history-refresh")?.addEventListener("click", loadHistory);
  document.getElementById("btn-history-clear")?.addEventListener("click", clearHistory);
  document.getElementById("btn-auto-update")?.addEventListener("click", runAutoUpdate);
  loadHistory();
  loadStats();
  loadAutoStatus();
}

async function loadHistory() {
  const container = document.getElementById("history-list")!;
  container.innerHTML = '<span style="color:var(--gray-text)">加载中...</span>';

  try {
    const resp = await fetch("/api/history?limit=50");
    const data = await resp.json();
    const items: HistoryItem[] = data.items || [];

    if (!items.length) {
      container.innerHTML = '<span style="color:var(--gray-text)">暂无下载记录</span>';
      return;
    }

    const icons: Record<string, string> = { success: "✅", failed: "❌", skipped: "⏭️", pending: "⏳" };

    container.innerHTML = items
      .map(
        (h) => /* html */ `
      <div class="mod-row">
        <div class="mod-icon">${icons[h.status] || "❓"}</div>
        <div class="mod-info">
          <div class="mod-name">Workshop ${esc(h.workshop_id)} ${h.mod_name ? `— ${esc(h.mod_name)}` : ""}</div>
          <div class="mod-meta">
            <span>${h.status}</span>
            <span>${h.created_at}</span>
            ${h.msg ? `<span>${esc(h.msg)}</span>` : ""}
          </div>
        </div>
      </div>`,
      )
      .join("");
  } catch {}
}

async function loadStats() {
  try {
    const resp = await fetch("/api/history/stats");
    const stats: Stats = await resp.json();
    document.getElementById("history-stats")!.innerHTML = /* html */ `
      <span>总计 <b>${stats.total}</b></span>
      <span style="color:var(--green)">成功 <b>${stats.success}</b></span>
      <span style="color:var(--red)">失败 <b>${stats.failed}</b></span>
    `;
  } catch {}
}

async function clearHistory() {
  await fetch("/api/history/clear", { method: "POST" });
  loadHistory();
  loadStats();
  toast("历史记录已清空", "success");
}

async function runAutoUpdate() {
  const btn = document.getElementById("btn-auto-update") as HTMLButtonElement;
  const status = document.getElementById("auto-update-status")!;
  btn.disabled = true;
  status.textContent = "⏳ 正在检查...";
  try {
    const resp = await fetch("/api/auto-update/run", { method: "POST" });
    const data = await resp.json();
    if (data.ok === false) {
      status.textContent = data.msg || "已在运行";
    } else {
      status.textContent = `检查了 ${data.checked} 个 Mod，${data.outdated} 个过期，已加入队列`;
      toast(`自动更新: ${data.outdated} 个 Mod 已加入队列`, "success");
    }
  } catch (e: any) {
    status.textContent = `失败: ${e.message}`;
  }
  btn.disabled = false;
  loadAutoStatus();
}

async function loadAutoStatus() {
  try {
    const resp = await fetch("/api/auto-update/status");
    const data = await resp.json();
    document.getElementById("auto-update-status")!.textContent = data.running ? "⏳ 检查中..." : "就绪";
  } catch {}
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

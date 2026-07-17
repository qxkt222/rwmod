/**
 * Update check panel — compare local mod timestamps with Steam Workshop.
 * Supports one-click "Update All" via POST /api/auto-update/run.
 */
import { toast } from "../toast";

interface UpdateItem {
  workshop_id: string;
  name: string;
  folder: string;
  remote_title: string;
  time_updated: number;
  file_description: string;
}

let _lastUpdateItems: UpdateItem[] = [];

export function initUpdatePanel() {
  document.getElementById("btn-check-updates")?.addEventListener("click", checkUpdates);
  document.getElementById("btn-update-all")?.addEventListener("click", updateAll);
}

async function checkUpdates() {
  const btn = document.getElementById("btn-check-updates") as HTMLButtonElement;
  const allBtn = document.getElementById("btn-update-all")!;
  const container = document.getElementById("update-results")!;
  btn.disabled = true;
  allBtn.style.display = "none";
  container.innerHTML = '<span style="color:var(--gray-text)">正在检查更新...</span>';

  try {
    const resp = await fetch("/api/mods/check-updates");
    const data = await resp.json();
    const updates: UpdateItem[] = data.updates || [];
    _lastUpdateItems = updates;

    if (!updates.length) {
      container.innerHTML = '<span style="color:var(--green)">✅ 所有 Mod 均为最新版本</span>';
      return;
    }

    allBtn.style.display = "";
    renderUpdateList(updates, container);
  } catch (e: any) {
    container.innerHTML = `<span style="color:var(--red)">检查失败: ${e.message}</span>`;
  }
  btn.disabled = false;
}

function renderUpdateList(updates: UpdateItem[], container: HTMLElement) {
  container.innerHTML = updates
    .map(
      (u, i) => {
        const desc = (u.file_description || "").trim();
        const hasDesc = desc.length > 0;
        const preview = hasDesc ? desc.slice(0, 200) : "";
        const hasMore = desc.length > 200;
        const uid = `changelog-${i}`;

        return /* html */ `
    <div class="mod-row" style="align-items:flex-start">
      <div class="mod-icon" style="margin-top:4px">🔄</div>
      <div class="mod-info" style="flex:1;min-width:0">
        <div class="mod-name">${esc(u.name)}</div>
        <div class="mod-meta">
          <span>${esc(u.folder)}</span>
          <span>Workshop ${esc(u.workshop_id)}</span>
          ${u.time_updated ? `<span>更新于 ${new Date(u.time_updated * 1000).toLocaleDateString("zh-CN")}</span>` : ""}
        </div>
        ${hasDesc ? /* html */ `
        <div class="changelog-block" style="margin-top:8px;font-size:12px;color:var(--gray-text);line-height:1.5">
          <div class="changelog-preview" id="${uid}-preview">
            ${esc(preview)}${hasMore ? "..." : ""}
          </div>
          ${hasMore ? /* html */ `
          <div class="changelog-full" id="${uid}-full" style="display:none">
            ${esc(desc)}
          </div>
          <button class="btn btn-ghost btn-sm changelog-toggle" data-target="${uid}" style="margin-top:4px;font-size:11px">
            📖 展开全文
          </button>` : ""}
        </div>` : ""}
      </div>
      <button class="btn btn-primary btn-sm" data-id="${u.workshop_id}" style="flex-shrink:0">⬇ 更新</button>
    </div>`;
      },
    )
    .join("");

  // Changelog toggle
  container.querySelectorAll(".changelog-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const uid = (btn as HTMLElement).dataset.target!;
      const full = document.getElementById(`${uid}-full`)!;
      const preview = document.getElementById(`${uid}-preview`)!;
      if (full.style.display === "none") {
        full.style.display = "";
        preview.style.display = "none";
        (btn as HTMLElement).textContent = "📖 收起";
      } else {
        full.style.display = "none";
        preview.style.display = "";
        (btn as HTMLElement).textContent = "📖 展开全文";
      }
    });
  });

  container.querySelectorAll(".btn-primary[data-id]").forEach((b) => {
    b.addEventListener("click", async () => {
      const id = (b as HTMLElement).dataset.id!;
      try {
        await fetch("/api/queue/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ids: [id] }),
        });
        toast(`已加入队列: ${id}`, "success");
      } catch (e: any) {
        toast(`失败: ${e.message}`, "error");
      }
    });
  });
}

async function updateAll() {
  const allBtn = document.getElementById("btn-update-all") as HTMLButtonElement;
  const container = document.getElementById("update-results")!;
  allBtn.disabled = true;
  allBtn.textContent = "⏳ 更新中...";
  container.innerHTML = '<span style="color:#7aa2f7">正在全部加入队列并开始下载...</span>';

  try {
    const resp = await fetch("/api/auto-update/run", { method: "POST" });
    const data = await resp.json();
    toast(
      `已检查 ${data.checked} 个 Mod，${data.outdated} 个待更新已加入队列并开始下载`,
      "success",
    );
    container.innerHTML =
      `<span style="color:#9ece6a">✅ 已加入 ${data.queued} 个 Mod 到下载队列，自动开始下载</span>\n` +
      `<span style="color:var(--gray-text)">切换到 📋 队列 面板查看进度</span>`;
  } catch (e: any) {
    container.innerHTML = `<span style="color:#f7768e">全部更新失败: ${e.message}</span>`;
    toast(`更新失败: ${e.message}`, "error");
  }
  allBtn.disabled = false;
  allBtn.textContent = "⬇ 全部更新";
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

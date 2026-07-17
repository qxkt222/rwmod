/**
 * Mods list panel — display and interact with installed mods.
 * Shows health status badges: 🟢 maintained / 🟡 stale / 🔴 abandoned / ⚫ removed
 * Shows compatibility badges: ✅ compatible / ❌ incompatible / ❓ unknown
 */
import type { ModEntry } from "../api";
import { refreshMods } from "../main";
import { toast } from "../toast";

let _onClick: ((mod: ModEntry) => void) | null = null;

const HEALTH_LABELS: Record<string, string> = {
  maintained: "🟢 活跃",
  stale: "🟡 停更",
  abandoned: "🔴 废弃",
  removed: "⚫ 下架",
  unknown: "⚪ 未知",
};

export function initModsPanel(mods: ModEntry[], onClick: (mod: ModEntry) => void) {
  _onClick = onClick;
  loadHealth();
  loadCompatibility();
  bindExportCollection();
}

export function onModClick(mod: ModEntry) {
  _onClick?.(mod);
}

// Exported so main.ts can re-apply badges after rendering mod list
export function refreshBadges() {
  loadHealth();
  loadCompatibility();
}

async function loadHealth() {
  try {
    const resp = await fetch("/api/mods/health");
    const data = await resp.json();
    const healthMap: Record<string, string> = {};
    for (const m of data.mods || []) {
      healthMap[m.folder] = m.status;
    }
    // Apply badges to mod rows
    document.querySelectorAll("#mod-list .mod-row").forEach((row) => {
      const folder = row.querySelector(".mod-meta span:first-child")?.textContent;
      const status = healthMap[folder || ""];
      if (status) {
        let badge = row.querySelector(".health-badge");
        if (!badge) {
          badge = document.createElement("span");
          badge.className = "health-badge";
          badge.style.cssText = "font-size:11px;margin-left:8px";
          row.querySelector(".mod-info")?.appendChild(badge);
        }
        badge.textContent = HEALTH_LABELS[status] || status;
      }
    });
  } catch { /* ignore */ }
}

async function loadCompatibility() {
  try {
    const resp = await fetch("/api/mods/compatibility");
    const data = await resp.json();
    if (data.error) return;

    const incompat: Set<string> = new Set(
      (data.groups?.incompatible || []).map((m: any) => m.folder),
    );
    const unknownSet: Set<string> = new Set(
      (data.groups?.unknown || []).map((m: any) => m.folder),
    );

    // Update header with summary
    const header = document.getElementById("mods-header");
    if (header && data.rimworld_version) {
      const existing = header.querySelector(".compat-summary");
      if (!existing) {
        const span = document.createElement("span");
        span.className = "compat-summary";
        span.style.cssText = "font-size:11px;color:var(--gray-text);margin-left:8px";
        header.appendChild(span);
      }
      const span = header.querySelector(".compat-summary")!;
      span.textContent = `RW ${data.rimworld_version} · ${data.incompatible_count} 不兼容`;
    }

    // Apply badges to mod rows
    document.querySelectorAll("#mod-list .mod-row").forEach((row) => {
      const folder = row.querySelector(".mod-meta span:first-child")?.textContent || "";
      let badge = row.querySelector(".compat-badge");
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "compat-badge";
        badge.style.cssText = "font-size:10px;margin-left:6px;padding:1px 4px;border-radius:3px";
        row.querySelector(".mod-info")?.appendChild(badge);
      }
      if (incompat.has(folder)) {
        (badge as HTMLElement).textContent = "❌ 不兼容";
        badge.style.cssText += ";color:#f7768e;background:#3b1e2c";
      } else if (unknownSet.has(folder)) {
        (badge as HTMLElement).textContent = "❓ 未知";
        badge.style.cssText += ";color:var(--gray-text)";
      } else {
        badge.remove();
      }
    });
  } catch { /* ignore */ }
}

// ── collection export ─────────────────────────────────────────────

function bindExportCollection() {
  const btn = document.getElementById("btn-export-collection");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    btn.textContent = "⏳ 生成中...";
    (btn as HTMLButtonElement).disabled = true;
    try {
      const resp = await fetch("/api/mods/export-collection");
      const data = await resp.json();
      showCollectionExport(data);
    } catch (e: any) {
      toast(`导出失败: ${e.message}`, "error");
    }
    btn.textContent = "📤 导出合集";
    (btn as HTMLButtonElement).disabled = false;
  });
}

function showCollectionExport(data: any) {
  const container = document.getElementById("mod-list")!;
  const ids = data.ids || [];
  const idsText = ids.join(" ");

  container.innerHTML = /* html */ `
    <div style="padding:12px">
      <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
        <strong>📦 Steam 合集 — ${data.total} 个 Mod</strong>
        <button class="btn btn-primary btn-sm" id="btn-copy-ids">📋 复制 ${ids.length} 个 ID</button>
        <button class="btn btn-ghost btn-sm" id="btn-copy-md">📝 复制 Markdown</button>
        <button class="btn btn-ghost btn-sm" id="btn-collection-close">✕ 关闭</button>
      </div>
      <div style="font-size:11px;color:var(--gray-text);margin-bottom:8px">
        粘贴到 Steam 合集编辑器 → 添加项目 → 批量粘贴 Workshop ID
      </div>
      <div style="background:var(--surface);border-radius:4px;padding:8px;font-size:11px;font-family:monospace;max-height:200px;overflow-y:auto;white-space:pre-wrap;word-break:break-all">
        ${esc(idsText)}
      </div>
      <div style="margin-top:8px;font-size:11px;max-height:300px;overflow-y:auto">
        ${data.mods?.map((m: any) => /* html */ `
          <div style="padding:2px 0">
            <a href="${escAttr(m.url)}" target="_blank" style="color:var(--blue)">${esc(m.name)}</a>
            <span style="color:var(--gray-text);margin-left:4px">${m.workshop_id}</span>
          </div>
        `).join("") || ""}
      </div>
    </div>
  `;

  // Copy IDs
  document.getElementById("btn-copy-ids")?.addEventListener("click", () => {
    navigator.clipboard.writeText(idsText).then(
      () => toast(`已复制 ${ids.length} 个 Workshop ID`, "success"),
      () => toast("复制失败", "error"),
    );
  });

  // Copy Markdown
  document.getElementById("btn-copy-md")?.addEventListener("click", () => {
    navigator.clipboard.writeText(data.markdown || "").then(
      () => toast("已复制 Markdown", "success"),
      () => toast("复制失败", "error"),
    );
  });

  // Close
  document.getElementById("btn-collection-close")?.addEventListener("click", () => {
    container.innerHTML = '<span style="color:var(--gray-text)">已关闭合集导出。刷新以重新加载 Mod 列表。</span>';
  });
}

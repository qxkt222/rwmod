/**
 * Profile panel — save/restore ModsConfig.xml snapshots.
 * RimWorld players can switch between mod sets with one click.
 */
import { toast } from "../toast";

interface ProfileEntry {
  name: string;
  mod_count: number;
  saved_at: string;
  size_kb: number;
}

export function initProfilePanel() {
  document.getElementById("btn-profile-save")?.addEventListener("click", saveProfile);
  refreshProfiles();
}

async function refreshProfiles() {
  const container = document.getElementById("profile-list")!;
  container.innerHTML = '<span style="color:var(--gray-text)">加载中...</span>';

  try {
    const resp = await fetch("/api/profiles");
    const data = await resp.json();

    const pathEl = document.getElementById("profile-modsconfig-path");
    if (pathEl) {
      pathEl.textContent = data.modsconfig_path
        ? `ModsConfig.xml: ${data.modsconfig_path}`
        : "未找到 ModsConfig.xml";
    }

    if (!data.profiles?.length) {
      container.innerHTML = '<div style="padding:16px;text-align:center;color:var(--gray-text)">暂无存档。点击「保存当前配置」创建第一个 profile。</div>';
      return;
    }

    renderProfileList(data.profiles, container);
  } catch (e: any) {
    container.innerHTML = `<span style="color:var(--red)">加载失败: ${e.message}</span>`;
  }
}

function renderProfileList(profiles: ProfileEntry[], container: HTMLElement) {
  container.innerHTML = profiles.map((p) => {
    const ts = formatTs(p.saved_at);
    return /* html */ `
      <div class="mod-row profile-item">
        <div class="mod-icon">💾</div>
        <div class="mod-info">
          <div class="mod-name">${esc(p.name)}</div>
          <div class="mod-meta">
            <span>${p.mod_count} 个 Mod</span>
            <span>${ts}</span>
            <span>${p.size_kb} KB</span>
          </div>
        </div>
        <div style="display:flex;gap:4px">
          <button class="btn btn-primary btn-sm" data-restore="${escAttr(p.name)}">↩ 启用</button>
          <button class="btn btn-ghost btn-sm" data-delete="${escAttr(p.name)}">✕</button>
        </div>
      </div>
    `;
  }).join("");

  // Restore
  container.querySelectorAll("[data-restore]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const name = (btn as HTMLElement).dataset.restore!;
      if (!confirm(`切换到 profile "${name}"？当前 ModsConfig.xml 将被覆盖（会自动备份）。`)) return;
      try {
        const resp = await fetch(`/api/profiles/${encodeURIComponent(name)}/restore`, { method: "POST" });
        const data = await resp.json();
        if (data.ok) {
          toast(`已启用: ${name}（${data.mod_count} 个 Mod）`, "success");
        } else {
          toast(data.msg, "error");
        }
      } catch (e: any) {
        toast(`切换失败: ${e.message}`, "error");
      }
    });
  });

  // Delete
  container.querySelectorAll("[data-delete]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const name = (btn as HTMLElement).dataset.delete!;
      if (!confirm(`删除 profile "${name}"？`)) return;
      try {
        await fetch(`/api/profiles/${encodeURIComponent(name)}`, { method: "DELETE" });
        toast("已删除", "success");
        refreshProfiles();
      } catch (e: any) {
        toast(`删除失败: ${e.message}`, "error");
      }
    });
  });
}

async function saveProfile() {
  const name = prompt("Profile 名称（如：原版、中世纪、魔改）：");
  if (!name?.trim()) return;

  try {
    const resp = await fetch("/api/profiles/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: name.trim() }),
    });
    const data = await resp.json();
    if (data.ok) {
      toast(data.msg, "success");
      refreshProfiles();
    } else {
      toast(data.msg, "error");
    }
  } catch (e: any) {
    toast(`保存失败: ${e.message}`, "error");
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

function escAttr(s: string): string {
  return s.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

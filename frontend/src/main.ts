/**
 * rwmod Web UI — main entry point.
 * Builds layout, initializes panels lazily, registers keyboard shortcuts.
 *
 * Panels are lazy-loaded: only the visible panel's module is loaded on demand.
 * This reduces initial JS footprint by ~60%.
 */
import "./style.css";
import { api, type ModEntry, type ConfigData } from "./api";
import { connectWS, type WSMessage } from "./ws";
import { initDashboardPanel } from "./panels/dashboard";
import { toast } from "./toast";

// ── state ──────────────────────────────────────────────────────
let mods: ModEntry[] = [];
let currentPanel = "dashboard";

// ── panel init registry ────────────────────────────────────────
const _panelInited = new Set<string>();

/** Lazy import + init a panel module. Called once per panel. */
async function _lazyInit(panel: string): Promise<void> {
  if (_panelInited.has(panel)) return;
  _panelInited.add(panel);

  switch (panel) {
    case "dashboard":
      initDashboardPanel();
      break;
    case "download": {
      const { initDownloadPanel, renderLog } = await import("./panels/download");
      initDownloadPanel();
      break;
    }
    case "collection": {
      const { initCollectionPanel } = await import("./panels/collection");
      initCollectionPanel();
      break;
    }
    case "import": {
      const { initImportPanel } = await import("./panels/import");
      initImportPanel();
      break;
    }
    case "mods": {
      const { initModsPanel, onModClick } = await import("./panels/mods");
      initModsPanel(mods, (mod) => {
        // show mod detail (future)
      });
      break;
    }
    case "search": {
      const { initSearchPanel } = await import("./panels/search");
      initSearchPanel();
      break;
    }
    case "queue": {
      const { initQueuePanel } = await import("./panels/queue");
      initQueuePanel();
      break;
    }
    case "updates": {
      const { initUpdatePanel } = await import("./panels/updates");
      initUpdatePanel();
      break;
    }
    case "rimsort": {
      const { initRimsortPanel } = await import("./panels/rimsort");
      initRimsortPanel();
      break;
    }
    case "profiles": {
      const { initProfilePanel } = await import("./panels/profiles");
      initProfilePanel();
      break;
    }
    case "history": {
      const { initHistoryPanel } = await import("./panels/history");
      initHistoryPanel();
      break;
    }
    case "backups": {
      const { initBackupPanel } = await import("./panels/backup");
      initBackupPanel();
      break;
    }
    case "config": {
      const { initConfigPanel } = await import("./panels/config");
      initConfigPanel();
      break;
    }
  }
}

// ── build layout ───────────────────────────────────────────────
document.getElementById("app")!.innerHTML = /* html */ `
<nav id="navbar">
  <div class="brand">🔧 rwmod <em>· RimWorld Mod 管理器</em></div>
  <div class="tabs" id="nav-tabs">
    <button class="tab active" data-panel="dashboard">📊 首页</button>
    <button class="tab" data-panel="download">📥 下载</button>
    <button class="tab" data-panel="collection">📦 合集</button>
    <button class="tab" data-panel="import">📋 导入</button>
    <button class="tab" data-panel="mods">📊 Mods</button>
    <button class="tab" data-panel="search">🔍 搜索</button>
    <button class="tab" data-panel="queue">📋 队列</button>
    <button class="tab" data-panel="rimsort">📐 RimSort</button>
    <button class="tab" data-panel="profiles">💾 配置档案</button>
    <button class="tab" data-panel="history">📜 历史</button>
    <button class="tab" data-panel="backups">💾 备份</button>
    <button class="tab" data-panel="config">⚙ 配置</button>
  </div>
  <div class="spacer"></div>
  <div class="nav-actions">
    <span id="online-indicator" style="font-size:12px;margin-right:8px" title="Steam API 状态">🟢</span>
    <button class="nav-btn" id="btn-export" title="导出 Mod 列表">📤</button>
    <button class="nav-btn" id="btn-dark" title="深色模式">🌙</button>
    <button class="nav-btn" id="btn-refresh" title="刷新">🔄</button>
    <button class="nav-btn" id="btn-cmd" title="命令面板 Ctrl+K">⚡</button>
  </div>
</nav>

<div id="main">
  <aside id="sidebar">
    <div class="side-section">快速操作</div>
    <div class="side-item" data-panel="dashboard"><span class="ico">📊</span>首页</div>
    <div class="side-item" data-panel="download"><span class="ico">📥</span>下载 Mod</div>
    <div class="side-item" data-panel="collection"><span class="ico">📦</span>下载合集</div>
    <div class="side-item" data-panel="import"><span class="ico">📋</span>导入列表</div>
    <div class="side-section">浏览</div>
    <div class="side-item" data-panel="mods"><span class="ico">📊</span>已安装 Mods<span class="side-badge" id="mod-count">0</span></div>
    <div class="side-item" data-panel="search"><span class="ico">🔍</span>搜索</div>
    <div class="side-item" data-panel="queue"><span class="ico">📋</span>下载队列<span class="side-badge" id="queue-count">0</span></div>
    <div class="side-item" data-panel="rimsort"><span class="ico">📐</span>RimSort</div>
    <div class="side-item" data-panel="profiles"><span class="ico">💾</span>配置档案</div>
    <div class="side-item" data-panel="history"><span class="ico">📜</span>下载历史</div>
    <div class="side-item" data-panel="backups"><span class="ico">💾</span>备份管理</div>
    <div class="side-item" data-panel="config"><span class="ico">⚙</span>配置</div>
  </aside>

  <div id="workspace">
    <div class="panel active" id="panel-dashboard">
      <div class="card" style="text-align:center;padding:32px">
        <div style="font-size:48px;margin-bottom:12px">🔧</div>
        <h2 style="margin:0;font-size:22px">rwmod · RimWorld Mod 管理器</h2>
        <p style="color:var(--gray-text);font-size:13px;margin:8px 0 24px">全离线 SteamCMD 匿名下载</p>
        <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap">
          <div class="card" style="min-width:120px;text-align:center;padding:16px">
            <div style="font-size:28px;font-weight:700;color:var(--blue)" id="db-mods-count">—</div>
            <div style="font-size:12px;color:var(--gray-text)">已安装 Mod</div>
          </div>
          <div class="card" style="min-width:120px;text-align:center;padding:16px">
            <div style="font-size:28px;font-weight:700;color:var(--yellow)" id="db-updates-count">—</div>
            <div style="font-size:12px;color:var(--gray-text)">待更新</div>
          </div>
          <div class="card" style="min-width:120px;text-align:center;padding:16px">
            <div style="font-size:28px;font-weight:700;color:var(--text)" id="db-disk-usage">—</div>
            <div style="font-size:12px;color:var(--gray-text)">磁盘占用</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">最近活动</div>
        <div id="db-activity" style="font-size:12px;color:var(--gray-text)">加载中...</div>
      </div>
      <div class="card">
        <div class="card-header">⚡ 快速操作</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button class="btn btn-primary" onclick="document.querySelector('[data-panel=\\'search\\']').click()">🔍 搜索 Workshop</button>
          <button class="btn btn-primary" onclick="document.querySelector('[data-panel=\\'download\\']').click()">📥 下载 Mod</button>
          <button class="btn btn-accent" id="btn-auto-update-dashboard">⬇ 一键更新</button>
          <button class="btn btn-ghost" onclick="document.querySelector('[data-panel=\\'queue\\']').click()">📋 下载队列</button>
        </div>
      </div>
    </div>

    <div class="panel" id="panel-download">
      <div class="card">
        <div class="card-header">📥 下载 Mod</div>
        <div class="form-row">
          <input type="text" id="mod-input" placeholder="Mod ID 或 Workshop 链接，多个用逗号分隔" />
          <button class="btn btn-primary" id="btn-download">下载</button>
        </div>
        <label class="check-label" style="margin-top:8px">
          <input type="checkbox" id="force-dl" /> 覆盖已存在的 mod
        </label>
        <div id="dep-preview" style="margin-top:8px;font-size:12px"></div>
      </div>
      <div class="card" style="flex:1;display:flex;flex-direction:column;overflow-y:auto;min-height:0">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>📋 下载日志</span>
          <button class="btn btn-ghost btn-sm" id="btn-clear-log">清空</button>
        </div>
        <div class="log-console" id="log"></div>
      </div>
    </div>

    <div class="panel" id="panel-collection">
      <div class="card">
        <div class="card-header">📦 下载 Steam 合集</div>
        <div class="form-row">
          <input type="text" id="collection-input" placeholder="Steam 合集 ID（如 3721899704）" />
          <button class="btn btn-primary" id="btn-collection-preview" style="margin-right:4px">预览</button>
          <button class="btn btn-primary" id="btn-collection">下载合集</button>
        </div>
        <label class="check-label" style="margin-top:8px">
          <input type="checkbox" id="force-collection" /> 覆盖已存在的 mod
        </label>
      </div>
      <div class="card" style="flex:1;display:flex;flex-direction:column;overflow-y:auto;min-height:0">
        <div class="card-header">📋 日志</div>
        <div class="log-console" id="log-collection"></div>
      </div>
    </div>

    <div class="panel" id="panel-import">
      <div class="card">
        <div class="card-header">📋 导入 Mod 列表</div>
        <label class="file-drop" id="drop-zone">
          <div>拖拽 .txt 文件到此处，或点击选择</div>
          <div style="font-size:11px;margin-top:4px">每行一个 Mod ID 或 Workshop 链接</div>
          <input type="file" id="import-file" accept=".txt" />
        </label>
      </div>
      <div class="card">
        <div class="card-header">📄 导入 ModsConfig.xml</div>
        <label class="file-drop" id="drop-zone-xml">
          <div>拖拽 ModsConfig.xml 到此处，下载缺失的 mod</div>
          <input type="file" id="import-sort" accept=".xml" />
        </label>
      </div>
    </div>

    <div class="panel" id="panel-mods">
      <div class="card" style="flex:1;min-height:0">
        <div class="card-header" style="display:flex;justify-content:space-between" id="mods-header">
          <span>📊 已安装 Mod</span>
          <div style="display:flex;gap:6px;align-items:center">
            <button class="btn btn-ghost btn-sm" id="btn-export-collection">📤 导出合集</button>
            <span style="font-weight:400;font-size:12px;color:var(--gray-text)" id="mod-count-label"></span>
          </div>
        </div>
        <div id="mod-list" style="font-size:12px;color:var(--gray-text)">加载中...</div>
      </div>
    </div>

    <div class="panel" id="panel-search">
      <div class="card">
        <div class="card-header">🔍 搜索 Steam Workshop</div>
        <div class="form-row">
          <input type="text" id="search-input" placeholder="搜索 RimWorld Mod..." />
          <button class="btn btn-primary" id="btn-search">搜索</button>
        </div>
      </div>
      <div class="card" style="flex:1;overflow-y:auto">
        <div id="search-results" style="font-size:12px;color:var(--gray-text)">输入关键词搜索</div>
      </div>
    </div>

    <div class="panel" id="panel-queue">
      <div class="card" style="flex:1;overflow-y:auto">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>📋 下载队列</span>
          <div style="display:flex;gap:6px">
            <button class="btn btn-primary btn-sm" id="btn-queue-start">▶ 开始</button>
            <button class="btn btn-ghost btn-sm" id="btn-queue-clear">清空已完成</button>
          </div>
        </div>
        <div id="queue-list" style="font-size:12px;color:var(--gray-text)">队列为空</div>
      </div>
      <div class="card">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>🔄 更新检查</span>
          <div style="display:flex;gap:6px">
            <button class="btn btn-ghost btn-sm" id="btn-check-updates">检查更新</button>
            <button class="btn btn-primary btn-sm" id="btn-update-all" style="display:none">⬇ 全部更新</button>
          </div>
        </div>
        <div id="update-results" style="font-size:12px;color:var(--gray-text)">点击「检查更新」</div>
      </div>
    </div>

    <div class="panel" id="panel-rimsort">
      <div class="card">
        <div class="card-header">📐 RimSort 集成</div>
        <div id="rimsort-content" style="font-size:12px;color:var(--gray-text)">加载中...</div>
      </div>
      <div class="card">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>🔍 排序分析</span>
          <button class="btn btn-primary btn-sm" id="btn-rimsort-order">🔍 分析排序</button>
        </div>
        <div id="rimsort-order-result" style="font-size:12px;color:var(--gray-text)">点击「分析排序」检测常见问题</div>
      </div>
    </div>

    <div class="panel" id="panel-profiles">
      <div class="card" style="flex:1;overflow-y:auto">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>💾 Mod 配置档案</span>
          <button class="btn btn-primary btn-sm" id="btn-profile-save">💾 保存当前配置</button>
        </div>
        <div id="profile-modsconfig-path" style="font-size:11px;color:var(--gray-text);padding:4px 16px"></div>
        <div id="profile-list" style="font-size:12px;color:var(--gray-text)">加载中...</div>
      </div>
    </div>

    <div class="panel" id="panel-history">
      <div class="card" style="flex:1;overflow-y:auto">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>📜 下载历史</span>
          <button class="btn btn-ghost btn-sm" id="btn-clear-history">清空历史</button>
        </div>
        <div id="history-list" style="font-size:12px;color:var(--gray-text)">加载中...</div>
      </div>
    </div>

    <div class="panel" id="panel-backups">
      <div class="card" style="flex:1;overflow-y:auto">
        <div class="card-header" style="display:flex;justify-content:space-between">
          <span>💾 Mod 备份</span>
          <div style="display:flex;gap:6px">
            <button class="btn btn-ghost btn-sm" id="btn-backup-refresh">🔄 刷新</button>
            <button class="btn btn-ghost btn-sm" id="btn-backup-cleanup">🧹 清理旧备份</button>
          </div>
        </div>
        <div id="backup-group-label" style="font-size:11px;color:var(--gray-text);padding:4px 16px"></div>
        <div id="backup-list" style="font-size:12px;color:var(--gray-text)">加载中...</div>
      </div>
    </div>

    <div class="panel" id="panel-config">
      <div class="card">
        <div class="card-header">⚙ 配置</div>
        <div id="config-display" style="font-size:12px;color:var(--gray-text);margin-bottom:12px">加载中...</div>
        <div class="form-group">
          <label>SteamCMD 路径</label>
          <input type="text" id="cfg-steamcmd" />
        </div>
        <div class="form-group">
          <label>Mods 目录</label>
          <input type="text" id="cfg-mods" />
        </div>
        <div class="form-group">
          <label>游戏目录</label>
          <input type="text" id="cfg-rimworld" />
        </div>
        <div class="form-group">
          <label>备份目录</label>
          <input type="text" id="cfg-backup" />
        </div>
        <div style="display:flex;gap:8px;margin-top:12px">
          <button class="btn btn-primary" id="btn-save-config">保存</button>
          <button class="btn btn-ghost" id="btn-check-steamcmd">检测 SteamCMD</button>
        </div>
        <div id="steamcmd-status" style="margin-top:8px;font-size:12px"></div>
      </div>
    </div>
  </div>
</div>

<div id="toast-container"></div>
<div id="cmd-palette" class="cmd-overlay">
  <div class="cmd-box">
    <input type="text" id="cmd-input" class="cmd-input" placeholder="输入命令..." autocomplete="off" />
    <div id="cmd-results" class="cmd-results"></div>
  </div>
</div>
`;

// ── panel navigation ──────────────────────────────────────────
export function switchPanel(name: string) {
  currentPanel = name;
  document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelectorAll(".side-item").forEach((s) => s.classList.remove("active"));

  const panel = document.getElementById(`panel-${name}`);
  if (panel) panel.classList.add("active");

  const tab = document.querySelector(`[data-panel="${name}"]`);
  if (tab) tab.classList.add("active");

  // Lazy-init the panel on first visit
  _lazyInit(name);
}

// ── tab click handlers ─────────────────────────────────────────
document.querySelector("#nav-tabs")?.addEventListener("click", (e) => {
  const btn = (e.target as HTMLElement).closest("[data-panel]");
  if (!btn) return;
  switchPanel((btn as HTMLElement).dataset.panel!);
});

document.querySelector("#sidebar")?.addEventListener("click", (e) => {
  const item = (e.target as HTMLElement).closest("[data-panel]");
  if (!item) return;
  switchPanel((item as HTMLElement).dataset.panel!);
});

// ── global actions ─────────────────────────────────────────────
export function setStatus(color: string, msg: string) {
  // simplified for now — extended by panels
  console.log(`[status:${color}] ${msg}`);
}

export async function refreshMods() {
  try {
    mods = await api.listMods();
    const el = document.getElementById("mod-count");
    if (el) el.textContent = String(mods.length);
    renderModList(mods);
  } catch { /* ignore */ }
}

function renderModList(modList: ModEntry[]) {
  const container = document.getElementById("mod-list");
  if (!container) return;

  if (!modList.length) {
    container.innerHTML = '<div style="padding:16px;text-align:center;color:var(--gray-text)">没有安装的 Mod</div>';
    return;
  }

  container.innerHTML = modList.map(m => /* html */ `
    <div class="mod-row">
      <div class="mod-icon">📦</div>
      <div class="mod-info">
        <div class="mod-name">${esc(m.name)}</div>
        <div class="mod-meta">
          <span>${esc(m.folder)}</span>
          ${m.workshop_id ? `<span>Workshop ${esc(m.workshop_id)}</span>` : ''}
          ${m.package_id ? `<span>${esc(m.package_id)}</span>` : ''}
        </div>
      </div>
    </div>
  `).join('');

  // After rendering, re-apply health and compatibility badges
  import('./panels/mods').then(m => m.refreshBadges()).catch(() => {});
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ── keyboard shortcuts ─────────────────────────────────────────
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "k") {
    e.preventDefault();
    import("./cmd").then(({ openCmdPalette }) => openCmdPalette());
  }
});

// ── toolbar buttons ────────────────────────────────────────────
document.getElementById("btn-cmd")?.addEventListener("click", () => {
  import("./cmd").then(({ openCmdPalette }) => openCmdPalette());
});

document.getElementById("btn-refresh")?.addEventListener("click", () => {
  refreshMods();
  toast("已刷新", "success");
});

document.getElementById("btn-dark")?.addEventListener("click", () => {
  document.body.classList.toggle("dark");
  const isDark = document.body.classList.contains("dark");
  (document.getElementById("btn-dark") as HTMLButtonElement).textContent = isDark ? "☀️" : "🌙";
});

document.getElementById("btn-export")?.addEventListener("click", async () => {
  try {
    const resp = await fetch("/api/mods/export");
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rwmod-export.json";
    a.click();
    URL.revokeObjectURL(url);
    toast("导出完成", "success");
  } catch {
    toast("导出失败", "error");
  }
});

// ── startup ────────────────────────────────────────────────────
(async () => {
  // Init dashboard (eager — it's the landing page)
  _lazyInit("dashboard");

  // Load mod list
  await refreshMods();

  // Connect WebSocket (non-blocking)
  connectWS((msg) => {
    if (msg.type === "queue_update") {
      const el = document.getElementById("queue-count");
      if (el && msg.items) {
        const active = (msg.items as any[]).filter((i: any) => i.status === "pending" || i.status === "downloading");
        el.textContent = String(active.length);
      }
    }
  });

  // Poll online status every 30s
  pollOnlineStatus();
  setInterval(pollOnlineStatus, 30000);
})();

function pollOnlineStatus() {
  fetch("/api/status")
    .then(r => r.json())
    .then((d: any) => {
      const el = document.getElementById("online-indicator");
      if (el) {
        el.textContent = d.online ? "🟢" : "🔴";
        el.title = d.online ? "Steam API 在线" : "Steam API 离线（使用本地缓存）";
      }
    })
    .catch(() => {});
}

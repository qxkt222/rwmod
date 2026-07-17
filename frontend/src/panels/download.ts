/**
 * Download panel — mod ID input, force toggle, SSE log, dependency preview.
 */
import { api, type SSEEvent } from "../api";
import { setStatus, refreshMods } from "../main";

let activeController: AbortController | null = null;
let depTimer: ReturnType<typeof setTimeout> | null = null;

export function initDownloadPanel() {
  const input = document.getElementById("mod-input") as HTMLInputElement | null;
  const btn = document.getElementById("btn-download") as HTMLButtonElement | null;
  const clearBtn = document.getElementById("btn-clear-log") as HTMLButtonElement | null;

  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") startDownload();
  });
  input?.addEventListener("input", () => {
    // Debounce: fetch dependencies 500ms after user stops typing
    if (depTimer) clearTimeout(depTimer);
    const val = input.value.trim();
    if (!val) {
      clearDepPreview();
      return;
    }
    depTimer = setTimeout(() => previewDeps(val), 500);
  });
  btn?.addEventListener("click", startDownload);
  clearBtn?.addEventListener("click", () => {
    const log = document.getElementById("log")!;
    log.textContent = "";
  });
}

async function previewDeps(raw: string) {
  const ids = raw.split(/[,;\s]+/).filter(Boolean);
  if (!ids.length) return;

  const container = document.getElementById("dep-preview")!;
  container.innerHTML = '<span style="font-size:11px;color:var(--gray-text)">查询依赖中...</span>';

  try {
    const resp = await fetch("/api/mods/dependencies", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    const data = await resp.json();
    const deps = data.deps || {};

    let totalInstalled = 0;
    let totalMissing = 0;
    const parts: string[] = [];

    for (const [mid, depList] of Object.entries(deps) as [string, any[]][]) {
      if (!depList || !depList.length) continue;
      const installed = depList.filter((d: any) => d.installed);
      const missing = depList.filter((d: any) => !d.installed);
      totalInstalled += installed.length;
      totalMissing += missing.length;

      parts.push(/* html */ `
        <div style="margin-bottom:6px">
          <strong style="font-size:11px">${esc(String(mid))}</strong>
          <span style="font-size:10px;color:var(--gray-text);margin-left:4px">${depList.length} 个依赖</span>
        </div>
        ${installed.map((d: any) => /* html */ `
          <div class="dep-item" style="font-size:11px;padding:2px 0 2px 12px">
            <span style="color:var(--green)">✓</span>
            <span>${esc(d.name)}</span>
            <span style="color:var(--gray-text);font-size:10px;margin-left:4px">${d.id}</span>
          </div>`).join("")}
        ${missing.map((d: any) => /* html */ `
          <div class="dep-item" style="font-size:11px;padding:2px 0 2px 12px">
            <span style="color:var(--yellow)">⚠</span>
            <span>${esc(d.name)}</span>
            <span style="color:var(--gray-text);font-size:10px;margin-left:4px">${d.id}</span>
            <span style="color:var(--red);font-size:10px">未安装</span>
          </div>`).join("")}
      `);
    }

    if (!parts.length) {
      container.innerHTML = '<span style="font-size:11px;color:var(--gray-text)">未检测到依赖关系</span>';
      return;
    }

    const summary = totalMissing > 0
      ? `<span style="color:var(--yellow);font-size:11px">⚠ ${totalMissing} 个依赖缺失，下载时将自动安装</span>`
      : totalInstalled > 0
        ? `<span style="color:var(--green);font-size:11px">✓ ${totalInstalled} 个依赖已安装</span>`
        : "";

    container.innerHTML = /* html */ `
      <div style="margin-bottom:4px">${summary}</div>
      ${parts.join("")}
    `;
  } catch {
    container.innerHTML = "";
  }
}

function clearDepPreview() {
  const container = document.getElementById("dep-preview");
  if (container) container.innerHTML = "";
}

async function startDownload() {
  const input = document.getElementById("mod-input") as HTMLInputElement;
  const forceChk = document.getElementById("force-dl") as HTMLInputElement;
  const raw = input.value.trim();
  if (!raw) return;

  const ids = raw.split(/[,;\s]+/).filter(Boolean);
  const force = forceChk.checked;
  const log = document.getElementById("log")!;
  log.textContent = "";
  setStatus("blue", `正在下载 ${ids.length} 个 Mod...`);

  for (const id of ids) {
    renderLog(`── Mod ${id} ──`);
    await new Promise<void>((resolve) => {
      activeController = api.downloadStream(id, force, (evt: SSEEvent) => {
        if (evt.event === "done" || evt.event === "fail") {
          resolve();
        }
        renderSSE(evt);
      });
    });
  }

  setStatus("green", "下载完成");
  refreshMods();
}

function renderSSE(evt: SSEEvent) {
  switch (evt.event) {
    case "start":
      return renderLog(`▶ 开始下载 ${evt.id}`);
    case "info":
      return renderLog(`  ${evt.msg}`, "line-info");
    case "log":
      return renderLog(`  ${evt.line}`);
    case "warn":
      return renderLog(`  ⚠ ${evt.msg}`, "line-warn");
    case "skip":
      return renderLog(`  ✓ ${evt.msg}`, "line-ok");
    case "ok":
      return renderLog(`  ✓ ${evt.msg}`, "line-ok");
    case "fail":
      return renderLog(`  ✗ ${evt.msg}`, "line-error");
    case "done":
      return renderLog(`✅ 完成 ${evt.id}`, "line-ok");
  }
}

export function renderLog(msg: string, cls = "") {
  const log = document.getElementById("log");
  if (!log) return;
  const classes: Record<string, string> = {
    "line-info": "color:#7aa2f7",
    "line-ok": "color:#9ece6a",
    "line-warn": "color:#e0af68",
    "line-error": "color:#f7768e",
  };
  const style = cls ? ` style="${classes[cls] || ""}"` : "";
  log.innerHTML += `<span${style}>${esc(msg)}</span>\n`;
  log.scrollTop = log.scrollHeight;
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

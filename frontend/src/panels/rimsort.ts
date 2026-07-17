/**
 * RimSort panel — generate ModsConfig.xml, compare with installed mods.
 */
import { toast } from "../toast";
import { refreshMods } from "../main";

export function initRimsortPanel() {
  const genBtn = document.getElementById("btn-rimsort-generate");
  if (genBtn) genBtn.addEventListener("click", generateConfig);
  setupRimsortDrop();
  bindOrderCheck();
}

async function generateConfig() {
  const btn = document.getElementById("btn-rimsort-generate") as HTMLButtonElement;
  btn.disabled = true;
  try {
    const resp = await fetch("/api/rimsort/generate", { method: "POST" });
    const data = await resp.json();
    const xml = data.modsconfig_xml;

    const pre = document.getElementById("rimsort-output")!;
    pre.textContent = xml;
    pre.style.display = "block";

    // Also download
    const blob = new Blob([xml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ModsConfig.xml";
    a.click();
    URL.revokeObjectURL(url);
    toast("已生成并下载 ModsConfig.xml", "success");
  } catch (e: any) {
    toast(`生成失败: ${e.message}`, "error");
  }
  btn.disabled = false;
}

async function compareFile() {
  const input = document.getElementById("rimsort-file") as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) {
    toast("请先选择 ModsConfig.xml 文件", "error");
    return;
  }

  const container = document.getElementById("rimsort-compare-result")!;
  container.innerHTML = '<span style="color:var(--gray-text)">正在对比...</span>';

  try {
    const fd = new FormData();
    fd.append("file", file);
    const resp = await fetch("/api/rimsort/compare-file", { method: "POST", body: fd });
    const data = await resp.json();

    if (data.error) {
      container.innerHTML = `<span style="color:var(--red)">解析失败: ${data.error}</span>`;
      return;
    }

    const miss = data.missing || [];
    const extra = data.extra || [];
    const installed = data.installed || [];

    container.innerHTML = /* html */ `
      <div style="margin-bottom:12px;font-size:14px">
        <b>对比结果</b>
        <span style="color:var(--gray-text);margin-left:12px">配置中有 ${data.total_in_config} 个 Mod</span>
      </div>
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px">
        <span style="color:var(--green)">✅ 已安装 ${installed.length}</span>
        <span style="color:var(--red)">❌ 缺失 ${miss.length}</span>
        <span style="color:var(--yellow)">⚠ 额外 ${extra.length}</span>
      </div>
      ${miss.length ? renderMissing(miss, data.missing_details || []) : ""}
      ${extra.length ? renderExtra(extra) : ""}
    `;
  } catch (e: any) {
    container.innerHTML = `<span style="color:var(--red)">对比失败: ${e.message}</span>`;
  }
}

function renderMissing(ids: string[], details: any[]): string {
  const rows = ids
    .map((pid: string, i: number) => {
      const d = details[i] || {};
      const wid = d.workshop_id || "";
      const dlBtn = wid
        ? `<button class="btn btn-primary btn-sm" data-wid="${wid}">⬇ 加入队列</button>`
        : `<span style="color:var(--gray-text);font-size:11px">无法解析 Workshop ID</span>`;

      return /* html */ `
      <div class="mod-row">
        <div class="mod-icon" style="background:var(--red);color:#fff">❌</div>
        <div class="mod-info">
          <div class="mod-name">${esc(pid)}</div>
          ${wid ? `<div class="mod-meta">Workshop ${esc(wid)}</div>` : ""}
        </div>
        ${dlBtn}
      </div>`;
    })
    .join("");

  // Delegate click events
  setTimeout(() => {
    document.querySelectorAll("#rimsort-compare-result .btn-primary[data-wid]").forEach((b) => {
      b.addEventListener("click", async () => {
        const wid = (b as HTMLElement).dataset.wid!;
        try {
          await fetch("/api/queue/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ids: [wid] }),
          });
          toast(`已加入队列: ${wid}`, "success");
        } catch (e: any) {
          toast(`失败: ${e.message}`, "error");
        }
      });
    });
  }, 50);

  return `<div style="margin-top:8px"><div style="font-weight:600;font-size:12px;color:var(--red)">缺失的 Mod (${ids.length})</div>${rows}</div>`;
}

function renderExtra(ids: string[]): string {
  const rows = ids.map((pid) => /* html */ `
    <div class="mod-row">
      <div class="mod-icon" style="background:var(--yellow);color:#fff">⚠</div>
      <div class="mod-info"><div class="mod-name">${esc(pid)}</div></div>
    </div>`).join("");

  return `<div style="margin-top:8px"><div style="font-weight:600;font-size:12px;color:var(--yellow)">额外安装的 Mod (${ids.length})</div>${rows}</div>`;
}

function setupRimsortDrop() {
  const zone = document.getElementById("drop-zone-rimsort")!;
  const input = document.getElementById("rimsort-file") as HTMLInputElement;

  input.addEventListener("change", () => { if (input.files?.[0]) compareFile(); });
  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (e.dataTransfer?.files.length) {
      input.files = e.dataTransfer.files;
      compareFile();
    }
  });
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// ── load order check ──────────────────────────────────────────────

function bindOrderCheck() {
  const btn = document.getElementById("btn-rimsort-order");
  if (!btn) return;

  btn.addEventListener("click", async () => {
    const container = document.getElementById("rimsort-order-result")!;
    btn.textContent = "⏳ 检查中...";
    (btn as HTMLButtonElement).disabled = true;
    container.innerHTML = '<span style="color:var(--gray-text)">正在分析加载顺序...</span>';

    try {
      const resp = await fetch("/api/rimsort/check-order");
      const data = await resp.json();

      if (data.error) {
        container.innerHTML = `<span style="color:var(--red)">${esc(data.error)}</span>`;
        return;
      }

      const issues = data.issues || [];
      const errCount = issues.filter((i: any) => i.severity === "error").length;
      const warnCount = issues.filter((i: any) => i.severity === "warn").length;

      const colorIcons: Record<string, string> = {
        error: "🔴",
        warn: "🟡",
        info: "🔵",
      };

      container.innerHTML = /* html */ `
        <div style="margin-bottom:12px;font-size:14px">
          <b>📐 排序分析</b>
          <span style="color:var(--gray-text);margin-left:8px">${data.total_mods} 个 Mod</span>
        </div>
        <div style="display:flex;gap:12px;margin-bottom:12px">
          <span style="color:${errCount ? 'var(--red)' : 'var(--green)'}">${errCount ? '🔴 ' + errCount + ' 错误' : '✅ 无错误'}</span>
          <span style="color:${warnCount ? 'var(--yellow)' : 'var(--green)'}">${warnCount ? '🟡 ' + warnCount + ' 警告' : ''}</span>
          ${!errCount && !warnCount ? '<span style="color:var(--green)">排序看起来不错！</span>' : ''}
        </div>
        ${issues.length ? issues.map((i: any) => /* html */ `
          <div style="padding:6px 8px;margin:4px 0;font-size:12px;border-left:3px solid ${
            i.severity === "error" ? "var(--red)" : "var(--yellow)"
          }">
            <span style="margin-right:4px">${colorIcons[i.severity] || ""}</span>
            ${esc(i.message)}
          </div>
        `).join("") : '<span style="color:var(--green)">✅ 未发现排序问题</span>'}
        <div style="margin-top:12px;font-size:11px;color:var(--gray-text)">
          💡 基于社区规则检测：Harmony 位置、Core/DLC 顺序、已知冲突、重复项。<br>
          更详细的排序分析请使用 <a href="https://github.com/rimpy-custom/RimPy" target="_blank" style="color:var(--blue)">RimPy Mod Manager</a>。
        </div>
      `;
    } catch (e: any) {
      container.innerHTML = `<span style="color:var(--red)">检查失败: ${e.message}</span>`;
    }
    btn.textContent = "🔍 分析排序";
    (btn as HTMLButtonElement).disabled = false;
  });
}

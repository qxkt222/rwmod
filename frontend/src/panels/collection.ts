/**
 * Collection panel — download entire Steam Workshop collections.
 */
import { api } from "../api";
import { setStatus, refreshMods } from "../main";

export function initCollectionPanel() {
  const input = document.getElementById("collection-input") as HTMLInputElement | null;
  const btn = document.getElementById("btn-collection") as HTMLButtonElement | null;
  const previewBtn = document.getElementById("btn-collection-preview");

  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") startCollection();
  });
  btn?.addEventListener("click", startCollection);
  previewBtn?.addEventListener("click", previewCollection);
}

async function startCollection() {
  const input = document.getElementById("collection-input") as HTMLInputElement;
  const forceChk = document.getElementById("force-collection") as HTMLInputElement;
  const cid = input.value.trim();
  if (!cid) return;

  const log = document.getElementById("log-collection")!;
  log.innerHTML = `<span style="color:#7aa2f7">正在获取合集 ${cid}...</span>\n`;
  setStatus("blue", "正在获取合集...");

  try {
    const data = await api.importCollection(cid, forceChk.checked);
    const ok = data.results.filter((r) => r.ok).length;
    log.innerHTML += `<span style="color:#9ece6a">合集 ${cid}: ${ok}/${data.total} 成功</span>\n`;
    data.results.forEach((r) => {
      const color = r.ok ? "#9ece6a" : "#f7768e";
      log.innerHTML += `<span style="color:${color}">  ${r.id}: ${r.ok ? "✓" : "✗"}</span>\n`;
    });
    log.scrollTop = log.scrollHeight;
    setStatus("green", `合集下载完成: ${ok}/${data.total}`);
  } catch (e: any) {
    log.innerHTML += `<span style="color:#f7768e">错误: ${e.message}</span>`;
    setStatus("red", "合集下载失败");
  }
  refreshMods();
}

async function previewCollection() {
  const input = document.getElementById("collection-input") as HTMLInputElement;
  const cid = input.value.trim();
  if (!cid) return;
  const log = document.getElementById("log-collection")!;
  log.innerHTML = '<span style="color:#7aa2f7">正在获取合集预览...</span>\n';

  try {
    const resp = await fetch(`/api/collection/preview/${encodeURIComponent(cid)}`);
    const d = await resp.json();
    if (d.error) { log.innerHTML = `<span style="color:#f7768e">${d.error}</span>`; return; }
    log.innerHTML =
      `<span style="color:#9ece6a">合集 ${d.collection_id}: ${d.total} 个 Mod</span>\n` +
      `<span style="color:#9ece6a">  🟢 已安装 ${d.installed_count}</span>\n` +
      `<span style="color:#7aa2f7">  🔵 新发现 ${d.new_count}</span>\n` +
      (d.failed_count ? `<span style="color:#e0af68">  🟡 之前失败 ${d.failed_count}</span>\n` : "") +
      `<span style="color:var(--gray-text)">点击"下载合集"开始下载</span>\n`;
    log.scrollTop = log.scrollHeight;
  } catch (e: any) { log.innerHTML = `<span style="color:#f7768e">预览失败: ${e.message}</span>`; }
}

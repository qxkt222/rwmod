/**
 * Import panel — drag & drop mod list files and ModsConfig.xml.
 */
import { api } from "../api";
import { setStatus, refreshMods } from "../main";
import { toast } from "../toast";

export function initImportPanel() {
  setupDropZone("drop-zone", "import-file", handleFileImport);
  setupDropZone("drop-zone-xml", "import-sort", handleSortImport);
}

function setupDropZone(zoneId: string, inputId: string, handler: (file: File) => void) {
  const zone = document.getElementById(zoneId)!;
  const input = document.getElementById(inputId) as HTMLInputElement;

  input.addEventListener("change", () => {
    if (input.files?.[0]) handler(input.files[0]);
  });

  zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    if (e.dataTransfer?.files.length) {
      input.files = e.dataTransfer.files;
      handler(e.dataTransfer.files[0]);
    }
  });
}

async function handleFileImport(file: File) {
  setStatus("blue", `导入 ${file.name}...`);
  try {
    const data = await api.importFile(file);
    const ok = data.results.filter((r) => r.ok).length;
    toast(`导入完成: ${ok}/${data.total} 成功`, "success");
    setStatus("green", "导入完成");
    refreshMods();
  } catch (e: any) {
    toast(`导入失败: ${e.message}`, "error");
    setStatus("red", "导入失败");
  }
}

async function handleSortImport(file: File) {
  setStatus("blue", `解析 ${file.name}...`);
  try {
    const data = await api.importSort(file);
    let msg = `ModsConfig: ${data.total_packages} 个包, ${data.missing} 缺失, ${data.downloaded} 已下载`;
    if (data.unknown?.length) msg += `, ${data.unknown.length} 无法解析`;
    toast(msg, "success");
    setStatus("green", "ModsConfig 导入完成");
    refreshMods();
  } catch (e: any) {
    toast(`导入失败: ${e.message}`, "error");
    setStatus("red", "导入失败");
  }
}

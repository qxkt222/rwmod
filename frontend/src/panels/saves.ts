import { toast } from "../toast";

export function initSavesPanel() {
  document.getElementById("btn-scan-saves")?.addEventListener("click", scanSaves);
  document.getElementById("saves-file-upload")?.addEventListener("change", uploadSave);
  scanSaves();
}

async function scanSaves() {
  const el = document.getElementById("saves-results");
  if (!el) return;
  el.innerHTML = '<div style="padding:16px;color:var(--gray-text)">Scanning...</div>';
  try {
    const resp = await fetch("/api/saves");
    const data = await resp.json();
    if (!data.saves?.length) {
      el.innerHTML = '<div style="padding:16px;text-align:center;color:var(--gray-text)">No save files found</div>';
      return;
    }
    el.innerHTML = data.saves.map((s: any) => {
      const status = s.loadable ? '<span style="color:green">Ready</span>'
        : '<span style="color:orange">Missing ' + s.missing_count + ' mods</span>';
      return '<div style="padding:8px;border-bottom:1px solid var(--border)">'
        + '<strong>' + esc(s.name) + '</strong> '
        + status + ' '
        + '<small style="color:var(--gray-text)">' + s.total_mods + ' mods</small>'
        + '</div>';
    }).join('');
  } catch (e: any) {
    el.innerHTML = '<div style="padding:16px;color:var(--red)">Error: ' + esc(e.message) + '</div>';
  }
}

async function uploadSave() {
  const input = document.getElementById("saves-file-upload") as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const resp = await fetch("/api/saves/analyze", { method: "POST", body: fd });
    const data = await resp.json();
    toast('Found ' + data.mod_count + ' mods in ' + data.filename, 'success');
    scanSaves();
  } catch (e: any) {
    toast('Upload failed: ' + e.message, 'error');
  }
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

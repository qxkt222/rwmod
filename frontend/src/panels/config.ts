/**
 * Config panel — view and edit rwmod settings.
 */
import { api } from "../api";
import { toast } from "../toast";

export function initConfigPanel() {
  document.getElementById("btn-save-config")?.addEventListener("click", saveConfig);
  document.getElementById("btn-check-steamcmd")?.addEventListener("click", checkSteamCMD);
  loadConfig();
  checkSteamCMD();
}

async function loadConfig() {
  try {
    const cfg = await api.getConfig();
    (document.getElementById("cfg-steamcmd") as HTMLInputElement).value = cfg.steamcmd_path;
    (document.getElementById("cfg-mods") as HTMLInputElement).value = cfg.mods_dir;
    (document.getElementById("cfg-backup") as HTMLInputElement).value = cfg.backup_dir || "";

    const icon = (ok: boolean) => ok ? "✅" : "❌ 未找到";
    document.getElementById("config-display")!.innerHTML = `
      <div>SteamCMD: ${esc(cfg.steamcmd_path)} ${icon(cfg.steamcmd_exists)}</div>
      <div>Mods 目录: ${esc(cfg.mods_dir)} ${icon(cfg.mods_dir_exists)}</div>
      <div>游戏目录: ${esc(cfg.rimworld_dir)}</div>
      <div>备份目录: ${esc(cfg.backup_dir || "未设置")}</div>
    `;
  } catch (e: any) {
    document.getElementById("config-display")!.textContent = `加载失败: ${e.message}`;
  }
}

async function saveConfig() {
  try {
    await api.saveConfig({
      steamcmd_path: (document.getElementById("cfg-steamcmd") as HTMLInputElement).value,
      mods_dir: (document.getElementById("cfg-mods") as HTMLInputElement).value,
      rimworld_dir: (document.getElementById("cfg-rimworld") as HTMLInputElement).value,
      backup_dir: (document.getElementById("cfg-backup") as HTMLInputElement).value,
    });
    toast("配置已保存", "success");
    loadConfig();
    checkSteamCMD();
  } catch (e: any) {
    toast(`保存失败: ${e.message}`, "error");
  }
}

async function checkSteamCMD() {
  const el = document.getElementById("steamcmd-status");
  if (!el) return;
  el.innerHTML = '<span style="color:var(--gray-text)">⏳ 检测中...</span>';
  try {
    const resp = await fetch("/api/steamcmd/check");
    const data = await resp.json();
    if (data.ok) {
      el.innerHTML = '<span style="color:var(--green)">✅ ' + data.msg + '</span>';
    } else {
      el.innerHTML = '<span style="color:var(--red)">❌ ' + data.msg + '</span>';
    }
  } catch (e: any) {
    el.innerHTML = '<span style="color:var(--red)">❌ 检测失败: ' + e.message + '</span>';
  }
}

function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

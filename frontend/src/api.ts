/**
 * REST API client for rwmod backend.
 */
const BASE = "/api";

export interface ModEntry {
  folder: string;
  name: string;
  package_id: string;
  workshop_id: string;
}

export interface ConfigData {
  steamcmd_path: string;
  mods_dir: string;
  rimworld_dir: string;
  backup_dir: string;
  steamcmd_exists: boolean;
  mods_dir_exists: boolean;
}

export interface DownloadResult {
  id: string;
  ok: boolean;
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + url, init);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error((body as any).detail || `${resp.status} ${resp.statusText}`);
  }
  return resp.json();
}

export const api = {
  listMods: () => req<ModEntry[]>("/mods"),

  downloadMods: (ids: string[], force: boolean) =>
    req<{ total: number; results: DownloadResult[] }>("/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids, force }),
    }),

  importCollection: (collectionId: string, force: boolean) =>
    req<{ total: number; results: DownloadResult[] }>("/import/collection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ collection_id: collectionId, force }),
    }),

  importFile: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{ total: number; results: DownloadResult[] }>("/import/file", {
      method: "POST",
      body: fd,
    });
  },

  importSort: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return req<{
      total_packages: number;
      missing: number;
      unknown: string[];
      downloaded: number;
      results: DownloadResult[];
    }>("/import/sort", { method: "POST", body: fd });
  },

  getConfig: () => req<ConfigData>("/config"),

  saveConfig: (cfg: Partial<ConfigData>) =>
    req<{ ok: boolean }>("/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    }),

  /** SSE download stream — returns an AbortController + async generator */
  downloadStream(
    id: string,
    force: boolean,
    onEvent: (evt: SSEEvent) => void,
  ): AbortController {
    const ctrl = new AbortController();
    const url = `${BASE}/download/stream?id=${encodeURIComponent(id)}&force=${force}`;

    fetch(url, { signal: ctrl.signal })
      .then(async (resp) => {
        const reader = resp.body?.getReader();
        if (!reader) return;
        const dec = new TextDecoder();
        let buf = "";
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop()!;
          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                onEvent(JSON.parse(line.slice(6)));
              } catch { /* ignore bad JSON */ }
            }
          }
        }
      })
      .catch(() => { /* aborted or network error */ });

    return ctrl;
  },
};

export interface SSEEvent {
  event: string;
  id?: string;
  msg?: string;
  line?: string;
  mod_id?: string;
}

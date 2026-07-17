/**
 * WebSocket client for real-time download progress.
 * Falls back to SSE via api.downloadStream if WS unavailable.
 */
interface WSMessage {
  type: string;
  mod_id?: string;
  msg?: string;
  line?: string;
  total?: number;
  ok?: number;
  fail?: number;
}

type WSCallback = (msg: WSMessage) => void;

let ws: WebSocket | null = null;
let listeners: WSCallback[] = [];
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectCount = 0;
const MAX_RECONNECT = 5;

export function connectWS(onMessage: WSCallback): WebSocket | null {
  if (ws && ws.readyState === WebSocket.OPEN) return ws;

  const protocol = location.protocol === "https:" ? "wss" : "ws";
  try {
    ws = new WebSocket(`${protocol}://${location.host}/ws`);
  } catch {
    console.log("[WS] WebSocket not available, using REST fallback");
    return null;
  }

  ws.onopen = () => {
    console.log("[WS] connected");
    reconnectCount = 0;
  };

  ws.onmessage = (e) => {
    try {
      const msg: WSMessage = JSON.parse(e.data);
      onMessage(msg);
      for (const fn of listeners) fn(msg);
    } catch { /* ignore */ }
  };

  ws.onclose = () => {
    console.log("[WS] disconnected");
    ws = null;
    reconnectCount += 1;
    if (reconnectCount <= MAX_RECONNECT) {
      const delay = Math.min(2000 * reconnectCount, 15000);
      reconnectTimer = setTimeout(() => connectWS(onMessage), delay);
    } else {
      console.log("[WS] max retries reached, using REST fallback");
    }
  };

  ws.onerror = () => ws?.close();

  return ws;
}

export function addWSListener(fn: WSCallback) {
  listeners.push(fn);
}

export function removeWSListener(fn: WSCallback) {
  listeners = listeners.filter((f) => f !== fn);
}

export function disconnectWS() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectCount = MAX_RECONNECT; // prevent further reconnect
  listeners = [];
  ws?.close();
  ws = null;
}

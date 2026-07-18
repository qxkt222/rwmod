/**
 * Toast notification system — non-blocking, auto-dismissing.
 * Supports success, error, warning, and info types.
 */

type ToastType = "success" | "error" | "warn" | "info";

const ICONS: Record<ToastType, string> = {
  success: "✅",
  error: "❌",
  warn: "⚠️",
  info: "ℹ️",
};

let _container: HTMLElement | null = null;

function ensureContainer(): HTMLElement {
  if (_container) return _container;
  _container = document.getElementById("toast-container");
  if (!_container) {
    _container = document.createElement("div");
    _container.id = "toast-container";
    _container.style.cssText =
      "position:fixed;bottom:20px;right:20px;z-index:9999;display:flex;flex-direction:column-reverse;gap:8px;pointer-events:none;";
    document.body.appendChild(_container);
  }
  return _container;
}

export function toast(
  msg: string,
  type: ToastType = "success",
  duration = 3500,
): void {
  const container = ensureContainer();
  const el = document.createElement("div");

  const colors: Record<ToastType, string> = {
    success: "#27AE60",
    error: "#E74C3C",
    warn: "#F39C12",
    info: "#1A6FB5",
  };

  el.style.cssText = [
    `background:${colors[type]}`,
    "color:#fff",
    "padding:10px 18px",
    "border-radius:6px",
    "font-size:13px",
    "font-weight:500",
    "box-shadow:0 4px 12px rgba(0,0,0,0.15)",
    "pointer-events:auto",
    "animation:toastIn .25s ease",
    "max-width:360px",
    "word-break:break-word",
  ].join(";");

  el.textContent = `${ICONS[type]} ${msg}`;
  container.appendChild(el);

  const timer = setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity .2s";
    setTimeout(() => el.remove(), 200);
  }, duration);

  // Click to dismiss early
  el.addEventListener("click", () => {
    clearTimeout(timer);
    el.remove();
  });
}

/** Handle fetch errors consistently — shows toast + logs to console */
export function handleError(err: unknown, context = ""): void {
  const msg =
    err instanceof Error ? err.message : String(err);
  toast(context ? `${context}: ${msg}` : msg, "error");
  console.error(`[rwmod] ${context}`, err);
}

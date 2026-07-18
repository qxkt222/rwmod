/**
 * Client-side router using History API.
 *
 * Panel names map to URL hashes (e.g., #download, #mods).
 * Clicking a nav tab updates the URL; browser back/forward
 * restores the correct panel.
 *
 * Usage:
 *   import { initRouter } from "./router";
 *   initRouter(onPanelChange);
 */

type PanelName = string;
type PanelChangeHandler = (panel: PanelName) => void;

/**
 * Initialize client-side routing.
 *
 * @param onPanelChange — called when the active panel changes
 * @returns a cleanup function
 */
export function initRouter(onPanelChange: PanelChangeHandler): () => void {
  // ── listen for nav clicks (delegated to document) ────────────
  const clickHandler = (e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest(
      "[data-panel]",
    ) as HTMLElement | null;
    if (!target) return;

    const panel = target.dataset.panel;
    if (!panel) return;

    e.preventDefault();
    navigate(panel);
  };

  document.addEventListener("click", clickHandler);

  // ── listen for browser back/forward ──────────────────────────
  const popHandler = () => {
    const panel = readPanelFromHash();
    onPanelChange(panel);
  };

  window.addEventListener("popstate", popHandler);

  // ── initial load — restore from URL or default ───────────────
  const initial = readPanelFromHash() || "dashboard";
  replaceState(initial); // don't push a new history entry on load

  // Trigger initial panel
  onPanelChange(initial);

  return () => {
    document.removeEventListener("click", clickHandler);
    window.removeEventListener("popstate", popHandler);
  };
}

/** Navigate to a panel — updates URL, triggers callback. */
export function navigate(panel: PanelName): void {
  window.history.pushState({ panel }, "", `#${panel}`);
  // popstate doesn't fire on pushState, so we manually trigger
  window.dispatchEvent(new PopStateEvent("popstate", { state: { panel } }));
}

/** Replace current history entry — used for initial load. */
function replaceState(panel: PanelName): void {
  window.history.replaceState({ panel }, "", `#${panel}`);
}

/** Read the current panel from URL hash. */
function readPanelFromHash(): PanelName | null {
  const hash = window.location.hash.slice(1); // remove #
  if (!hash) return null;
  // Only accept known panel names
  const known = new Set([
    "dashboard", "download", "collection", "import", "mods",
    "search", "queue", "rimsort", "profiles", "history",
    "backups", "config", "updates",
  ]);
  return known.has(hash) ? hash : null;
}

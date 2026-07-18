/**
 * Lightweight UI component system for vanilla TypeScript.
 *
 * Each "component" is a function that returns a cleanup function.
 * Components manage their own DOM subtree and state subscriptions.
 *
 * Usage:
 *   const cleanup = mountPanel("#panel-id", init);
 *   // later: cleanup();  // removes listeners and DOM
 */

import { store, type AppState } from "./store";

type Cleanup = () => void;

/**
 * Register a panel component.
 * - `selector`: CSS selector for the panel container.
 * - `init`: Function that runs once, returns optional cleanup.
 */
export function mountPanel(
  selector: string,
  init: (el: HTMLElement) => Cleanup | void,
): Cleanup {
  const el = document.querySelector(selector) as HTMLElement | null;
  if (!el) return () => {};

  const cleanup = init(el);

  // Auto-subscribe to state changes for reactive DOM updates
  const unsubs: (() => void)[] = [];

  return () => {
    cleanup?.();
    unsubs.forEach((u) => u());
  };
}

/**
 * Subscribe to a store key and update a DOM element's textContent.
 * Returns an unsubscribe function.
 */
export function bindText<K extends keyof AppState>(
  key: K,
  selector: string,
  format?: (val: AppState[K]) => string,
): () => void {
  return store.subscribe(key, (val) => {
    const els = document.querySelectorAll(selector);
    const text = format ? format(val) : String(val ?? "");
    els.forEach((el) => { el.textContent = text; });
  });
}

/**
 * Set an element's text safely (HTML escaped).
 */
export function setText(selector: string, text: string): void {
  const el = document.querySelector(selector);
  if (el) el.textContent = text;
}

/**
 * Escape HTML entities to prevent XSS.
 */
export function esc(s: string): string {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

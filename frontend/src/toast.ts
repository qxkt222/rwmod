/**
 * Toast notification system.
 */

export function toast(msg: string, type: "success" | "error" = "success") {
  const container = document.getElementById("toast-container")!;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("removing");
    setTimeout(() => el.remove(), 200);
  }, 3500);
}

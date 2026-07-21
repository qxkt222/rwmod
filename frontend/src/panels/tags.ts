import { toast } from '../toast';

export function initTagsPanel() {
  loadTags();
}

async function loadTags() {
  const el = document.getElementById('tags-list');
  if (!el) return;
  try {
    const resp = await fetch('/api/tags');
    const data = await resp.json();
    if (!data.tags?.length) {
      el.innerHTML = '<div>No tags yet</div>';
      return;
    }
    el.innerHTML = data.tags.map((t: any) => (
      '<div class=tag-row data-tag="' + esc(t.tag) + '">' +
      '<span class=tag>' + esc(t.tag) + '</span>' +
      '<span>' + t.count + ' mods</span>' +
      '</div>'
    )).join('');
    el.querySelectorAll('.tag-row').forEach(row => {
      row.addEventListener('click', async () => {
        const tag = (row as HTMLElement).dataset.tag!;
        const detail = document.getElementById('tags-detail');
        if (!detail) return;
        const r = await fetch('/api/tags/by-tag/' + encodeURIComponent(tag));
        const d = await r.json();
        detail.innerHTML = '<h4>#' + esc(tag) + '</h4>' +
          (d.folders?.map((f: string) => '<div>' + esc(f) + '</div>').join('') || '<div>None</div>');
      });
    });
  } catch (e: any) {
    el.innerHTML = '<div>Error: ' + esc(e.message) + '</div>';
  }
}

function esc(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
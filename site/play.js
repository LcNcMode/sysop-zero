"use strict";
// Full-window player: play.html#/<slug>. The only way the gallery opens a prod outside the dialog.
(async () => {
  const title = document.getElementById("p-title");
  const m = location.hash.match(/^#\/(.+)$/);
  if (!m) { title.textContent = "no prod selected"; return; }
  const slug = decodeURIComponent(m[1]);
  try {
    const data = await fetch("prods.json", { cache: "no-cache" }).then((r) => r.json());
    const p = (data.prods || []).find((x) => x.slug === slug);
    if (!p || !p.runnable) { title.textContent = "this prod can't run in the browser"; return; }
    title.textContent = `${p.title} — ${p.handles.join(", ")}`;
    document.title = `${p.title} — Sysop Zero`;
    const nfo = document.getElementById("p-nfo");
    if (p.has_nfo) { nfo.href = prodUrl(p).base + "nfo.txt"; nfo.hidden = false; }
    loadIntoFrame(document.getElementById("p-frame"), p);
  } catch (e) {
    title.textContent = "could not load prods.json: " + e.message;
  }
})();

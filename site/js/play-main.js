// play-main.js — entry point of the full-window player (play.html#/<slug>).
// This page is the only way a prod is opened outside the gallery dialog: the "new window"
// button links here, and the guard in every published prod page redirects here.

import { $ } from "./dom.js";
import { loadProds } from "./data.js";
import { nfoUrl } from "./urls.js";
import { currentSlug } from "./router.js";
import { createStage } from "./stage.js";
import { initTextSize } from "./textsize.js";

async function main() {
  initTextSize();
  const title = $("#p-title");
  const slug = currentSlug();
  if (!slug) { title.textContent = "no prod selected"; return; }

  const { prods } = await loadProds();
  const p = prods.find((x) => x.slug === slug);
  if (!p || !p.runnable) { title.textContent = "this prod can't run in the browser"; return; }

  title.textContent = `${p.title} — ${p.handles.join(", ")}`;
  document.title = `${p.title} — Sysop Zero`;
  if (p.has_nfo) { $("#p-nfo").href = nfoUrl(p); $("#p-nfo").hidden = false; }

  const stage = createStage({ frame: $("#p-frame"), gate: $("#p-gate") });
  const started = await stage.start(p);
  if (started === false) location.href = "./"; // "back" on the heads-up: to the gallery
}

// A different prod in the same tab (edited address, or a link): start over.
window.addEventListener("hashchange", () => location.reload());

main().catch((e) => { $("#p-title").textContent = "could not load the file list: " + e.message; });

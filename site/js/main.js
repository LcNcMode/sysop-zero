// main.js — entry point of the gallery (index.html). It only connects the other modules:
//
//   data.js      load config.json and prods.json
//   filters.js   the dropdowns
//   card.js      prod → card HTML
//   router.js    #/<slug> in the address bar
//   dialog.js    the player dialog (uses stage.js → gate.js, player.js)
//   textsize.js  the text size button
//
// New feature? Put it in its own module and add one or two lines here. See site/README.md.

import { $, esc } from "./dom.js";
import { loadConfig, loadProds } from "./data.js";
import { submitUrl } from "./urls.js";
import { initFilters, applyFilters } from "./filters.js";
import { cardHtml } from "./card.js";
import { initDialog } from "./dialog.js";
import { initTextSize } from "./textsize.js";
import * as router from "./router.js";

async function main() {
  initTextSize($("#text-size"));
  const [cfg, data] = await Promise.all([loadConfig(), loadProds()]);
  const prods = data.prods;

  // Header and footer text from config.
  if (cfg.title) { document.title = cfg.title; $("#site-title").textContent = cfg.title; }
  $("#tagline").textContent = cfg.tagline || "";
  const submit = submitUrl(cfg);
  if (submit) { $("#submit-link").href = submit; $("#submit-link").hidden = false; }
  $("#generated").textContent = data.generated ? "updated " + data.generated.slice(0, 10) : "";

  // The grid.
  const render = () => {
    const list = applyFilters(prods);
    $("#grid").innerHTML = list.length
      ? list.map((p) => cardHtml(p, cfg)).join("")
      : '<p class="dim">no prods match.</p>';
  };
  initFilters(prods, render);
  render();

  // The player: a click changes the address, the address opens or closes the dialog.
  const dialog = initDialog(() => router.leave());
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-run]");
    if (b) router.go(b.dataset.run);
  });
  router.onRoute((slug) => {
    const p = slug && prods.find((x) => x.slug === slug && x.runnable);
    if (p) dialog.open(p); else { dialog.close(); if (slug) router.leave(); }
  });
}

main().catch((e) => {
  $("#grid").innerHTML = `<p class="dim">could not load the file list: ${esc(e.message)}</p>`;
});

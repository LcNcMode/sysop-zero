"use strict";
// Gallery: reads prods.json (built from every prods/*/prod.yaml by scripts/prodcheck.py)
// and runs web prods in a sandboxed iframe (player.js). All paths are relative, so the site works
// at a GitHub Pages project path or on a custom domain (site/config.json).
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let PRODS = [], CFG = {};

async function load() {
  const [cfg, data] = await Promise.all([
    fetch("config.json").then((r) => r.json()).catch(() => ({})),
    fetch("prods.json", { cache: "no-cache" }).then((r) => r.json()),
  ]);
  CFG = cfg;
  if (cfg.title) { document.title = cfg.title; $("#site-title").textContent = cfg.title; }
  $("#tagline").textContent = cfg.tagline || "";
  if (cfg.repo_url) { const a = $("#repo-link"); a.href = cfg.repo_url.replace(/\/$/, "") + "/issues/new/choose"; a.hidden = false; }
  $("#generated").textContent = data.generated ? "updated " + data.generated.slice(0, 10) : "";
  PRODS = data.prods || [];
  const cats = [...new Set(PRODS.map((p) => p.category))].sort();
  $("#f-category").insertAdjacentHTML("beforeend", cats.map((c) => `<option>${esc(c)}</option>`).join(""));
  render();
  route();
}

function render() {
  const fc = $("#f-category").value, fp = $("#f-provenance").value;
  const list = PRODS.filter((p) => (!fc || p.category === fc) && (!fp || p.provenance.type === fp));
  $("#grid").innerHTML = list.length ? list.map(card).join("") : '<p class="dim">no prods match.</p>';
}

function card(p) {
  const base = `prods/${encodeURIComponent(p.slug)}/`;
  const prov = p.provenance || {};
  return `<article class="card" id="prod-${esc(p.slug)}">
    <h2>${esc(p.title)}</h2>
    <div class="by">by ${esc(p.handles.join(", "))}${p.group && !p.handles.includes(p.group) ? " of " + esc(p.group) : ""}</div>
    <div class="meta">
      <span class="tag">${esc(p.category)}</span><span class="tag">${esc(p.platform)}</span><span class="tag">${esc(p.year)}</span>
      <span class="tag prov-${esc(prov.type)}" title="${esc((prov.models || []).join("; "))}">${esc(prov.type)}</span>
      <span class="tag">${esc(p.license)}</span>
      ${p.party ? `<span class="tag">${esc(p.party)}</span>` : ""}
      ${p.drift && p.drift.length ? `<span class="tag drift" title="${esc(p.drift.join("\n"))}">drift ×${p.drift.length}</span>` : ""}
    </div>
    ${prov.notes ? `<p class="dim">${esc(prov.notes)}</p>` : ""}
    <div class="actions">
      ${p.runnable ? `<button data-run="${esc(p.slug)}">▶ run</button>` : '<span class="dim">not runnable in browser</span>'}
      ${p.download ? `<a href="${base}${p.download.split("/").map(encodeURIComponent).join("/")}" download>download</a>` : ""}
      ${(p.links || []).filter((l) => /^https:\/\//.test(l.url)).map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)} ↗</a>`).join("")}
      ${p.has_nfo ? `<a href="${base}nfo.txt" target="_blank" rel="noopener">nfo</a>` : ""}
      <a href="${CFG.repo_url ? CFG.repo_url.replace(/\/$/, "") + "/tree/HEAD/prods/" + encodeURIComponent(p.slug) : base + "prod.yaml"}" target="_blank" rel="noopener">${CFG.repo_url ? "source" : "prod.yaml"}</a>
    </div>
  </article>`;
}

function play(slug) {
  const p = PRODS.find((x) => x.slug === slug);
  if (!p || !p.runnable) return;
  const { base } = prodUrl(p);
  $("#p-title").textContent = `${p.title} — ${p.handles.join(", ")}`;
  // "open full window" goes to the sandboxed player page, never to the prod's own URL.
  $("#p-open").href = "play.html#/" + encodeURIComponent(p.slug);
  $("#p-nfo").href = base + "nfo.txt";
  $("#p-nfo").hidden = !p.has_nfo;
  loadIntoFrame($("#p-frame"), p);
  $("#player").showModal();
  if (location.hash !== "#/" + slug) history.replaceState(null, "", "#/" + slug);
}

function stop() { $("#p-frame").src = "about:blank"; if ($("#player").open) $("#player").close(); history.replaceState(null, "", location.pathname + location.search); }
function route() { const m = location.hash.match(/^#\/(.+)$/); if (m) play(decodeURIComponent(m[1])); }

document.addEventListener("click", (e) => { const b = e.target.closest("[data-run]"); if (b) play(b.dataset.run); });
$("#p-close").addEventListener("click", stop);
$("#player").addEventListener("close", () => { $("#p-frame").src = "about:blank"; });
$("#f-category").addEventListener("change", render);
$("#f-provenance").addEventListener("change", render);
window.addEventListener("hashchange", route);
load().catch((e) => { $("#grid").innerHTML = `<p class="dim">could not load prods.json: ${esc(e.message)}</p>`; });

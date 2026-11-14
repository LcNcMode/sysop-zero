// card.js — turns one prod into the HTML of its gallery card. Pure: data in, string out.
//
// To show a new fact about a prod: add it to prods.json in scripts/prodcheck.py (build_site),
// document it in the Prod typedef in data.js, then add one line to the right part below.
// Every value goes through esc(). No inline styles (the CSP blocks them): use classes from
// css/card.css.

import { esc, humanBytes } from "./dom.js";
import { nfoUrl, downloadUrl, sourceLink } from "./urls.js";

/** @typedef {import("./data.js").Prod} Prod */
/** @typedef {import("./data.js").Config} Config */

const tag = (text, cls = "") => `<li class="tag ${cls}">${esc(text)}</li>`;

/** "by Venture of Xanadu" @param {Prod} p */
function byline(p) {
  const of = p.group && !p.handles.includes(p.group) ? " of " + esc(p.group) : "";
  return `<p class="by">by ${esc(p.handles.join(", "))}${of}</p>`;
}

/** Category, platform, year, size, license, party. @param {Prod} p */
function facts(p) {
  return `<ul class="meta">
      ${tag(p.category)}${tag(p.platform)}${tag(p.year)}${tag(humanBytes(p.bytes))}${tag(p.license)}
      ${p.party ? tag(p.party) : ""}
    </ul>`;
}

/** Declared provenance: the type, and the AI tools as readable text. @param {Prod} p */
function provenance(p) {
  const prov = p.provenance || {};
  const models = prov.models || [];
  const list = models.length
    ? ` made with:<ul>${models.map((m) => `<li>${esc(m)}</li>`).join("")}</ul>`
    : "";
  const notes = prov.notes
    ? `<details><summary>how it was made</summary><p>${esc(prov.notes.trim())}</p></details>`
    : "";
  return `<div class="made"><span class="tag prov-${esc(prov.type)}">${esc(prov.type)}</span>${list}</div>${notes}`;
}

/** Drift found by CI, as a neutral note. @param {Prod} p */
function drift(p) {
  if (!p.drift || !p.drift.length) return "";
  return `<div class="drift">declared vs observed, ${p.drift.length} note${p.drift.length > 1 ? "s" : ""}:
      <ul>${p.drift.map((d) => `<li>${esc(d)}</li>`).join("")}</ul></div>`;
}

/** Run, download, links, nfo, source. @param {Prod} p @param {Config} cfg */
function actions(p, cfg) {
  const ext = 'target="_blank" rel="noopener noreferrer"';
  const src = sourceLink(cfg, p);
  const links = (p.links || [])
    .filter((l) => /^https:\/\//.test(l.url)) // https only: no javascript: or data: links
    .map((l) => `<a class="btn" href="${esc(l.url)}" ${ext}>${esc(l.label)} ↗</a>`)
    .join("");
  return `<div class="actions">
      ${p.runnable
        ? `<button type="button" class="btn-primary" data-run="${esc(p.slug)}">▶ run</button>`
        : '<span class="dim">not runnable in browser</span>'}
      ${p.download ? `<a class="btn" href="${esc(downloadUrl(p))}" download>download</a>` : ""}
      ${links}
      ${p.has_nfo ? `<a class="btn" href="${esc(nfoUrl(p))}" ${ext}>nfo</a>` : ""}
      <a class="btn" href="${esc(src.href)}" ${ext}>${esc(src.label)}</a>
    </div>`;
}

/**
 * @param {Prod} p
 * @param {Config} cfg
 * @returns {string} HTML for one <article class="card">
 */
export function cardHtml(p, cfg) {
  return `<article class="card" id="prod-${esc(p.slug)}">
    <h2>${esc(p.title)}</h2>
    ${byline(p)}
    ${facts(p)}
    ${provenance(p)}
    ${drift(p)}
    ${actions(p, cfg)}
  </article>`;
}

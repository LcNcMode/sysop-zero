// filters.js — the dropdowns above the gallery (category, provenance).
//
// To add a filter: add a <select id="f-..."> to index.html, then one entry to FILTERS below
// with how to read that value from a prod. Nothing else needs to change.

import { $, esc } from "./dom.js";

/** @typedef {import("./data.js").Prod} Prod */

/** @type {{id: string, value: (p: Prod) => string, fill?: boolean}[]} */
const FILTERS = [
  // fill: true = the options are the values that occur in the prods (otherwise they are in the HTML)
  { id: "#f-category", value: (p) => p.category, fill: true },
  { id: "#f-provenance", value: (p) => p.provenance.type },
];

/**
 * Fill the dropdowns and call `onChange` whenever the visitor changes one.
 * @param {Prod[]} prods
 * @param {() => void} onChange
 */
export function initFilters(prods, onChange) {
  for (const f of FILTERS) {
    const sel = $(f.id);
    if (f.fill) {
      const values = [...new Set(prods.map(f.value))].sort();
      sel.insertAdjacentHTML("beforeend", values.map((v) => `<option>${esc(v)}</option>`).join(""));
    }
    sel.addEventListener("change", onChange);
  }
}

/** @param {Prod[]} prods @returns {Prod[]} the prods that match every dropdown */
export function applyFilters(prods) {
  return prods.filter((p) => FILTERS.every((f) => { const want = $(f.id).value; return !want || f.value(p) === want; }));
}

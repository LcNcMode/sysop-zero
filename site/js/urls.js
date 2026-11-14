// urls.js — every address the site links to is built here.
//
// Rules:
//  - Paths are relative, so the site works at a GitHub Pages project path and on a custom domain.
//  - The repo address comes from config (cfg.repo_url). Never write an owner or repo name here.
//  - A prod is never linked directly for running: use playerUrl(). See js/player.js for why.

/** @typedef {import("./data.js").Prod} Prod */
/** @typedef {import("./data.js").Config} Config */

const encPath = (path) => path.split("/").map(encodeURIComponent).join("/");
const repo = (cfg) => (cfg.repo_url || "").replace(/\/$/, "");

/** Folder of a prod, with a trailing slash. @param {Prod} p */
export const prodBase = (p) => `prods/${encodeURIComponent(p.slug)}/`;

/** The file the sandboxed iframe loads. @param {Prod} p */
export const entryUrl = (p) => prodBase(p) + encPath(p.entry);

/** @param {Prod} p */
export const nfoUrl = (p) => prodBase(p) + "nfo.txt";

/** @param {Prod} p @returns {string|null} */
export const downloadUrl = (p) => (p.download ? prodBase(p) + encPath(p.download) : null);

/** The full-window, sandboxed player page for a prod. @param {string} slug */
export const playerUrl = (slug) => "play.html#/" + encodeURIComponent(slug);

/** Where to read a prod's source: the repo folder, or its prod.yaml if no repo is known.
 *  @param {Config} cfg @param {Prod} p @returns {{href: string, label: string}} */
export function sourceLink(cfg, p) {
  return repo(cfg)
    ? { href: `${repo(cfg)}/tree/HEAD/prods/${encodeURIComponent(p.slug)}`, label: "source" }
    : { href: prodBase(p) + "prod.yaml", label: "prod.yaml" };
}

// player.js — loads a prod into a sandboxed iframe. SECURITY-CRITICAL, keep it small.
//
// Prods are published on the same origin as the gallery, so they may only run inside this
// sandbox: allow-scripts WITHOUT allow-same-origin gives the prod an opaque origin, so it can't
// script the gallery, read its storage, or lift its own sandbox. Asset fetches rely on CORS,
// which GitHub Pages sends (Access-Control-Allow-Origin: *). Every published prod HTML file also
// carries a guard (scripts/prodcheck.py) that refuses to run anywhere but in such a sandbox.
//
// Do not add sandbox flags (above all: never allow-same-origin, allow-top-navigation or
// allow-popups) without the maintainer's explicit say-so. See docs/OPERATIONS.md.

import { entryUrl } from "./urls.js";

/** @typedef {import("./data.js").Prod} Prod */

export const PROD_SANDBOX = "allow-scripts allow-pointer-lock";

// Navigate the iframe without adding a history entry. Setting `frame.src` would add one each
// time, and the Back button would then step the iframe backwards instead of closing the player
// (router.js relies on Back). The sandbox attribute applies to every navigation of the frame.
function navigate(frame, url) {
  if (frame.contentWindow) frame.contentWindow.location.replace(url);
  else frame.src = url;
}

/**
 * Start a prod in the given iframe.
 * @param {HTMLIFrameElement} frame
 * @param {Prod} p
 */
export function loadIntoFrame(frame, p) {
  frame.setAttribute("sandbox", PROD_SANDBOX); // set before navigating, every time
  frame.setAttribute("referrerpolicy", "no-referrer");
  navigate(frame, new URL(entryUrl(p), document.baseURI).href);
  frame.dataset.slug = p.slug; // what is loaded, for tests and debugging
}

/** Stop whatever runs in the iframe (also stops its sound). @param {HTMLIFrameElement} frame */
export function unloadFrame(frame) {
  if (!frame.dataset.slug) return; // nothing loaded
  navigate(frame, "about:blank");
  delete frame.dataset.slug;
}

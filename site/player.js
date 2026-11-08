"use strict";
// Shared by the gallery (index.html) and the full-window player (play.html).
//
// Prods are published on the same origin as the gallery, so they may only run inside this
// sandbox: allow-scripts without allow-same-origin gives the prod an opaque origin, so it can't
// script the gallery, read its storage, or lift its own sandbox. Asset fetches rely on CORS,
// which GitHub Pages sends (Access-Control-Allow-Origin: *). Every published prod HTML file also
// carries a guard (scripts/prodcheck.py) that refuses to run anywhere but in such a sandbox.
const PROD_SANDBOX = "allow-scripts allow-pointer-lock";

function prodUrl(p) {
  const base = `prods/${encodeURIComponent(p.slug)}/`;
  return { base, entry: base + p.entry.split("/").map(encodeURIComponent).join("/") };
}

function loadIntoFrame(frame, p) {
  frame.setAttribute("sandbox", PROD_SANDBOX); // set before src, every time
  frame.setAttribute("referrerpolicy", "no-referrer");
  frame.src = prodUrl(p).entry;
}

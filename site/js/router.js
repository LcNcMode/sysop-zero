// router.js — the address bar as state. One route exists today:
//
//   index.html#/<slug>   the gallery with that prod open in the player
//
// Opening a prod adds a history entry, so the Back button (phone gesture, TV remote, browser)
// closes the player instead of leaving the site.

let pushed = false; // true when the current #/slug entry was added by go(), not by a deep link

/** @returns {string|null} the slug in the address bar, or null */
export function currentSlug() {
  const m = location.hash.match(/^#\/(.+)$/);
  if (!m) return null;
  try { return decodeURIComponent(m[1]); } catch { return null; }
}

/** Open a prod: changes the address, which calls the onRoute handler. @param {string} slug */
export function go(slug) {
  if (currentSlug() === slug) return;
  pushed = true;
  location.hash = "#/" + encodeURIComponent(slug);
}

/** Leave the prod route. Safe to call when already on the plain gallery. */
export function leave() {
  if (currentSlug() === null) return;
  if (pushed) { pushed = false; history.back(); return; }
  // Arrived by deep link: there is no gallery entry to go back to, so rewrite this one.
  history.replaceState(null, "", location.pathname + location.search);
}

/**
 * Call `handler(slug|null)` now and on every later address change.
 * @param {(slug: string|null) => void} handler
 */
export function onRoute(handler) {
  window.addEventListener("hashchange", () => {
    if (currentSlug() === null) pushed = false;
    handler(currentSlug());
  });
  handler(currentSlug());
}

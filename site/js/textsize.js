// textsize.js — the "text size" button: normal → large → extra large → normal.
// It sets data-size on <html>; css/tokens.css turns that into a bigger 1rem, and because every
// size on the site is in rem, everything grows together. Made for TVs across the room, useful
// for anyone. The choice is remembered on the device.

import { recall, remember } from "./storage.js";

const SIZES = ["m", "l", "xl"];
const LABELS = { m: "A", l: "A+", xl: "A++" };
const KEY = "text-size";

/**
 * Apply the remembered size, and wire the button if the page has one.
 * @param {HTMLButtonElement|null} [button] the button that cycles the size (play.html has none)
 */
export function initTextSize(button = null) {
  let size = SIZES.includes(recall(KEY)) ? recall(KEY) : "m";
  const apply = () => {
    if (size === "m") delete document.documentElement.dataset.size;
    else document.documentElement.dataset.size = size;
    if (button) button.textContent = `text size: ${LABELS[size]}`;
  };
  apply();
  if (!button) return;
  button.addEventListener("click", () => {
    size = SIZES[(SIZES.indexOf(size) + 1) % SIZES.length];
    remember(KEY, size);
    apply();
  });
  apply();
}

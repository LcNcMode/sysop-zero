// dialog.js — the player dialog in the gallery: title bar, buttons, and the stage inside it.
// It only shows and hides. Which prod is open is decided by the address (router.js);
// main.js connects the two.

import { $ } from "./dom.js";
import { nfoUrl, playerUrl } from "./urls.js";
import { createStage } from "./stage.js";

/** @typedef {import("./data.js").Prod} Prod */

/**
 * @param {() => void} onClosed called whenever the dialog closes, however it was closed
 *        (close button, Esc, "back" on the heads-up, Back button)
 * @returns {{open: (p: Prod) => void, close: () => void}}
 */
export function initDialog(onClosed) {
  const dialog = $("#player");
  const frame = $("#p-frame");
  const stage = createStage({ frame, gate: $("#p-gate") });

  $("#p-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => { stage.stop(); onClosed(); });

  // Real fullscreen (no bar at all) where the browser has it. iPhones don't: the button stays hidden.
  const fs = $("#p-fs");
  if (document.fullscreenEnabled && frame.requestFullscreen) {
    fs.hidden = false;
    fs.addEventListener("click", () => frame.requestFullscreen().catch(() => {}));
  }

  return {
    async open(p) {
      $("#p-title").textContent = `${p.title} — ${p.handles.join(", ")}`;
      // "new window" goes to the sandboxed player page, never to the prod's own URL.
      $("#p-open").href = playerUrl(p.slug);
      $("#p-nfo").href = nfoUrl(p);
      $("#p-nfo").hidden = !p.has_nfo;
      if (!dialog.open) dialog.showModal();
      const started = await stage.start(p);
      if (!started && dialog.open) dialog.close(); // the visitor chose "back" on the heads-up
    },
    close() { if (dialog.open) dialog.close(); },
  };
}

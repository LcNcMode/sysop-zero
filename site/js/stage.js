// stage.js — "run this prod here": heads-up first if needed, then the sandboxed iframe.
// Used by both places a prod can run: the gallery dialog (dialog.js) and play.html (play-main.js).

import { loadIntoFrame, unloadFrame } from "./player.js";
import { needsHeadsUp, askHeadsUp, dismissHeadsUp } from "./gate.js";

/** @typedef {import("./data.js").Prod} Prod */

/**
 * @param {{frame: HTMLIFrameElement, gate: HTMLElement}} els the iframe and the empty notice element
 * @returns {{start: (p: Prod) => Promise<boolean|null>, stop: () => void}}
 *          start() resolves true when the prod was loaded, false when the visitor chose "back",
 *          and null when this start was overtaken (stop() or a newer start() came first).
 *          Callers must only react to false: a null belongs to a run that no longer matters.
 */
export function createStage({ frame, gate }) {
  let run = 0; // increases on every start/stop, so a late answer to an old notice is ignored

  return {
    async start(p) {
      const mine = ++run;
      unloadFrame(frame);
      if (needsHeadsUp()) {
        frame.hidden = true;
        const ok = await askHeadsUp(gate);
        if (mine !== run || ok === null) return null;
        if (!ok) return false;
      }
      frame.hidden = false;
      loadIntoFrame(frame, p);
      frame.focus(); // keys go to the prod (many start on space or enter)
      return true;
    },
    stop() {
      run++;
      dismissHeadsUp(gate);
      unloadFrame(frame);
    },
  };
}

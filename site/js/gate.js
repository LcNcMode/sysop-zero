// gate.js — the heads-up a visitor sees before their first prod: demos can flash and be loud.
//
// It is shown once per device (remembered in js/storage.js). If nothing can be remembered it is
// shown every time, which is the safe direction. Pressing "run it" is also the tap that lets
// browsers start sound on phones.
//
// Later idea (needs a schema change, so not done here): a per-prod `warnings` field in
// prod.yaml, so only prods that really flash ask, and ask every time.

import { recall, remember } from "./storage.js";

const KEY = "heads-up-seen";

/** @returns {boolean} true when the notice still has to be shown on this device */
export const needsHeadsUp = () => recall(KEY) !== "1";

/**
 * Show the notice inside `host` and wait for the visitor's choice.
 * @param {HTMLElement} host an empty element next to the iframe (class "gate" is styled in player.css)
 * @returns {Promise<boolean>} true = run the prod, false = go back
 */
export function askHeadsUp(host) {
  return new Promise((resolve) => {
    host.innerHTML = `
      <h2>Heads up</h2>
      <p>Prods can flash, strobe and get loud. If flashing lights are a problem for you, skip this one.</p>
      <p class="dim">Shown once on this device.</p>
      <div class="choices">
        <button type="button" class="btn-primary" data-choice="run">▶ run it</button>
        <button type="button" data-choice="back">back</button>
      </div>`;
    host.hidden = false;
    host.querySelector('[data-choice="run"]').focus();
    host.addEventListener("click", function onClick(e) {
      const b = e.target.closest("[data-choice]");
      if (!b) return;
      host.removeEventListener("click", onClick);
      dismissHeadsUp(host);
      const run = b.dataset.choice === "run";
      if (run) remember(KEY, "1");
      resolve(run);
    });
  });
}

/** Remove the notice (also used when the player closes while it is showing). @param {HTMLElement} host */
export function dismissHeadsUp(host) {
  host.hidden = true;
  host.innerHTML = "";
}

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

// The question that is on screen right now, if any: its listener and how to answer it.
// Only one can be open at a time; dismissing or asking again always settles the old one.
/** @type {{host: HTMLElement, onClick: (e: Event) => void, settle: (answer: boolean|null) => void}|null} */
let pending = null;

/**
 * Show the notice inside `host` and wait for the visitor's choice.
 * @param {HTMLElement} host an empty element next to the iframe (class "gate" is styled in player.css)
 * @returns {Promise<boolean|null>} true = run the prod, false = the visitor chose "back",
 *          null = the notice was dismissed by something else (player closed, another prod opened)
 */
export function askHeadsUp(host) {
  dismissHeadsUp(host);
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
    const onClick = (e) => {
      const b = e.target.closest("[data-choice]");
      if (!b) return;
      const run = b.dataset.choice === "run";
      if (run) remember(KEY, "1");
      close(run);
    };
    pending = { host, onClick, settle: resolve };
    host.addEventListener("click", onClick);
    host.querySelector('[data-choice="run"]').focus();
  });
}

/** Take the notice off screen and answer whoever is waiting for it. */
function close(answer) {
  if (!pending) return;
  const { host, onClick, settle } = pending;
  pending = null;
  host.removeEventListener("click", onClick);
  host.hidden = true;
  host.innerHTML = "";
  settle(answer);
}

/**
 * Remove the notice without a choice (the player closed while it was showing).
 * Whoever was waiting gets null. Safe to call when no notice is showing.
 * @param {HTMLElement} host
 */
export function dismissHeadsUp(host) {
  close(null);
  host.hidden = true;
  host.innerHTML = "";
}

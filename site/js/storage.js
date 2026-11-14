// storage.js — remember small choices on this device (text size, "seen the heads-up").
// localStorage can be missing or blocked (private mode, some TVs), so every call is guarded
// and the site must work when nothing is remembered. Nothing here is ever sent anywhere.

const PREFIX = "sysop-zero.";

/** @param {string} key @returns {string|null} the stored value, or null */
export function recall(key) {
  try { return localStorage.getItem(PREFIX + key); } catch { return null; }
}

/** @param {string} key @param {string} value */
export function remember(key, value) {
  try { localStorage.setItem(PREFIX + key, value); } catch { /* not remembered: fine */ }
}

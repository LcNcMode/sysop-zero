// dom.js — tiny helpers for finding elements and writing safe HTML.
// No state, no side effects. Safe to import from any module.

/** Find one element. @param {string} sel CSS selector @returns {HTMLElement|null} */
export const $ = (sel) => document.querySelector(sel);

const ENTITIES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/**
 * Escape text before putting it into an HTML string.
 * Everything from prods.json is written by contributors, so it ALWAYS goes through esc().
 * @param {unknown} s
 * @returns {string}
 */
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ENTITIES[c]);

/**
 * Bytes as a short human size: 26 KiB, 3.1 MiB.
 * @param {number} n
 * @returns {string}
 */
export function humanBytes(n) {
  if (!Number.isFinite(n)) return "";
  if (n < 1024) return `${n} B`;
  const units = ["KiB", "MiB", "GiB"];
  let v = n, u = -1;
  do { v /= 1024; u++; } while (v >= 1024 && u < units.length - 1);
  return `${v < 10 ? v.toFixed(1) : Math.round(v)} ${units[u]}`;
}

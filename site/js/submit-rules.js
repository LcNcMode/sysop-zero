// submit-rules.js — quick checks on the submission answers, before the visitor goes to GitHub.
//
// These mirror the checks in scripts/triage.py (check_common and check_prod). triage.py is the
// judge: it runs on the issue and has the final word. The checks here only save the visitor a
// round trip. If you change a rule in triage.py, change it here too, and the other way round.
// Messages say what is wrong and how to fix it, in one line.

/** @typedef {import("./submit-spec.js").Field} Field */

const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/;
const SPDX = /^[A-Za-z0-9.+-]+$/;
const PLACEHOLDER = /^\s*(tbd|todo|tba|n\/?a|none|-+|\?+|soon|later|coming soon|x+)\s*$/i;

/** Lines of a textarea, without bullets and blanks. @param {string} v */
export const lines = (v) => (v || "").split("\n").map((l) => l.replace(/^[\s\-*]+|[\s\-*]+$/g, "")).filter(Boolean);

/** Handles as a list. @param {string} v */
export const handleList = (v) => (v || "").split(/[,\n]/).map((h) => h.trim()).filter(Boolean);

/**
 * One check per field id. Each gets the field's value and all values, and returns a message
 * or "" when the value is fine. Add a rule by adding an entry here.
 * @type {Record<string, (value: string, all: Record<string, string>) => string>}
 */
const RULES = {
  handles(v) {
    const hs = handleList(v);
    if (hs.some((h) => h.length > 40 || h.includes("@"))) return "Scene handles only: comma-separated, max 40 characters each, no @.";
    if (new Set(hs.map((h) => h.toLowerCase())).size !== hs.length) return "The same handle is listed twice.";
    return "";
  },
  year(v) {
    return /^\d{4}$/.test(v.trim()) && +v >= 1970 && +v <= 2100 ? "" : "A four-digit year, 1970 to 2100, e.g. 2026.";
  },
  license(v) {
    return SPDX.test(v.trim()) ? "" : "An SPDX id like CC-BY-NC-SA-4.0, CC-BY-4.0 or CC0-1.0.";
  },
  models(v, all) {
    const tools = lines(v);
    if ((all.provenance === "ai" || all.provenance === "hybrid") && !tools.length)
      return "Needed for ai and hybrid: one tool per line with what it did, e.g. Claude — code.";
    if (all.provenance === "human" && tools.length)
      return "Provenance says human, but tools are listed. If AI did creative work, go back and pick hybrid or ai. Otherwise empty this field.";
    return "";
  },
  notes(v) {
    return v.trim() && !PLACEHOLDER.test(v) ? "" : "Add a short nfo: who did what, and your greetings. Every handle and the group must be named.";
  },
};

/**
 * Check some fields.
 * @param {Field[]} fields the fields to check (one step, or all of them)
 * @param {Record<string, string>} values every answer so far, by field id
 * @returns {Record<string, string>} field id → message, only for fields with a problem
 */
export function check(fields, values) {
  /** @type {Record<string, string>} */
  const problems = {};
  for (const f of fields) {
    const v = values[f.id] || "";
    if (f.required && !v.trim()) { problems[f.id] = "This one is needed."; continue; }
    if (EMAIL.test(v)) { problems[f.id] = "That looks like an email address. Handles only: remove it."; continue; }
    if (f.type === "dropdown" && v && !f.options.includes(v)) { problems[f.id] = "Pick one from the list."; continue; }
    const rule = RULES[f.id];
    const msg = rule && (v.trim() || f.id === "models" || f.id === "notes") ? rule(v, values) : "";
    if (msg) problems[f.id] = msg;
  }
  return problems;
}

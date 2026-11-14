// submit-main.js — entry point of the upload page (submit.html): a guided version of the
// Prod submission form. It asks the questions here, checks the answers, and then opens
// GitHub's own form with everything filled in. Nothing is sent from this page, and there is
// no server behind it: GitHub stores the files and knows who submitted.
//
//   submit-spec.js   load submit.json (the form, generated from the issue form YAML)
//   submit-form.js   draw the steps
//   submit-rules.js  check the answers (mirror of scripts/triage.py)
//   submit-url.js    build the prefilled GitHub link
//
// State: `values` (answers by field id) and `at` (which step). Both live here and nowhere else.

import { $, esc } from "./dom.js";
import { recall, remember } from "./storage.js";
import { loadSubmitSpec } from "./submit-spec.js";
import { planSteps, stepHtml, handoverHtml, budgetNote } from "./submit-form.js";
import { check } from "./submit-rules.js";
import { initTextSize } from "./textsize.js";

const DRAFT = "submit-draft"; // answers so far, kept on the device so a reload loses nothing

function loadDraft() {
  try { const d = JSON.parse(recall(DRAFT) || "{}"); return d && typeof d === "object" ? d : {}; } catch { return {}; }
}

async function main() {
  initTextSize($("#text-size"));
  const box = $("#wizard");
  const spec = await loadSubmitSpec();
  const steps = planSteps(spec);
  const total = steps.length + 1; // + the hand-over step
  /** @type {Record<string, string>} */
  let values = loadDraft();
  let at = 0;

  const collect = () => {
    for (const el of box.querySelectorAll("[name]")) values[el.name] = el.value;
    remember(DRAFT, JSON.stringify(values));
  };
  const showBudget = () => {
    const note = $("#budget-note");
    if (note) note.textContent = budgetNote(spec, values.category || "");
  };
  const draw = (problems = {}) => {
    box.innerHTML = at < steps.length ? stepHtml(steps[at], at + 1, total, values, problems) : handoverHtml(spec, values, total);
    showBudget();
    // Focus the first problem, or else the heading, so keyboard and screen-reader users land in the new step.
    const first = box.querySelector('[aria-invalid="true"]') || box.querySelector("h2");
    if (first.tagName === "H2") first.tabIndex = -1; // headings need this to take focus
    first.focus();
  };

  box.addEventListener("input", (e) => {
    collect();
    showBudget();
    // The visitor is fixing this field: take its message away until the next check.
    e.target.removeAttribute("aria-invalid");
    const err = e.target.id && document.getElementById(e.target.id + "-err");
    if (err) err.textContent = "";
  });
  box.addEventListener("click", async (e) => {
    const go = e.target.closest("[data-go]");
    const copy = e.target.closest("[data-copy]");
    if (go) {
      collect();
      if (go.dataset.go === "back") { at = Math.max(0, at - 1); draw(); return; }
      const problems = check(steps[at].fields, values);
      if (Object.keys(problems).length) draw(problems); else { at++; draw(); }
    } else if (copy) {
      try { await navigator.clipboard.writeText(values[copy.dataset.copy] || ""); copy.textContent = "copied"; }
      catch { copy.textContent = "copy failed: go back and copy it by hand"; }
    }
  });
  $("#start-over").addEventListener("click", () => { values = {}; remember(DRAFT, "{}"); at = 0; draw(); });

  draw();
}

main().catch((e) => { $("#wizard").innerHTML = `<p class="problem">could not load the form: ${esc(e.message)}</p>`; });

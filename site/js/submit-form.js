// submit-form.js — draws the submission questions, one small step at a time, and the last
// "hand over to GitHub" step. It draws whatever fields submit.json contains; STEPS only says
// which questions share a screen.

import { esc, humanBytes } from "./dom.js";
import { check } from "./submit-rules.js";
import { githubUrl } from "./submit-url.js";

/** @typedef {import("./submit-spec.js").SubmitSpec} SubmitSpec */
/** @typedef {import("./submit-spec.js").Field} Field */

// Which questions go together. A field id that is in the form but not listed here is added
// to the last step automatically, so a new form field can never go missing.
const STEPS = [
  { title: "Who and what", ids: ["title", "group", "handles"] },
  { title: "What kind", ids: ["category", "platform", "year", "party"] },
  { title: "Who made it", ids: ["provenance", "models"] },
  { title: "License and nfo", ids: ["license", "notes"] },
];
// Done on GitHub, not here: the file upload (only GitHub can store the zip) and every
// checkbox (release terms are the visitor's own promise, so nobody ticks them for them).
const ON_GITHUB = (f) => f.id === "link" || f.type === "checkboxes";

/** The steps with their Field objects. @param {SubmitSpec} spec @returns {{title: string, fields: Field[]}[]} */
export function planSteps(spec) {
  const here = spec.fields.filter((f) => !ON_GITHUB(f));
  const placed = new Set(STEPS.flatMap((s) => s.ids));
  const steps = STEPS.map((s) => ({ title: s.title, fields: s.ids.map((id) => here.find((f) => f.id === id)).filter(Boolean) }));
  steps[steps.length - 1].fields.push(...here.filter((f) => !placed.has(f.id)));
  return steps.filter((s) => s.fields.length);
}

/** One question: label, help text, control, and a place for its problem. @param {Field} f */
function fieldHtml(f, value, problem) {
  const id = `q-${esc(f.id)}`;
  const attrs = `id="${id}" name="${esc(f.id)}" aria-describedby="${id}-help ${id}-err"${problem ? ' aria-invalid="true"' : ""}`;
  let control;
  if (f.type === "dropdown") {
    const opts = f.options.map((o) => `<option${o === value ? " selected" : ""}>${esc(o)}</option>`).join("");
    control = `<select ${attrs}><option value="">choose…</option>${opts}</select>`;
  } else if (f.type === "textarea") {
    control = `<textarea ${attrs} rows="6">${esc(value)}</textarea>`;
  } else {
    control = `<input ${attrs} type="text" value="${esc(value)}" autocomplete="off">`;
  }
  return `<div class="field">
      <label for="${id}">${esc(f.label)}${f.required ? "" : ' <span class="dim">(optional)</span>'}</label>
      <p class="help dim" id="${id}-help">${esc(f.description)}</p>
      ${control}
      <p class="problem" id="${id}-err" role="alert">${esc(problem || "")}</p>
    </div>`;
}

/**
 * HTML of one question step.
 * @param {{title: string, fields: Field[]}} step
 * @param {number} n step number, from 1
 * @param {number} total number of steps including the last GitHub step
 * @param {Record<string, string>} values
 * @param {Record<string, string>} problems field id → message
 */
export function stepHtml(step, n, total, values, problems) {
  const budget = step.fields.some((f) => f.id === "category") ? '<p class="dim" id="budget-note"></p>' : "";
  return `<p class="dim">step ${n} of ${total}</p>
    <h2>${esc(step.title)}</h2>
    ${step.fields.map((f) => fieldHtml(f, values[f.id] ?? f.default ?? "", problems[f.id])).join("")}
    ${budget}
    <div class="choices">
      ${n > 1 ? '<button type="button" data-go="back">← back</button>' : ""}
      <button type="button" class="btn-primary" data-go="next">next →</button>
    </div>`;
}

/** "Size budget for intro-4k: 4.0 KiB, measured on the entry file." @param {SubmitSpec} spec @param {string} category */
export function budgetNote(spec, category) {
  const b = spec.budgets[category];
  if (!b) return "";
  return `Size budget for ${category}: ${humanBytes(b.limit_bytes)}, measured on ${b.measure === "entry" ? "the entry file" : "the whole prod folder"}.`;
}

/**
 * HTML of the last step: a summary, and what to do on GitHub.
 * @param {SubmitSpec} spec
 * @param {Record<string, string>} values
 * @param {number} total
 */
export function handoverHtml(spec, values, total) {
  const fields = spec.fields.filter((f) => !ON_GITHUB(f));
  const problems = check(fields, values);
  const summary = fields
    .filter((f) => (values[f.id] || "").trim())
    .map((f) => `<dt>${esc(f.label)}</dt><dd>${esc(values[f.id].trim())}</dd>`)
    .join("");
  const { url, left_out } = githubUrl(spec, values);
  const upload = spec.fields.find((f) => f.id === "link");
  const boxes = spec.fields.filter((f) => f.type === "checkboxes");

  let action;
  if (Object.keys(problems).length) {
    action = `<p class="problem">Something is still missing. Go back and check: ${esc(fields.filter((f) => problems[f.id]).map((f) => f.label).join(", "))}.</p>`;
  } else if (!url) {
    action = '<p class="problem">This copy of the board has no repo address, so there is nowhere to send it.</p>';
  } else {
    const paste = left_out.map((id) => fields.find((f) => f.id === id)).filter(Boolean);
    action = `<ol class="todo">
        <li>Press <b>continue on GitHub</b> (you need a free GitHub account). Your answers should already be in the form: glance over them.</li>
        ${paste.map((f) => `<li><b>${esc(f.label)}</b> was too long for the link. <button type="button" data-copy="${esc(f.id)}">copy it</button> and paste it into that field.</li>`).join("")}
        ${upload ? `<li>Drag a <b>.zip</b> of your prod into <b>${esc(upload.label)}</b>.</li>` : ""}
        ${boxes.map((f) => `<li>Tick the boxes under <b>${esc(f.label)}</b>.</li>`).join("")}
        <li>Press <b>Create</b>. Within a minute Sysop Zero answers in the issue: a checklist, or a pull request with your prod.</li>
      </ol>
      <div class="choices">
        <button type="button" data-go="back">← back</button>
        <a class="btn btn-primary" id="to-github" href="${esc(url)}" target="_blank" rel="noopener noreferrer">continue on GitHub ↗</a>
      </div>`;
  }
  return `<p class="dim">step ${total} of ${total}</p>
    <h2>Check and send</h2>
    <dl class="summary">${summary}</dl>
    ${action}
    ${Object.keys(problems).length || !url ? '<div class="choices"><button type="button" data-go="back">← back</button></div>' : ""}
    <p class="dim">Nothing has been sent yet. Your answers are only kept on this device until you press Create on GitHub.</p>`;
}

// submit-spec.js — loads submit.json: the Prod submission form as data.
//
// The build (scripts/prodcheck.py, submit_spec) generates it from the GitHub issue form
// .github/ISSUE_TEMPLATE/prod-submission.yml. So to add, rename or change a question you edit
// that YAML file, and both GitHub's form and submit.html follow. Never list fields by hand here.
// Like prods.json, submit.json only exists in the built site.

/**
 * @typedef {Object} Field
 * @property {string} id           also the URL parameter that prefills the field on GitHub
 * @property {"input"|"textarea"|"dropdown"|"checkboxes"} type
 * @property {string} label
 * @property {string} description
 * @property {string} default
 * @property {boolean} required
 * @property {string[]} options    choices of a dropdown, or the boxes of a checkboxes field
 */

/**
 * @typedef {Object} SubmitSpec
 * @property {number} version
 * @property {string} template       file name of the issue form
 * @property {string} title          title pattern of the issue form
 * @property {string} new_issue_url  ".../issues/new", or "" when the build knows no repo
 * @property {Field[]} fields
 * @property {Record<string, {limit_bytes: number, measure: "entry"|"folder"}>} budgets
 * @property {string} default_license
 * @property {string} schema         path of the prod.yaml JSON schema
 */

/** @returns {Promise<SubmitSpec>} throws if submit.json can't be read */
export async function loadSubmitSpec() {
  const r = await fetch("submit.json", { cache: "no-cache" });
  if (!r.ok) throw new Error(`submit.json: HTTP ${r.status}`);
  return r.json();
}

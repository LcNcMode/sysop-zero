// submit-url.js — builds the GitHub link that opens the issue form with the answers filled in.
//
// GitHub prefills an issue form field from a URL parameter named after the field's id
// (docs: "Syntax for GitHub's form schema", the `id` key). Attachments and checkboxes can't be
// prefilled, which is right: the visitor attaches the zip and ticks the release terms themselves.

/** @typedef {import("./submit-spec.js").SubmitSpec} SubmitSpec */

// Servers refuse very long addresses. Past this length the long text fields are left out of
// the link and the visitor pastes them instead (see `left_out`).
const MAX_URL = 6000;

// Note on `title`: the form has a field with the id "title" (the prod's title), and GitHub also
// uses the URL parameter `title` for the issue's own title. They are the same parameter, so the
// issue is simply named after the prod. Don't add a "[prod] ... by ..." prefix here: it would
// end up in the prod's title field.

/**
 * @param {SubmitSpec} spec
 * @param {Record<string, string>} values answers by field id
 * @returns {{url: string, left_out: string[]}} the link, and the ids of fields that did not fit
 *          ("" as url when the build knows no repo)
 */
export function githubUrl(spec, values) {
  if (!spec.new_issue_url) return { url: "", left_out: [] };
  const build = (skip) => {
    const q = new URLSearchParams({ template: spec.template });
    for (const f of spec.fields) {
      const v = (values[f.id] || "").trim();
      if (v && f.type !== "checkboxes" && !skip.includes(f.id)) q.set(f.id, v);
    }
    return `${spec.new_issue_url}?${q}`;
  };
  // Leave out the longest textarea first, until the link fits.
  const longest = spec.fields
    .filter((f) => f.type === "textarea" && values[f.id])
    .sort((a, b) => values[b.id].length - values[a.id].length)
    .map((f) => f.id);
  const left_out = [];
  let url = build(left_out);
  while (url.length > MAX_URL && longest.length) {
    left_out.push(longest.shift());
    url = build(left_out);
  }
  return { url, left_out };
}

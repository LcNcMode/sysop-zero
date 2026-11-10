#!/usr/bin/env python3
"""triage — check a Prod submission / Compo entry issue form. Deterministic, no AI.

Reads the issue body as rendered by GitHub issue forms ("### <label>" + value), checks it
against the form, scripts/schema/prod.schema.json and parties/, and writes:
  * a Markdown comment (what is missing and how to fix it, or a draft prod.yaml), and
  * exactly one label: `needs-info` or `ready-for-pr`.

The issue body is untrusted data. Nothing in it is executed or followed, and free-text
fields are only echoed back inside a fenced code block, never as Markdown.

Usage:
  python3 scripts/triage.py --event "$GITHUB_EVENT_PATH" --comment-out c.md --label-out l.txt
  python3 scripts/triage.py --self-test        # run tests/fixtures/issues/ against expected.json
Exit codes: 0 ok · 1 self-test failed · 2 usage error / not a triage issue
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from prodcheck import AI_HINTS, BUDGETS, DEFAULT_LICENSE, SCHEMA, human  # noqa: E402

FORMS = {
    "prod-submission": ROOT / ".github/ISSUE_TEMPLATE/prod-submission.yml",
    "compo-entry": ROOT / ".github/ISSUE_TEMPLATE/compo-entry.yml",
    "prod-update": ROOT / ".github/ISSUE_TEMPLATE/prod-update.yml",
}
MAINTAINER_ROLES = ("OWNER", "MEMBER", "COLLABORATOR")
PROD_SLUG = re.compile(r"\d{4}-[a-z0-9][a-z0-9-]*")
SUBMITTED_IN = re.compile(r"submission issue #(\d+)")
MARK = "<!-- sysop-zero:triage -->"
LABELS = ("needs-info", "ready-for-pr")
NO_RESPONSE = "_No response_"
PLACEHOLDER = re.compile(r"^\s*(tbd|todo|tba|n/?a|none|-+|\?+|soon|later|coming soon|x+)\s*$", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL = re.compile(r"https?://\S+")
SPDX = re.compile(r"^[A-Za-z0-9.+-]+$")
SLUG = re.compile(r"[^a-z0-9]+")
PARTY_SLUG = re.compile(r"\d{4}-[a-z0-9][a-z0-9-]*")
PROD_PATH = re.compile(r"prods/\d{4}-[a-z0-9][a-z0-9-]*")
ISSUE_REF = re.compile(r"#\d+")
ATTACHMENT = re.compile(r"https://github\.com/user-attachments/files/\d+/[A-Za-z0-9._-]+\.zip")
ISSUE_URL = re.compile(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(issues|pull)/\d+/?")


# --- parsing ---------------------------------------------------------------------------

def form_fields(kind: str) -> dict[str, dict]:
    """label -> {id, type, options} from the issue form, so a renamed label can't drift."""
    spec = yaml.safe_load(FORMS[kind].read_text(encoding="utf-8"))
    out = {}
    for item in spec.get("body", []):
        attrs = item.get("attributes", {})
        if item.get("type") == "markdown" or "label" not in attrs:
            continue
        out[attrs["label"].strip()] = {
            "id": item.get("id"), "type": item["type"],
            "options": attrs.get("options", []),
            "required_boxes": [o["label"].strip() for o in attrs.get("options", [])
                               if isinstance(o, dict) and o.get("required")],
            "required": bool(item.get("validations", {}).get("required")),
        }
    return out


def parse_body(body: str, kind: str) -> dict[str, str]:
    """GitHub renders each form field as '### <label>' followed by its value."""
    fields = form_fields(kind)
    values: dict[str, str] = {}
    current = None
    buf: list[str] = []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m and m.group(1) in fields:
            if current:
                values[current] = "\n".join(buf).strip()
            current, buf = fields[m.group(1)]["id"], []
        elif current:
            buf.append(line)
    if current:
        values[current] = "\n".join(buf).strip()
    return {k: ("" if v == NO_RESPONSE else v) for k, v in values.items()}


def checked_labels(value: str) -> set[str]:
    return {m.strip() for m in re.findall(r"^- \[[xX]\]\s+(.+?)\s*$", value or "", re.M)}


def lines(value: str) -> list[str]:
    return [ln.strip(" -*\t") for ln in (value or "").split("\n") if ln.strip(" -*\t")]


# --- checks ----------------------------------------------------------------------------

class Findings:
    def __init__(self):
        self.items: list[tuple[str, bool, str]] = []  # (code, blocking, message)

    def block(self, code: str, msg: str):
        self.items.append((code, True, msg))

    def note(self, code: str, msg: str):
        self.items.append((code, False, msg))

    @property
    def blocking(self):
        return [i for i in self.items if i[1]]

    @property
    def codes(self):
        return sorted({i[0] for i in self.items})


def enum(prop: str) -> list[str]:
    return SCHEMA["properties"][prop]["enum"]


def check_common(v: dict, f: Findings, fields: dict):
    for label, meta in fields.items():
        if meta["required"] and meta["type"] != "checkboxes" and not v.get(meta["id"]):
            f.block(f"missing:{meta['id']}", f"**{label}** is empty. Fill it in and save the issue.")
    for label, meta in fields.items():
        # Required boxes are checked against the form itself, so deleting the section or
        # swapping in a different box can't skip them.
        if meta["type"] == "checkboxes" and meta["required_boxes"]:
            ticked = checked_labels(v.get(meta["id"], ""))
            if not all(req in ticked for req in meta["required_boxes"]):
                f.block(f"terms:{meta['id']}", f"**{label}**: every box in this section is required. If you "
                        "removed or changed it while editing, open a new issue with the form.")
    prov = v.get("provenance", "")
    if prov and prov not in enum_prov():
        f.block("bad:provenance", f"**Provenance** must be one of `{'`, `'.join(enum_prov())}`.")
    models = lines(v.get("models", ""))
    if prov in ("ai", "hybrid") and not models:
        f.block("missing:models", "**AI models and tools used** is required for `ai` and `hybrid`. One per line, "
                "with what each did, e.g. `Claude — code`, `Suno — music`. See docs/PROVENANCE.md.")
    if prov == "human" and models:
        f.block("provenance:human-with-models", "**Provenance** says `human`, but **AI models and tools used** "
                "lists tools. AI is welcome here, it just has to be declared: if AI did any creative work "
                "(code, visuals, music), pick `hybrid` (or `ai`) and say who did what in the notes. If the tools "
                "were only autocomplete, keep `human`, empty the tools field and mention it in the notes. "
                "See docs/PROVENANCE.md.")
    free_text = " ".join(v.get(k, "") for k in ("notes", "models"))
    if prov == "human" and not models and AI_HINTS.search(free_text):  # with models, the block above says it
        f.note("drift:provenance-hints", "Provenance says `human`, but the text mentions AI tools. Double-check the "
               "declaration — CI runs the same check on the nfo later.")
    if any(EMAIL.search(v.get(k, "")) for k in v if k not in ("link",)):
        f.block("personal-data", "Looks like an email address is in the form. **Handles only**: remove it "
                "(edit the issue). Private contact details never go in the repo.")


def enum_prov():
    return SCHEMA["properties"]["provenance"]["properties"]["type"]["enum"]


def check_prod(v: dict, f: Findings) -> dict | None:
    fields = form_fields("prod-submission")
    check_common(v, f, fields)
    handles = [h.strip() for h in re.split(r"[,\n]", v.get("handles", "")) if h.strip()]
    for h in handles:
        if len(h) > 40 or "@" in h:
            f.block("bad:handles", "**Handles**: comma-separated scene handles, max 40 characters each, no `@`.")
            break
    if len(set(h.lower() for h in handles)) != len(handles):
        f.block("bad:handles-dupe", "**Handles**: the same handle is listed twice.")
    for prop, fid in (("category", "category"), ("platform", "platform")):
        if v.get(fid) and v[fid] not in enum(prop):
            f.block(f"bad:{fid}", f"**{prop.title()}** must be one of `{'`, `'.join(enum(prop))}`.")
    year = None
    if v.get("year"):
        if re.fullmatch(r"\d{4}", v["year"].strip()) and 1970 <= int(v["year"]) <= 2100:
            year = int(v["year"])
        else:
            f.block("bad:year", "**Year** must be a four-digit year (1970–2100), e.g. `2026`. Styled as an older "
                    "year? Put that year here and explain it in the notes.")
    lic = v.get("license", "").strip()
    if lic and not SPDX.fullmatch(lic):
        f.block("bad:license", "**License** must be an SPDX id like `CC-BY-NC-SA-4.0`, `CC-BY-4.0` or `CC0-1.0` "
                "(https://spdx.org/licenses/).")
    elif lic and lic != DEFAULT_LICENSE:
        f.note("license-file", f"`{lic}` is not the default license, so the prod folder needs a `LICENSE` file "
               f"that names it (e.g. a line `SPDX-License-Identifier: {lic}`).")
    if not v.get("notes", "").strip() or PLACEHOLDER.match(v.get("notes", "")):
        f.block("missing:notes", "**Notes / nfo** is empty. Add a short nfo: credits per handle (who did "
                "what), and your greetings. It becomes the prod's `nfo.txt`, and CI checks that the group and "
                "every handle are named in it.")
    link = v.get("link", "")
    if link and PLACEHOLDER.match(link):
        f.block("missing:files", "**Where are the files?** still says it's coming. Edit the issue and put them in "
                "that field: drag a `.zip` into it while editing, or paste a link to a fork branch, release or "
                "archive. (A zip in a comment isn't picked up — the check only reads the issue itself.)")
    elif link and not URL.search(link) and "/" not in link:
        f.block("bad:files", "**Where are the files?** needs a link, or a `.zip` dragged into that field while "
                "editing the issue, so a maintainer can fetch them.")
    if link and not ATTACHMENT.search(link) and not f.blocking:
        f.note("intake:manual", "Tip: drag a `.zip` of the prod into **Where are the files?** (edit the issue) "
               "and Sysop Zero opens the pull request for you. Other links need a maintainer to fetch them.")
    cat = v.get("category")
    if cat in BUDGETS:
        b = BUDGETS[cat]
        what = "the entry file" if b["measure"] == "entry" else "the whole prod folder"
        f.note("budget", f"Size budget for `{cat}`: {human(b['limit_bytes'])} ({b['limit_bytes']} bytes), measured on {what}. CI checks it on the PR.")
    party = v.get("party", "").strip()
    if party and PARTY_SLUG.fullmatch(party) and not (ROOT / "parties" / f"{party}.yaml").is_file():
        f.note("party-unknown", f"No `parties/{party}.yaml` yet. Fine for a free-text party name; for a Sysop Zero "
               "compo, check the slug.")
    if v.get("platform") and v["platform"] != "web":
        f.note("not-web", "Non-web prods aren't runnable in the gallery; they're listed with their nfo and files.")
    if f.blocking:
        return None
    draft = {
        "title": v["title"].strip(), "group": v["group"].strip(), "handles": handles,
        "platform": v["platform"], "category": v["category"], "year": year, "license": lic,
        "provenance": {"type": v["provenance"]},
    }
    models = lines(v.get("models", ""))
    if models:
        draft["provenance"]["models"] = models
    draft["provenance"]["notes"] = "TODO: who did what — direction, prompts, hand edits, untouched output."
    if party:
        draft["party"] = party
    errs = sorted(Draft202012Validator(SCHEMA).iter_errors(draft), key=lambda e: list(e.path))
    for e in errs:
        loc = "/".join(str(x) for x in e.path) or "(root)"
        loc = re.sub(r"[^A-Za-z0-9_/()-]", "", loc)  # paths are schema keys/indexes; strip anything else
        f.block("schema", f"The draft `prod.yaml` doesn't pass the schema at `{loc}`. Check that field "
                "against docs/CONTRIBUTING.md; a maintainer can help.")
    return None if errs else draft


def prod_slug(value: str) -> str | None:
    """'2026-26k-intro', 'prods/2026-26k-intro/' or a link ending in it -> '2026-26k-intro'."""
    v = (value or "").strip().rstrip("/").split("/")[-1]
    return v if PROD_SLUG.fullmatch(v) and (ROOT / "prods" / v / "prod.yaml").is_file() else None


def allowed_updaters(slug: str, lookup) -> tuple[set[str], bool]:
    """GitHub logins that may update a prod: its `maintainers`, plus whoever opened the submission
    issue named in the prod.yaml header. Returns (logins, complete) — complete is False when the
    original submitter couldn't be looked up."""
    text = (ROOT / "prods" / slug / "prod.yaml").read_text(encoding="utf-8")
    decl = yaml.safe_load(text) or {}
    logins = {m.lower() for m in decl.get("maintainers") or []}
    m = SUBMITTED_IN.search(text.split("\n\n")[0])
    complete = True
    if m:
        who = lookup(int(m.group(1))) if lookup else None
        if who:
            logins.add(who.lower())
        else:
            complete = False
    return logins, complete


def check_update(v: dict, f: Findings, author: str | None, association: str | None, lookup) -> str | None:
    fields = form_fields("prod-update")
    check_common(v, f, fields)
    slug = None
    if v.get("prod"):
        slug = prod_slug(v["prod"])
        if not slug:
            f.block("prod-unknown", "**Prod** must be the folder name of a released prod, like `2026-26k-intro` "
                    "(look it up under `prods/` in the repo, or in the gallery link).")
    if v.get("changes") and PLACEHOLDER.match(v["changes"]):
        f.block("missing:changes", "**What changed?** still says TBD. A line for the changelog is enough, "
                "e.g. 'Starts on touch screens now'.")
    link = v.get("link", "")
    if link and not ATTACHMENT.search(link):
        f.block("missing:zip", "**New files** needs a `.zip` of the whole new version: edit the issue and drag "
                "the zip into that field. Links to other sites can't be picked up.")
    if slug and author is not None and (association or "").upper() not in MAINTAINER_ROLES:
        logins, complete = allowed_updaters(slug, lookup)
        if author.lower() not in logins:
            msg = ("Only the creator who submitted this prod, or one of its listed maintainers, can update it. "
                   "If that's you, open the update from the same GitHub account; otherwise ask them, or a "
                   "maintainer, to do it.")
            if not complete:
                msg = "I couldn't confirm that you submitted this prod. A maintainer will check it by hand."
            f.block("not-allowed", msg)
    return slug


def check_compo(v: dict, f: Findings):
    fields = form_fields("compo-entry")
    check_common(v, f, fields)
    party = v.get("party", "").strip()
    if party and not PARTY_SLUG.fullmatch(party):
        f.block("bad:party", "**Party** must be a party slug from `parties/`, like `2027-sysop-zero-party` "
                "(lowercase, digits and dashes).")
    elif party and not (ROOT / "parties" / f"{party}.yaml").is_file():
        f.block("party-unknown", "That party isn't in `parties/` yet. Use the slug of an announced party "
                "(the file name without `.yaml`).")
    prod = v.get("prod", "").strip().rstrip("/")
    if prod:
        if PROD_PATH.fullmatch(prod):
            if not (ROOT / prod / "prod.yaml").is_file():
                f.block("prod-unknown", "**Prod** points at a folder that isn't in the repo yet. Link the "
                        "submission issue or PR instead, or wait until it's merged.")
        elif not (ISSUE_REF.fullmatch(prod) or ISSUE_URL.fullmatch(prod)):
            f.block("bad:prod", "**Prod** must be a repo path like `prods/2027-my-intro/`, or a link to your "
                    "submission issue or PR (`#12` or its full URL).")
    compo = v.get("compo")
    if compo and compo not in enum("category"):
        f.block("bad:compo", f"**Compo** must be one of `{'`, `'.join(enum('category'))}`.")


# --- output ----------------------------------------------------------------------------

def fence(text: str, lang: str = "") -> str:
    """Fence untrusted text so it can't break out: the fence is longer than any run inside."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{lang}\n{text.rstrip()}\n{ticks}"


def slugify(title: str) -> str:
    return SLUG.sub("-", title.lower()).strip("-")[:40].strip("-") or "my-prod"


def render(kind: str, f: Findings, draft: dict | None, slug: str | None = None) -> tuple[str, str]:
    label = "needs-info" if f.blocking else "ready-for-pr"
    what = {"prod-submission": "prod", "prod-update": "prod update"}.get(kind, "compo entry")
    out = [MARK, f"### 📡 Sysop Zero — {what} check", ""]
    if f.blocking:
        out += ["Thanks for the upload! A few things before this can go in:", ""]
        out += [f"- [ ] {m}" for _, b, m in f.items if b]
        out += ["", "Edit the issue (**⋯ → Edit**) and I'll check it again automatically."]
    else:
        out += ["Looks good — everything the form needs is there. ✅", ""]
        if kind == "prod-update" and slug:
            out += [f"Sysop Zero opens a pull request that replaces `prods/{slug}/` with your zip."]
        if draft:
            folder = f"prods/{draft['year']}-{slugify(draft['title'])}/"
            out += [f"Draft `{folder}prod.yaml` for the maintainer (the PR will use this):", "",
                    fence(yaml.safe_dump(draft, sort_keys=False, allow_unicode=True), "yaml"), "",
                    "Still needed in the folder: `nfo.txt` crediting the group and every handle, and the prod "
                    "itself (`index.html` for web prods)."]
    notes = [m for _, b, m in f.items if not b]
    if notes:
        out += ["", "<details><summary>Notes (not blocking)</summary>", ""] + [f"- {m}" for m in notes] + ["", "</details>"]
    out += ["", "_This check is a script, not an AI (`scripts/triage.py`). A maintainer takes it from here._",
            "", "— Sysop Zero"]
    return "\n".join(out) + "\n", label


def triage(kind: str, body: str, author: str | None = None, association: str | None = None,
           lookup=None) -> tuple[str, str, Findings]:
    """author=None skips the who-may-update check (intake relies on the triage job having run it)."""
    f = Findings()
    slug = None
    values = parse_body(body, kind)
    if not values:
        f.block("unparsed", "I couldn't read the form fields. Please open a new issue with the form "
                "(**New issue → Prod submission**) instead of a blank issue.")
        draft = None
    elif kind == "prod-submission":
        draft = check_prod(values, f)
    elif kind == "prod-update":
        slug = check_update(values, f, author, association, lookup)
        draft = None
    else:
        check_compo(values, f)
        draft = None
    comment, label = render(kind, f, draft, slug)
    assert label in LABELS
    return comment, label, f


# --- CLI -------------------------------------------------------------------------------

def self_test() -> int:
    base = ROOT / "tests/fixtures/issues"
    expected = json.loads((base / "expected.json").read_text(encoding="utf-8"))
    failed = 0
    for name, exp in sorted(expected.items()):
        stub = {int(k): v for k, v in exp.get("submitters", {}).items()}
        comment, label, f = triage(exp["kind"], (base / name).read_text(encoding="utf-8"),
                                   exp.get("author"), exp.get("association"), stub.get)
        problems = []
        if label != exp["label"]:
            problems.append(f"label {label} != {exp['label']}")
        if f.codes != sorted(exp["codes"]):
            problems.append(f"codes {f.codes} != {sorted(exp['codes'])}")
        for needle in exp.get("comment_must_not_contain", []):
            outside = re.sub(r"(`{3,})[\s\S]*?\1", "", comment)  # mentions inside code fences don't notify
            if needle in outside:
                problems.append(f"comment leaks {needle!r} outside a code fence")
        status = "ok" if not problems else "FAIL: " + "; ".join(problems)
        print(f"{'✅' if not problems else '❌'} {name}: {status}")
        failed += bool(problems)
    print(f"triage self-test: {len(expected) - failed}/{len(expected)} passed")
    return 1 if failed else 0


def github_issue_author(number: int) -> str | None:
    """Login of whoever opened issue <number> in this repo (REST, built-in token). None if unknown."""
    import os
    import urllib.request
    repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        return None
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues/{number}",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "User-Agent": "sysop-zero-triage"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return (json.loads(r.read()).get("user") or {}).get("login")
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", help="path to the GitHub event JSON (issues event)")
    ap.add_argument("--comment-out", help="write the comment Markdown here")
    ap.add_argument("--label-out", help="write the single label here")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not (a.event and a.comment_out and a.label_out):
        ap.error("--event, --comment-out and --label-out are required")
    ev = json.loads(Path(a.event).read_text(encoding="utf-8"))
    issue = ev.get("issue") or {}
    labels = {lbl.get("name") for lbl in issue.get("labels", [])}
    kind = next((k for k in FORMS if k in labels), None)
    if not kind:
        print("not a prod-submission / prod-update / compo-entry issue; nothing to do", file=sys.stderr)
        return 2
    comment, label, f = triage(kind, issue.get("body") or "", (issue.get("user") or {}).get("login", ""),
                               issue.get("author_association", ""), github_issue_author)
    Path(a.comment_out).write_text(comment, encoding="utf-8")
    Path(a.label_out).write_text(label + "\n", encoding="utf-8")
    print(f"{kind}: {label} · findings: {', '.join(f.codes) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

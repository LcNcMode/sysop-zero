#!/usr/bin/env python3
"""prodcheck — validate prods, observe them, report drift, and build the gallery.

Declared = prod.yaml (human-owned). Observed = what this script measures.
Any mismatch between the two is drift and is reported.

Exit codes:
  0  no errors (drift may still be reported as warnings)
  1  at least one error (schema invalid, missing entry, size over budget, ...)
  2  usage / internal failure
With --expect-findings the meaning is inverted for self-tests: exit 0 only if
every prod produced at least one error or drift finding.

Usage:
  python3 scripts/prodcheck.py [--prods prods] [--report report.md]
                               [--json report.json] [--site-out _site]
                               [--expect-findings]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "scripts/schema/prod.schema.json").read_text())
BUDGETS = {k: v for k, v in json.loads((ROOT / "scripts/categories.json").read_text()).items() if not k.startswith("_")}
DEFAULT_LICENSE = "CC-BY-NC-SA-4.0"
AI_HINTS = re.compile(r"\b(claude|chatgpt|gpt-?\d|openai|gemini|suno|udio|midjourney|stable diffusion|dall-?e|copilot|llama)\b", re.I)
FOLDER_RE = re.compile(r"^(\d{4})-[a-z0-9][a-z0-9-]*$")

# The gallery serves prods from the same origin as the gallery (and, on <owner>.github.io, as every
# other Pages site of the owner). They are only safe inside the gallery's sandboxed iframe, so:
#  - file types that run scripts when opened directly, and that the guard below cannot cover, are
#    refused (SVG only when it carries script);
#  - every HTML file gets a guard at build time (see build_site).
BLOCKED_EXT = {".xhtml", ".xht", ".xml", ".xsl", ".xslt", ".shtml", ".svgz", ".mht", ".mhtml"}
SVG_SCRIPT = re.compile(rb"<script|\bon[a-z]+\s*=|javascript:|<foreignObject", re.I)
# Runs before any prod code. Inside the gallery's sandbox the document has an opaque origin
# ("null"); anywhere else (opened directly, or framed by another site) the guard stops the HTML
# parser, so no prod script runs, and sends the visitor to the sandboxed player instead.
GUARD = ('<script>/* sysop-zero: run only inside the gallery sandbox */'
         'if(self.origin!=="null"){{document.write("<plaintext hidden>");'
         'location.replace({target})}}</script>')
DOCTYPE = re.compile(rb"^(\xef\xbb\xbf)?\s*<!doctype[^>]*>", re.I)


class _DateSafeLoader(yaml.SafeLoader):
    """SafeLoader that keeps dates as strings so JSON Schema sees them as text."""


_DateSafeLoader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def _is_utf8(raw: bytes) -> bool:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return False
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def folder_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def check_prod(folder: Path) -> dict:
    res = {"slug": folder.name, "path": folder.as_posix(), "errors": [], "drift": [], "observed": {}, "declared": None}
    err, drift, obs = res["errors"].append, res["drift"].append, res["observed"]

    if folder.is_symlink():
        err("the prod folder is a symlink; prods must contain real files only")
        return res
    yml = folder / "prod.yaml"
    if not yml.is_file():
        err("missing prod.yaml")
        return res
    try:
        decl = yaml.load(yml.read_text(encoding="utf-8"), Loader=_DateSafeLoader)
    except yaml.YAMLError as e:
        err(f"prod.yaml is not valid YAML: {e}")
        return res
    res["declared"] = decl
    if not isinstance(decl, dict):
        err("prod.yaml must be a mapping")
        return res
    for e in sorted(Draft202012Validator(SCHEMA).iter_errors(decl), key=lambda e: list(e.path)):
        loc = "/".join(str(x) for x in e.path) or "(root)"
        err(f"schema: `{loc}`: {e.message}")
    if res["errors"]:
        return res

    # --- files that would be unsafe to publish ------------------------------
    for f in sorted(folder.rglob("*")):
        rel = f.relative_to(folder).as_posix()
        if f.is_symlink():
            err(f"`{rel}` is a symlink; prods must contain real files only")
        elif f.is_file() and f.suffix.lower() in BLOCKED_EXT:
            err(f"`{rel}`: {f.suffix.lower()} files are not allowed in a prod (they can run scripts outside the gallery sandbox)")
        elif f.is_file() and f.suffix.lower() in (".html", ".htm") and not _is_utf8(f.read_bytes()):
            # A UTF-16 byte-order mark beats the server's charset, which would garble the guard.
            err(f"`{rel}`: HTML must be UTF-8 (no UTF-16 byte-order mark)")
        elif f.is_file() and f.suffix.lower() == ".svg" and SVG_SCRIPT.search(f.read_bytes()):
            err(f"`{rel}`: SVG with script, event handlers or foreignObject is not allowed (use a script-free SVG, or draw it from your HTML)")
    if res["errors"]:
        return res

    # --- observe -----------------------------------------------------------
    m = FOLDER_RE.match(folder.name)
    obs["folder_year"] = int(m.group(1)) if m else None
    entry_rel = decl.get("entry", "index.html")
    entry = (folder / entry_rel).resolve()
    if folder.resolve() not in entry.parents:
        err(f"entry `{entry_rel}` points outside the prod folder")
        return res
    obs["entry_exists"] = entry.is_file()
    obs["entry_bytes"] = entry.stat().st_size if entry.is_file() else None
    obs["folder_bytes"] = folder_size(folder)
    obs["files"] = sum(1 for f in folder.rglob("*") if f.is_file())
    obs["has_nfo"] = (folder / "nfo.txt").is_file()
    nfo = (folder / "nfo.txt").read_text(encoding="utf-8", errors="replace") if obs["has_nfo"] else ""
    lic_files = sorted(p.name for p in folder.glob("LICENSE*"))
    obs["license_files"] = lic_files
    html_title = None
    if entry.is_file() and entry.suffix.lower() in (".html", ".htm"):
        t = re.search(r"<title>(.*?)</title>", entry.read_text(encoding="utf-8", errors="replace"), re.I | re.S)
        html_title = t.group(1).strip() if t else None
    obs["html_title"] = html_title
    ai_hits = set()
    for f in [folder / "nfo.txt", *folder.glob("*.md")]:
        if f.is_file():
            ai_hits |= {h.lower() for h in AI_HINTS.findall(f.read_text(encoding="utf-8", errors="replace"))}
    obs["ai_mentions"] = sorted(ai_hits)

    # --- compare declared vs observed -------------------------------------
    if m is None:
        drift(f"folder name `{folder.name}` does not follow `YYYY-slug`")
    elif obs["folder_year"] != decl["year"]:
        drift(f"year: declared {decl['year']}, folder says {obs['folder_year']}")

    if not obs["entry_exists"]:
        err(f"entry: declared `{entry_rel}`, file not found")
    elif decl["platform"] == "web" and entry.suffix.lower() not in (".html", ".htm"):
        drift(f"platform: declared web, but entry `{entry_rel}` is not an HTML file")

    budget = BUDGETS[decl["category"]]
    measured = obs["entry_bytes"] if budget["measure"] == "entry" else obs["folder_bytes"]
    obs["measured_bytes"], obs["budget_bytes"], obs["measure"] = measured, budget["limit_bytes"], budget["measure"]
    if measured is not None and measured > budget["limit_bytes"]:
        err(f"size: {decl['category']} budget is {human(budget['limit_bytes'])} ({budget['measure']}), observed {human(measured)} ({measured} bytes)")

    if decl["platform"] == "web" and html_title is not None and html_title != decl["title"]:
        drift(f"title: declared “{decl['title']}”, entry <title> is “{html_title}”")
    if decl["platform"] == "web" and obs["entry_exists"] and html_title is None and entry.suffix.lower() in (".html", ".htm"):
        drift("title: entry HTML has no <title>")

    if decl["license"] != DEFAULT_LICENSE and not lic_files:
        drift(f"license: declared {decl['license']} (not the repo default), but no LICENSE file in the prod folder")
    for lf in lic_files:
        txt = (folder / lf).read_text(encoding="utf-8", errors="replace")
        if decl["license"] not in txt and decl["license"].replace("-", " ") not in txt:
            spdx_line = next((line for line in txt.splitlines() if "SPDX-License-Identifier" in line), None)
            if not spdx_line or decl["license"] not in spdx_line:
                drift(f"license: declared {decl['license']}, `{lf}` does not mention it (add `SPDX-License-Identifier: {decl['license']}`)")

    prov = decl["provenance"]
    if prov["type"] == "human" and prov.get("models"):
        drift(f"provenance: declared human, but models are listed: {', '.join(prov['models'])}")
    if prov["type"] == "human" and ai_hits:
        drift(f"provenance: declared human, but the prod's docs mention AI tools: {', '.join(sorted(ai_hits))}")

    if not obs["has_nfo"]:
        drift("nfo.txt: missing")
    else:
        for h in decl["handles"]:
            if h.lower() not in nfo.lower():
                drift(f"handles: `{h}` is declared but not credited in nfo.txt")
        if decl["group"].lower() not in nfo.lower():
            drift(f"group: `{decl['group']}` is declared but not named in nfo.txt")
    return res


def render_report(results: list[dict], title: str) -> str:
    n_err = sum(len(r["errors"]) for r in results)
    n_drift = sum(len(r["drift"]) for r in results)
    status = "❌ errors" if n_err else ("⚠️ drift" if n_drift else "✅ clean")
    out = [f"### {title}: {status}", "",
           f"{len(results)} prod(s) · {n_err} error(s) · {n_drift} drift finding(s)", ""]
    for r in results:
        d = r["declared"] if isinstance(r["declared"], dict) else {}
        o = r["observed"]
        icon = "❌" if r["errors"] else ("⚠️" if r["drift"] else "✅")
        out.append(f"#### {icon} `{r['path']}`")
        if d and o:
            size = f"{human(o['measured_bytes'])} / {human(o['budget_bytes'])} ({o['measure']})" if o.get("measured_bytes") is not None else "n/a"
            out += ["", "| field | declared | observed |", "|---|---|---|",
                    f"| title | {d.get('title','')} | {o.get('html_title') or '—'} |",
                    f"| year | {d.get('year','')} | folder: {o.get('folder_year') or '—'} |",
                    f"| category / size | {d.get('category','')} | {size} |",
                    f"| entry | {d.get('entry','index.html')} | {'found' if o.get('entry_exists') else 'missing'} |",
                    f"| license | {d.get('license','')} | files: {', '.join(o.get('license_files') or []) or 'repo default'} |",
                    f"| provenance | {d.get('provenance',{}).get('type','')} | AI tools mentioned: {', '.join(o.get('ai_mentions') or []) or 'none'} |",
                    ""]
        for e in r["errors"]:
            out.append(f"- ❌ **error** — {e}")
        for x in r["drift"]:
            out.append(f"- ⚠️ **drift** — {x}")
        if not r["errors"] and not r["drift"]:
            out.append("- declared matches observed")
        out.append("")
    return "\n".join(out)


def guard_html(dst: Path, out: Path, slug: str) -> None:
    """Prepend GUARD to every HTML file of a published prod (after the doctype, so the prod keeps
    standards mode). Size budgets are measured on the source, so the guard costs a prod nothing."""
    for f in sorted(dst.rglob("*")):
        if not (f.is_file() and f.suffix.lower() in (".html", ".htm")):
            continue
        up = "../" * (len(f.relative_to(out).parts) - 1)
        target = json.dumps(up + "play.html#/" + urllib.parse.quote(slug, safe=""))  # a safe JS string
        guard = GUARD.format(target=target).encode()
        raw = f.read_bytes()
        m = DOCTYPE.match(raw)
        cut = m.end() if m else (3 if raw.startswith(b"\xef\xbb\xbf") else 0)
        f.write_bytes(raw[:cut] + guard + raw[cut:])


def build_site(results: list[dict], out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "site", out)
    cfg = json.loads((ROOT / "site/config.json").read_text())
    if not cfg.get("repo_url") and os.environ.get("GITHUB_REPOSITORY"):
        # Portability: derive the repo link at build time instead of hardcoding it.
        cfg["repo_url"] = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}"
    (out / "config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    index = []
    for r in results:
        if r["errors"]:
            continue
        d, src = r["declared"], Path(r["path"])
        dst = out / "prods" / r["slug"]
        shutil.copytree(src, dst, symlinks=True)  # check_prod refuses symlinks; never follow one
        guard_html(dst, out, r["slug"])
        index.append({
            "slug": r["slug"], **{k: d.get(k) for k in ("title", "group", "handles", "platform", "category", "year", "released", "license", "party", "tags")},
            "provenance": d["provenance"], "entry": d.get("entry", "index.html"),
            "runnable": d["platform"] == "web",
            "has_nfo": r["observed"]["has_nfo"], "bytes": r["observed"]["measured_bytes"], "drift": r["drift"],
        })
    index.sort(key=lambda p: (str(p.get("released") or p["year"])), reverse=True)
    (out / "prods.json").write_text(json.dumps({"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "prods": index}, indent=2, ensure_ascii=False))
    if cfg.get("custom_domain"):
        (out / "CNAME").write_text(cfg["custom_domain"].strip() + "\n")
    (out / ".nojekyll").write_text("")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prods", default="prods", help="folder that holds one sub-folder per prod")
    ap.add_argument("--title", default="Sysop Zero prod check")
    ap.add_argument("--report", help="write a Markdown report here")
    ap.add_argument("--json", help="write a JSON report here")
    ap.add_argument("--site-out", help="build the gallery into this folder")
    ap.add_argument("--expect-findings", action="store_true", help="self-test: succeed only if every prod has findings")
    a = ap.parse_args()

    base = Path(a.prods)
    if not base.is_dir():
        print(f"no such folder: {base}", file=sys.stderr)
        return 2
    folders = sorted(p for p in base.iterdir() if p.is_dir())
    results = [check_prod(f) for f in folders]
    md = render_report(results, a.title)
    print(md)
    if a.report:
        Path(a.report).write_text(md + "\n", encoding="utf-8")
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    for r in results:  # GitHub annotations
        for e in r["errors"]:
            print(f"::error file={r['path']}/prod.yaml::{e}")
        for x in r["drift"]:
            print(f"::warning file={r['path']}/prod.yaml::drift: {x}")
    if a.site_out:
        build_site(results, Path(a.site_out))
    if a.expect_findings:
        silent = [r["slug"] for r in results if not r["errors"] and not r["drift"]]
        if silent or not results:
            print(f"self-test failed: no findings for {silent or 'any prod'}", file=sys.stderr)
            return 1
        return 0
    return 1 if any(r["errors"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())

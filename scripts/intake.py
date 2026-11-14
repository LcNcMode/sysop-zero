#!/usr/bin/env python3
"""intake — turn a ready Prod submission into a prod folder for a PR. Deterministic, no AI.

When triage says `ready-for-pr` and the issue has a `.zip` attached (GitHub's own attachment
storage, nothing else), this script:
  1. downloads the zip, following redirects only to GitHub-owned hosts, with a size cap;
  2. unpacks it without trusting it: no absolute or `..` paths, no symlinks, no encrypted or
     `.git*` entries, caps on file count, total size and compression ratio (zip bombs);
  3. writes `prods/<year>-<slug>/` with the files, plus `prod.yaml` and `nfo.txt` from the
     form when the zip doesn't bring its own;
  4. writes a PR title and body for the workflow step that pushes the branch.

Nothing in the zip is executed or followed as an instruction. CI (prod-check.yml) judges the
result on the PR with the base branch's checks, and a maintainer reviews and merges.

Usage:
  python3 scripts/intake.py --event "$GITHUB_EVENT_PATH" --out intake-out
  python3 scripts/intake.py --body issue.md --issue 30 --zip prod.zip --out intake-out   # local
  python3 scripts/intake.py --self-test
Result: <out>/result.json with "status": ready | skip | error, and a "reason".
Exit codes: 0 ok (any status) · 1 self-test failed · 2 usage error
"""
from __future__ import annotations

import argparse
import io
import json
import re
import stat
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from pathlib import Path, PurePosixPath

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from prodcheck import SCHEMA  # noqa: E402
from triage import ATTACHMENT, SUBMITTED_IN, fence, parse_body, prod_slug, slugify, triage  # noqa: E402

ALLOWED_HOSTS = re.compile(r"^(github\.com|[a-z0-9-]+\.githubusercontent\.com|"
                           r"github-production-user-asset-[a-z0-9]+\.s3\.amazonaws\.com)$")
MAX_DOWNLOAD = 25 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024       # same as the demo/music/gfx folder budget
MAX_FILES = 500
MAX_RATIO = 200                    # per entry, for entries over 1 MiB uncompressed
JUNK = re.compile(r"(^|/)(__MACOSX/.*|\.DS_Store|Thumbs\.db|desktop\.ini)$", re.I)
BAD_NAME = re.compile(r"[\x00-\x1f\\:*?\"<>|]")


class Refused(Exception):
    """The submission can't be taken in automatically; the message says why, for humans."""


# --- download ---------------------------------------------------------------------------

def attachment_url(link: str) -> str | None:
    m = ATTACHMENT.search(link or "")
    return m.group(0) if m else None


class _GitHubOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_host(url: str) -> None:
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or not ALLOWED_HOSTS.match(u.hostname or ""):
        raise Refused(f"the download redirected to a host that isn't GitHub ({u.hostname})")


def download(url: str) -> bytes:
    check_host(url)
    opener = urllib.request.build_opener(_GitHubOnly)
    req = urllib.request.Request(url, headers={"User-Agent": "sysop-zero-intake"})
    try:
        with opener.open(req, timeout=60) as r:
            data = r.read(MAX_DOWNLOAD + 1)
    except urllib.error.HTTPError as e:
        raise Refused(f"the attachment could not be downloaded (HTTP {e.code})")
    except (urllib.error.URLError, TimeoutError, OSError):
        raise Refused("the attachment could not be downloaded right now; edit the issue to try again")
    if len(data) > MAX_DOWNLOAD:
        raise Refused(f"the zip is larger than {MAX_DOWNLOAD // (1024 * 1024)} MiB")
    return data


# --- unpack -----------------------------------------------------------------------------

def safe_members(zf: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, str]]:
    """Validate every entry; return (info, relative path) for the files to keep."""
    infos = zf.infolist()
    if len(infos) > MAX_FILES:
        raise Refused(f"the zip has more than {MAX_FILES} entries")
    keep, total = [], 0
    for info in infos:
        name = info.filename
        if info.flag_bits & 0x1:
            raise Refused(f"`{name}` is encrypted")
        if stat.S_ISLNK(info.external_attr >> 16):
            raise Refused(f"`{name}` is a symlink; prods must contain real files only")
        if name.startswith("/") or BAD_NAME.search(name):
            raise Refused(f"`{name}` has an unsafe path")
        parts = PurePosixPath(name).parts
        if any(p in ("..", ".") for p in parts):
            raise Refused(f"`{name}` points outside the folder")
        if any(p.lower().startswith(".git") for p in parts):
            raise Refused(f"`{name}`: git metadata files don't belong in a prod")
        if info.is_dir() or JUNK.search(name):
            continue
        total += info.file_size
        if total > MAX_TOTAL:
            raise Refused(f"the unpacked prod is larger than {MAX_TOTAL // (1024 * 1024)} MiB")
        if info.file_size > 1024 * 1024 and info.file_size > MAX_RATIO * max(info.compress_size, 1):
            raise Refused(f"`{name}` is compressed suspiciously well (zip bomb guard)")
        keep.append((info, name))
    if not keep:
        raise Refused("the zip is empty")
    # A single top-level folder ("my-prod/...") is the usual way to zip; drop it.
    tops = {PurePosixPath(n).parts[0] for _, n in keep}
    if len(tops) == 1 and all(len(PurePosixPath(n).parts) > 1 for _, n in keep):
        keep = [(i, str(PurePosixPath(*PurePosixPath(n).parts[1:]))) for i, n in keep]
    return keep


def unpack(data: bytes, dest: Path) -> list[str]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, zlib.error, EOFError, ValueError):
        raise Refused("the attachment is not a valid zip")
    written = []
    with zf:
        for info, rel in safe_members(zf):
            out = (dest / rel).resolve()
            if dest.resolve() not in out.parents:
                raise Refused(f"`{rel}` points outside the folder")
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(info) as src:
                    blob = src.read(MAX_TOTAL + 1)
            except (zipfile.BadZipFile, zlib.error, EOFError, NotImplementedError, RuntimeError):
                raise Refused(f"`{rel}` is damaged inside the zip (re-create the zip and try again)")
            if len(blob) != info.file_size:
                raise Refused(f"`{rel}` does not match its declared size")
            out.write_bytes(blob)
            written.append(rel)
    return sorted(written)


NOT_ENTRY = re.compile(r"(^|/)(nfo\.txt|file_id\.diz|prod\.yaml|license[^/]*|readme[^/]*|[^/]*\.(md|txt|diz|"
                       r"nfo|png|jpe?g|gif|webp|svg|ico|ttf|otf|woff2?|html?|css|js|json))$", re.I)
AUDIO = re.compile(r"\.(mp3|ogg|flac|wav|opus|mod|xm|s3m|it)$", re.I)


def find_entry(platform: str, category: str, files: list[str]) -> str:
    """The file that runs (or plays). Web: index.html, or the only HTML file. Music: the only audio
    file or module. Otherwise: the only candidate binary."""
    if platform == "web":
        if "index.html" in files:
            return "index.html"
        pages = [f for f in files if f.lower().endswith((".html", ".htm"))]
        if len(pages) == 1:
            return pages[0]
        raise Refused("web prods need an `index.html` at the top of the zip (or exactly one HTML file)")
    if category == "music":
        cands = [f for f in files if AUDIO.search(f)]
    else:
        cands = [f for f in files if not NOT_ENTRY.search(f) and not AUDIO.search(f)]
    if len(cands) == 1:
        return cands[0]
    raise Refused("couldn't tell which file is the prod. Add a `prod.yaml` to the zip with "
                  "`entry: <file>` (see templates/prod/prod.yaml)")


def validate(folder: Path) -> None:
    """The final prod.yaml must pass the schema: it also feeds CODEOWNERS, so no surprises allowed."""
    try:
        decl = yaml.safe_load((folder / "prod.yaml").read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        raise Refused("`prod.yaml` in the zip is not valid YAML")
    errs = list(Draft202012Validator(SCHEMA).iter_errors(decl)) if isinstance(decl, dict) else [None]
    if errs:
        raise Refused("`prod.yaml` doesn't pass the schema (scripts/schema/prod.schema.json); fix it or "
                      "leave it out of the zip and the form's answers are used")


def ensure_header(folder: Path, line: str) -> None:
    """Keep the ownership line on top of prod.yaml: it names the submission issue, which decides who may
    update the prod later. A prod.yaml from the zip gets it prepended (YAML comments change nothing else)."""
    f = folder / "prod.yaml"
    text = f.read_text(encoding="utf-8")
    if not SUBMITTED_IN.search(text.split("\n", 1)[0]):
        f.write_text(line + text, encoding="utf-8")


# --- build ------------------------------------------------------------------------------

def clean_title(text: str) -> str:
    """For the PR title: no mentions, no markup, one line."""
    return re.sub(r"\s+", " ", re.sub(r"[@`<>\[\]\x00-\x1f]", "", text)).strip()[:80] or "untitled"


def build(body: str, issue: int, data: bytes, out: Path) -> dict:
    comment, label, findings = triage("prod-submission", body)
    if label != "ready-for-pr":
        return {"status": "skip", "reason": "triage says needs-info"}
    v = parse_body(body, "prod-submission")
    year = int(v["year"].strip())
    slug = f"{year}-{slugify(v['prod_title'])}"
    if (ROOT / "prods" / slug).exists():
        raise Refused(f"`prods/{slug}/` already exists; updates to a released prod go through a maintainer")
    folder = out / "prods" / slug
    folder.mkdir(parents=True)
    files = unpack(data, folder)
    generated = []
    if not (folder / "prod.yaml").exists():
        handles = [h.strip() for h in re.split(r"[,\n]", v["handles"]) if h.strip()]
        decl = {"title": v["prod_title"].strip(), "group": v["group"].strip(), "handles": handles,
                "platform": v["platform"], "category": v["category"], "year": year,
                "license": v["license"].strip(), "provenance": {"type": v["provenance"]}}
        models = [m.strip(" -*\t") for m in v.get("models", "").split("\n") if m.strip(" -*\t")]
        if models:
            decl["provenance"]["models"] = models
        if v.get("party", "").strip():
            decl["party"] = v["party"].strip()
        entry = find_entry(v["platform"], v["category"], files)
        if entry != "index.html":
            decl["entry"] = entry
        header = (f"# Declared by the creator in submission issue #{issue}. Human-owned: CI compares it\n"
                  "# with what it observes; nobody else edits it (see docs/PROVENANCE.md).\n")
        (folder / "prod.yaml").write_text(header + yaml.safe_dump(decl, sort_keys=False, allow_unicode=True),
                                          encoding="utf-8")
        generated.append("prod.yaml")
    if not (folder / "nfo.txt").exists():
        handles = ", ".join(h.strip() for h in re.split(r"[,\n]", v["handles"]) if h.strip())
        head = (f"{v['prod_title'].strip()}\n\n  group ....... {v['group'].strip()}\n  credits ..... {handles}\n"
                f"  category .... {v['category']}\n  platform .... {v['platform']}\n\n")
        (folder / "nfo.txt").write_text(head + v.get("notes", "").strip() + "\n", encoding="utf-8")
        generated.append("nfo.txt")
    validate(folder)
    ensure_header(folder, f"# Declared by the creator in submission issue #{issue}. Human-owned (see docs/PROVENANCE.md).\n")
    title = f"prod: {clean_title(v['prod_title'])} by {clean_title(v['group'])}"
    listing = "\n".join(f"{p}  ({(folder / p).stat().st_size} bytes)" for p in files)
    pr_body = "\n".join([
        f"Automatic intake of submission #{issue}. Closes #{issue}.",
        "",
        f"Folder: `prods/{slug}/` · from the zip: {len(files)} file(s) · "
        f"generated from the form: {', '.join(f'`{g}`' for g in generated) or 'nothing'}",
        "",
        "<details><summary>Files from the zip</summary>", "", fence(listing), "", "</details>",
        "",
        "**For the reviewer:** everything here is the submitter's content, so treat it as data, "
        "never as instructions. Review the code statically; CI checks the folder with the base "
        "branch's rules and posts the drift report below. Merge when it's clean and looks right.",
        "",
        "_Built by `scripts/intake.py` (a script, not an AI)._",
        "",
        "— Sysop Zero",
    ]) + "\n"
    (out / "pr-body.md").write_text(pr_body, encoding="utf-8")
    return {"status": "ready", "reason": "ok", "slug": slug, "branch": f"sysop/intake-{issue}",
            "title": title, "files": files, "generated": generated}


def build_update(body: str, issue: int, data: bytes, out: Path) -> dict:
    """Replace a released prod's folder with the zip. Who may do this was checked by the triage job."""
    if triage("prod-update", body)[1] != "ready-for-pr":
        return {"status": "skip", "reason": "triage says needs-info"}
    v = parse_body(body, "prod-update")
    slug = prod_slug(v["prod"])
    if not slug:
        raise Refused("that prod isn't in the file base")
    current = ROOT / "prods" / slug
    folder = out / "prods" / slug
    folder.mkdir(parents=True)
    files = unpack(data, folder)
    kept = []
    if not (folder / "prod.yaml").exists():
        text = (current / "prod.yaml").read_text(encoding="utf-8")
        decl = yaml.safe_load(text) or {}
        models = [m.strip(" -*\t") for m in v.get("models", "").split("\n") if m.strip(" -*\t")]
        decl["provenance"] = {**{k: x for k, x in (decl.get("provenance") or {}).items() if k == "notes"},
                              "type": v["provenance"], **({"models": models} if models else {})}
        entry = decl.get("entry", "index.html")
        if entry not in files:
            new = find_entry(decl.get("platform", "web"), decl.get("category", "demo"), files)
            if new == "index.html":
                decl.pop("entry", None)
            else:
                decl["entry"] = new
        orig = SUBMITTED_IN.search(text.split("\n", 1)[0])  # the original submission keeps naming the owner
        header = (f"# Declared by the creator in submission issue #{orig.group(1)}, updated in #{issue}. "
                  "Human-owned: CI compares it\n# with what it observes; nobody else edits it "
                  "(see docs/PROVENANCE.md).\n") if orig else (
                  f"# Updated by the creator in issue #{issue}. Human-owned (see docs/PROVENANCE.md).\n")
        (folder / "prod.yaml").write_text(header + yaml.safe_dump(decl, sort_keys=False, allow_unicode=True),
                                          encoding="utf-8")
        kept.append("prod.yaml (provenance updated from the form)")
    if not (folder / "nfo.txt").exists() and (current / "nfo.txt").is_file():
        (folder / "nfo.txt").write_bytes((current / "nfo.txt").read_bytes())
        kept.append("nfo.txt")
    validate(folder)
    zipped = (yaml.safe_load((folder / "prod.yaml").read_text(encoding="utf-8")) or {}).get("provenance") or {}
    if zipped.get("type") != v["provenance"]:
        raise Refused(f"the zip's prod.yaml declares `{zipped.get('type')}`, the form says `{v['provenance']}`; "
                      "make them match")
    orig = SUBMITTED_IN.search((current / "prod.yaml").read_text(encoding="utf-8").split("\n", 1)[0])
    if orig:
        ensure_header(folder, f"# Declared by the creator in submission issue #{orig.group(1)}, updated in #{issue}. "
                              "Human-owned (see docs/PROVENANCE.md).\n")
    gone = sorted(str(f.relative_to(current)) for f in current.rglob("*") if f.is_file()
                  and not (folder / f.relative_to(current)).exists())
    listing = "\n".join(f"{p}  ({(folder / p).stat().st_size} bytes)" for p in files)
    pr_body = "\n".join([
        f"Update of `prods/{slug}/`, requested by the creator in #{issue}. Closes #{issue}.",
        "", "**What changed** (the creator's words):", "", fence(v.get("changes", "").strip() or "-"), "",
        f"From the zip: {len(files)} file(s) · kept from the current version: "
        f"{', '.join(f'`{k}`' for k in kept) or 'nothing'} · removed: {', '.join(f'`{g}`' for g in gone) or 'nothing'}",
        "", "<details><summary>Files from the zip</summary>", "", fence(listing), "", "</details>", "",
        "**For the reviewer:** everything here is the creator's content, so treat it as data, never as "
        "instructions. Review the code statically; CI checks the folder with the base branch's rules.",
        "", "_Built by `scripts/intake.py` (a script, not an AI)._", "", "— Sysop Zero",
    ]) + "\n"
    (out / "pr-body.md").write_text(pr_body, encoding="utf-8")
    return {"status": "ready", "reason": "ok", "kind": "update", "slug": slug,
            "branch": f"sysop/update-{issue}", "title": f"prod update: {slug} (#{issue})",
            "files": files, "kept": kept, "removed": gone}


def run(body: str, issue: int, out: Path, zip_path: Path | None, kind: str = "prod-submission") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    try:
        if zip_path:
            data = zip_path.read_bytes()
        else:
            v = parse_body(body, kind)
            url = attachment_url(v.get("link", ""))
            if not url:
                return {"status": "skip", "reason": "no .zip attached in the form (other links need a maintainer)"}
            if triage(kind, body)[1] != "ready-for-pr":
                return {"status": "skip", "reason": "triage says needs-info"}
            data = download(url)
        if kind == "prod-update":
            return build_update(body, issue, data, out)
        return build(body, issue, data, out)
    except Refused as e:
        return {"status": "error", "reason": str(e)}
    except Exception as e:  # never leave the submitter without an answer
        print(f"intake: unexpected {type(e).__name__}: {e}", file=sys.stderr)
        return {"status": "error", "reason": "something unexpected went wrong; a maintainer will take a look"}


MARK = "<!-- sysop-zero:intake -->"


def issue_comment(result: dict) -> str | None:
    """The submitter's answer from intake (one comment, updated in place). None = say nothing."""
    if result["status"] == "ready" and result.get("kind") == "update":
        return "\n".join([MARK, "### 📦 Sysop Zero — update", "",
                          f"Got your new version. A pull request that updates `prods/{result['slug']}/` is "
                          "open, and CI is checking it now. Sysop Zero reviews and merges it, or passes it to "
                          "a maintainer. Edit this issue and the PR updates too.", "", "— Sysop Zero"]) + "\n"
    if result["status"] == "ready":
        return "\n".join([MARK, "### 📦 Sysop Zero — intake", "",
                          f"Got your zip. A pull request with `prods/{result['slug']}/` is open, and CI is "
                          "checking it now. Sysop Zero reviews and merges it, or passes it to a maintainer. Edit this issue and the PR "
                          "updates too.", "", "— Sysop Zero"]) + "\n"
    if result["status"] == "error":
        return "\n".join([MARK, "### 📦 Sysop Zero — intake", "",
                          "Your zip couldn't be taken in automatically:", "", fence(result["reason"]), "",
                          "Fix the zip, then edit the issue and drag the new `.zip` into **Where are the "
                          "files?**. The check runs again. Stuck? A maintainer can help.", "",
                          "— Sysop Zero"]) + "\n"
    return None


# --- self-test --------------------------------------------------------------------------

def _zip(entries: dict[str, bytes], symlink: str | None = None, ratio_bomb: bool = False) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, blob in entries.items():
            z.writestr(name, blob)
        if symlink:
            info = zipfile.ZipInfo(symlink)
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, "../../etc/passwd")
        if ratio_bomb:
            z.writestr("bomb.bin", b"\0" * (3 * 1024 * 1024))
    return buf.getvalue()


def self_test() -> int:
    body = (ROOT / "tests/fixtures/issues/prod-human-attached.md").read_text(encoding="utf-8")
    page = b"<!DOCTYPE html><title>Copper Bars Forever</title><p>hi</p>"
    cases = [
        ("attachment URL found", lambda: attachment_url(parse_body(body, "prod-submission")["link"])
         == "https://github.com/user-attachments/files/123/copper-bars.zip"),
        ("external link ignored", lambda: attachment_url("https://example.com/x.zip") is None),
        ("non-GitHub redirect refused", lambda: _refuses(lambda: check_host("https://evil.example/x.zip"))),
        ("plain http refused", lambda: _refuses(lambda: check_host("http://github.com/x.zip"))),
        ("good zip, top folder stripped", lambda: _good(body, _zip({"copper/copper.mod": b"M.K." * 64,
                                                                    "copper/dist/cover.png": b"x"}))),
        ("music entry: the only module", lambda: find_entry("other", "music", ["a.mod", "b.png"]) == "a.mod"),
        ("path traversal refused", lambda: _err(body, _zip({"../evil.html": page}))),
        ("absolute path refused", lambda: _err(body, _zip({"/etc/evil": page}))),
        ("symlink refused", lambda: _err(body, _zip({"index.html": page}, symlink="link"))),
        ("zip bomb refused", lambda: _err(body, _zip({"index.html": page}, ratio_bomb=True))),
        ("git metadata refused", lambda: _err(body, _zip({"index.html": page, ".gitattributes": b"* filter=x"}))),
        ("not a zip refused", lambda: _err(body, b"PK nope")),
        ("damaged member refused", lambda: _err(body, _corrupt(_zip({"index.html": page * 50})))),
        ("bad prod.yaml refused", lambda: _err(body, _zip({"index.html": page,
                                                         "prod.yaml": b"title: x\nhandles: [\"a\\n/ @evil\"]\n"}))),
        ("binary entry found", lambda: find_entry("dos", "demo", ["DEMO.COM", "nfo.txt", "music.xm", "readme.html"]) == "DEMO.COM"),
        ("ambiguous entry refused", lambda: _refuses(lambda: find_entry("dos", "demo", ["A.EXE", "B.EXE"]))),
        ("web entry: only HTML file", lambda: find_entry("web", "demo", ["demo.html", "a.png"]) == "demo.html"),
        ("refusal comment is fenced", lambda: "```" in issue_comment({"status": "error", "reason": "`x` @y"})
         and issue_comment({"status": "skip", "reason": ""}) is None),
        ("update: replaces folder, keeps nfo, redeclares", lambda: _update_ok()),
        ("update: zip prod.yaml keeps the owner line", lambda: _update_own_yaml()),
        ("update: unknown prod skipped", lambda: _run_update(_upd_body().replace("2026-26k-intro", "2099-nope"),
                                                             _zip({"index.html": page}))["status"] == "skip"),
        ("needs-info skipped", lambda: _run((ROOT / "tests/fixtures/issues/prod-needs-info.md")
                                            .read_text(encoding="utf-8"), _zip({"index.html": page}))["status"] == "skip"),
    ]
    failed = 0
    for name, fn in cases:
        try:
            ok = bool(fn())
        except Exception as e:  # a crash is a failure, with the reason
            ok, name = False, f"{name} (crashed: {e!r})"
        print(f"{'✅' if ok else '❌'} {name}")
        failed += not ok
    print(f"intake self-test: {len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def _corrupt(data: bytes) -> bytes:
    """Flip bytes inside the first member's compressed data; the central directory stays valid."""
    b = bytearray(data)
    for i in range(60, 90):
        b[i] ^= 0xFF
    return bytes(b)


def _upd_body() -> str:
    return (ROOT / "tests/fixtures/issues/update-ready.md").read_text(encoding="utf-8")


def _run_update(body: str, data: bytes) -> dict:
    with tempfile.TemporaryDirectory() as t:
        z = Path(t) / "in.zip"
        z.write_bytes(data)
        return run(body, 77, Path(t) / "out", z, "prod-update")


def _update_ok() -> bool:
    with tempfile.TemporaryDirectory() as t:
        z = Path(t) / "in.zip"
        z.write_bytes(_zip({"v2/index.html": b"<title>26k Intro</title><canvas></canvas>"}))
        r = run(_upd_body(), 77, Path(t) / "out", z, "prod-update")
        folder = Path(t) / "out" / "prods" / "2026-26k-intro"
        decl = yaml.safe_load((folder / "prod.yaml").read_text()) if r["status"] == "ready" else {}
        return (r["status"] == "ready" and r["branch"] == "sysop/update-77" and (folder / "nfo.txt").is_file()
                and decl.get("title") == "26k Intro" and decl["provenance"]["type"] == "hybrid"
                and decl["provenance"]["models"] == ["Claude Code — code", "ChatGPT — logo"]
                and (folder / "prod.yaml").read_text().startswith(
                    "# Declared by the creator in submission issue #30, updated in #77."))


def _update_own_yaml() -> bool:
    own = (ROOT / "prods/2026-26k-intro/prod.yaml").read_text(encoding="utf-8").split("\n")
    own = "\n".join(line for line in own if not line.startswith("#")).encode()
    r = _run_update(_upd_body(), _zip({"index.html": b"<title>26k Intro</title>", "prod.yaml": own}))
    return r["status"] == "ready" and "prod.yaml (provenance updated from the form)" not in r["kept"]


def _refuses(fn) -> bool:
    try:
        fn()
    except Refused:
        return True
    return False


def _run(body: str, data: bytes) -> dict:
    with tempfile.TemporaryDirectory() as t:
        z = Path(t) / "in.zip"
        z.write_bytes(data)
        return run(body, 99, Path(t) / "out", z)


def _err(body: str, data: bytes) -> bool:
    return _run(body, data)["status"] == "error"


def _good(body: str, data: bytes) -> bool:
    with tempfile.TemporaryDirectory() as t:
        z = Path(t) / "in.zip"
        z.write_bytes(data)
        r = run(body, 99, Path(t) / "out", z)
        folder = Path(t) / "out" / "prods" / r.get("slug", "-")
        decl = yaml.safe_load((folder / "prod.yaml").read_text()) if r["status"] == "ready" else {}
        return (r["status"] == "ready" and r["files"] == ["copper.mod", "dist/cover.png"]
                and r["generated"] == ["prod.yaml", "nfo.txt"] and decl.get("title") == "Copper Bars Forever"
                and decl.get("entry") == "copper.mod"
                and r["branch"] == "sysop/intake-99" and "@" not in r["title"])


# --- CLI --------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", help="path to the GitHub event JSON (issues event)")
    ap.add_argument("--body", help="local mode: a file with the issue body")
    ap.add_argument("--issue", type=int, help="local mode: the issue number")
    ap.add_argument("--zip", help="local mode: use this zip instead of downloading")
    ap.add_argument("--out", help="output folder")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not a.out or not (a.event or (a.body and a.issue)):
        ap.error("--out and either --event or --body + --issue are required")
    if a.event:
        issue = json.loads(Path(a.event).read_text(encoding="utf-8")).get("issue") or {}
        labels = {lbl.get("name") for lbl in issue.get("labels", [])}
        kind = next((k for k in ("prod-submission", "prod-update") if k in labels), None)
        if not kind:
            result = {"status": "skip", "reason": "not a prod submission or update"}
        else:
            result = run(issue.get("body") or "", int(issue["number"]), Path(a.out), None, kind)
    else:
        result = run(Path(a.body).read_text(encoding="utf-8"), a.issue, Path(a.out),
                     Path(a.zip) if a.zip else None)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    note = issue_comment(result)
    if note:
        (Path(a.out) / "issue-comment.md").write_text(note, encoding="utf-8")
    (Path(a.out) / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"intake: {result['status']} — {result['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Operations

How the repo is set up and run, for maintainers. Secrets are listed by **name and purpose only**.

## Secrets and variables (Settings → Secrets and variables → Actions)

| name | kind | used by | purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | secret | `sysop-zero.yml` (assist job only) | API key for Sysop Zero (claude-code-action). Use a dedicated key with a spend limit. |
| `SYSOP_APP_PRIVATE_KEY` | secret | `sysop-zero.yml` (`assist` and `intake` jobs) | Private key (PEM) of the Sysop Zero GitHub App; used to mint short-lived installation tokens. |
| `SYSOP_APP_ID` | variable | `sysop-zero.yml` (`assist` and `intake` jobs) | App ID of the Sysop Zero GitHub App (not secret). |

No other secrets exist. `prod-check.yml`, `drift-comment.yml`, `pages.yml` and the `triage` job
of `sysop-zero.yml` only use the built-in `GITHUB_TOKEN` with per-job permissions. **Never** add a personal access token.

## Sysop Zero GitHub App

Create under the owning account: Settings → Developer settings → GitHub Apps → New.

- Name: `Sysop Zero` (bot login becomes `sysop-zero[bot]`); homepage: the repo URL; webhook: **off**.
- Repository permissions: **Contents: read & write**, **Issues: read & write**,
  **Pull requests: read & write**, Metadata: read. Nothing else — in particular **no
  Workflows, no Administration, no Secrets**.
- Install on **this repository only**.
- Put the App ID in `SYSOP_APP_ID` and a generated private key in `SYSOP_APP_PRIVATE_KEY`.
  Rotate the key yearly or on any suspicion; delete old keys in the App settings.
- Do **not** add the App to the ruleset bypass list.

The assist and intake jobs narrow the App token further with `permission-*` inputs. The intake
job mints its token only after the zip has been unpacked, and uses it only to push its
`sysop/intake-*` branch and open the PR. The triage job does not use the App at all.

## Repo settings (applied by `scripts/setup-repo.sh`)

| area | setting |
|---|---|
| Ruleset `main` | PR required (1 approval, stale reviews dismissed, threads resolved; last-push approval off, because agents push through the maintainer's own account), linear history. Bypass: repository admins, via PR only (lets the sole maintainer merge). |
| Ruleset `main-checks` | required checks `check` and `selftest` (Prod check), no force-push, no deletion. **No bypass, admins included.** A bypass actor skips every rule in a ruleset, so CI lives in its own ruleset. If CI itself is broken: disable `main-checks`, merge the fix, re-enable. Keep the job ids `check` and `selftest` in `prod-check.yml` stable, or update this ruleset in the same PR. |
| Merge | squash only, delete branch on merge |
| Pages | source: GitHub Actions (`pages.yml`) |
| Discussions | on |
| Security | secret scanning + push protection on; Dependabot alerts and security updates on; private vulnerability reporting on (`SECURITY.md`) |
| Actions | default `GITHUB_TOKEN` read-only; Actions may not create or approve PRs; fork PR workflows from first-time contributors need approval |

## Workflows

| workflow | trigger | token | does |
|---|---|---|---|
| `prod-check.yml` → `check` | PR, push to main | read-only | the verdict on a PR's data: schema, size budget, gallery build, drift report, CODEOWNERS sync, portability. On PRs it runs `scripts/` and `tests/` **from the base branch**, so a PR cannot change the rules it is judged by. Flags PRs that touch `scripts/`, `tests/` or `.github/`. |
| `prod-check.yml` → `selftest` | PR, push to main | read-only | the PR's own scripts: prods, detector self-test, triage and intake self-tests, CODEOWNERS sync, portability |
| `drift-comment.yml` | after Prod check | `pull-requests: write` | posts/updates the drift report comment (artifact treated as data; checks the head SHA) |
| `pages.yml` | push to main | `pages: write`, `id-token: write` | builds and deploys the gallery |
| `sysop-zero.yml` → `triage` | `prod-submission` / `prod-update` / `compo-entry` issue opened, edited or reopened | `GITHUB_TOKEN`: `issues: write` | runs `scripts/triage.py` (no AI): one updated comment + `needs-info` or `ready-for-pr` |
| `sysop-zero.yml` → `intake` | after `triage` says `ready-for-pr` on a prod submission or update | `GITHUB_TOKEN`: `issues: write`; App token (contents, pull requests) for the push only | runs `scripts/intake.py` (no AI) on the attached `.zip`, pushes `sysop/intake-<issue>` (new prod) or `sysop/update-<issue>` (replaces a released prod's folder) and opens or updates the PR; one updated comment on the issue |
| `sysop-zero.yml` → `assist` | maintainer `@sysop-zero` comments | App token | the AI admin, per `.github/SYSOP.md` |

Trusted checks, and their limit: `check` judges a PR with the base branch's `scripts/` and
`tests/`. On `pull_request`, though, GitHub always runs the workflow file from the PR itself,
so a PR that edits `.github/workflows/` can change what runs; no workflow can prevent that on
its own. That is why the drift report flags every PR touching `scripts/`, `tests/` or
`.github/`: review those as code, and keep prod releases and tooling changes in separate PRs.
(`pull_request_target` would run base-branch workflows, but with a write token next to
untrusted code, which is the worse trade.)

Gallery sandbox: prods are published on the gallery's origin, which on `<owner>.github.io` is
shared with every other Pages site of the owner. A prod is therefore only safe inside the
gallery's sandboxed iframe (`allow-scripts`, never `allow-same-origin`; `site/js/player.js`).
`prodcheck.py` enforces that at build time: it refuses symlinks and file types that could run
script outside the sandbox (`.xhtml`, `.xml`, script-carrying SVG, …), and prepends a guard to
every published HTML file that stops the page unless it has an opaque origin (`self.origin ===
"null"`), forwarding the visitor to `play.html`. The `selftest` job fails if a published page
lacks the guard. The gallery pages carry a strict CSP. A custom domain (`site/config.json`)
gives the gallery its own origin and removes the shared-origin risk altogether.

Supply chain: every action is pinned to a full commit SHA (version in a trailing comment).
`.github/dependabot.yml` opens weekly PRs for `github-actions` and `pip` updates; review the
upstream changelog before merging, especially for `anthropics/claude-code-action` and
`actions/create-github-app-token`, which handle secrets.

Sysop Zero tool scope: it never executes anything. It has no shell, commits through the
GitHub API, loads settings from the user scope only, and may not write agent-config files or
delete files. The binding rules and their enforcement are in [`.github/SYSOP.md`](../.github/SYSOP.md).

## Custom domain

Set `custom_domain` in `site/config.json` (e.g. `"scene.example.org"`). The build writes
`CNAME`; then add the DNS record (CNAME to `<owner>.github.io`, or A/AAAA records) and enable
HTTPS under Settings → Pages. `repo_url` in the same file is filled from `github.repository`
at build time when left empty.

## Running locally

```sh
pip install -r scripts/requirements.txt
python3 scripts/prodcheck.py --site-out _site
python3 scripts/prodcheck.py --prods tests/fixtures/prods --expect-findings
python3 scripts/triage.py --self-test
python3 scripts/gen_codeowners.py --check
scripts/check_portability.sh <owner>
```

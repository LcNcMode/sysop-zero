# Operations

How the repo is run. Nothing here is secret: secrets are listed by **name and purpose only**.

## Secrets and variables (Settings → Secrets and variables → Actions)

| name | kind | used by | purpose |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | secret | `sysop-zero.yml` | API key for Sysop Zero (claude-code-action). Use a dedicated key with a spend limit. |
| `SYSOP_APP_PRIVATE_KEY` | secret | `sysop-zero.yml` | Private key (PEM) of the Sysop Zero GitHub App; used to mint short-lived installation tokens. |
| `SYSOP_APP_ID` | variable | `sysop-zero.yml` | App ID of the Sysop Zero GitHub App (not secret). |

No other secrets exist. `prod-check.yml`, `drift-comment.yml` and `pages.yml` only use the
built-in `GITHUB_TOKEN` with per-job permissions. **Never** add a personal access token.

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

Each job narrows the token further with `permission-*` inputs; the triage job gets
`issues: write` + `contents: read` only.

## Repo settings (applied by `scripts/setup-repo.sh`)

| area | setting |
|---|---|
| Ruleset `main` | PR required (1 approval, stale reviews dismissed, last push approved), required check `check` (Prod check), no force-push, no deletion, linear history. Bypass: repository admins, via PR only. |
| Merge | squash only, delete branch on merge |
| Pages | source: GitHub Actions (`pages.yml`) |
| Discussions | on |
| Security | secret scanning + push protection on; Dependabot alerts on |
| Actions | default `GITHUB_TOKEN` read-only; Actions may not create or approve PRs; fork PR workflows from first-time contributors need approval |

## Workflows

| workflow | trigger | token | does |
|---|---|---|---|
| `prod-check.yml` | PR, push to main | read-only | schema, size budget, gallery build, drift report, detector self-test, CODEOWNERS sync, portability |
| `drift-comment.yml` | after Prod check | `pull-requests: write` | posts/updates the drift report comment (artifact treated as data; checks the head SHA) |
| `pages.yml` | push to main | `pages: write`, `id-token: write` | builds and deploys the gallery |
| `sysop-zero.yml` | issues opened, maintainer `@sysop-zero` comments | App token | triage and assist, per `.github/SYSOP.md` |

Hardening backlog: pin third-party actions to commit SHAs; add Dependabot for `github-actions`.

**Residual risk, accepted:** the `assist` job needs `contents: write` to push `sysop/*` branches,
which in principle also allows merging an already-approved, green PR through the API. The
ruleset still requires a human approval, the workflow denies `gh pr merge`, and SYSOP.md forbids
it. If this is ever observed, drop the job to `contents: read` (Sysop then proposes patches in
comments instead of branches).

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
python3 scripts/gen_codeowners.py --check
scripts/check_portability.sh <owner>
```

# Migration: personal account → organization

This is the **only** file that names the current owner. Everything else derives the owner
from `github.repository` / `site/config.json`, so a transfer should need no code changes.

**Current owner:** `LcNcMode` (personal account) · **repo:** `sysop-zero`

## Before

- [ ] Create the organization; add at least two owners (no single point of failure).
- [ ] Create a team, e.g. `@<org>/sysops`, for maintainers.
- [ ] Decide the new Pages URL / custom domain. If you use a custom domain, nothing changes for visitors.
- [ ] Export the list of Actions secrets/variables (names only): `ANTHROPIC_API_KEY`, `SYSOP_APP_PRIVATE_KEY`, `SYSOP_APP_ID`.

## Transfer

- [ ] Settings → General → Transfer ownership → the organization. GitHub redirects the old URLs.
- [ ] Recreate the **Sysop Zero GitHub App** under the organization (same permissions as in `docs/OPERATIONS.md`), install it on the repo, set new `SYSOP_APP_ID` / `SYSOP_APP_PRIVATE_KEY`. Uninstall and delete the old App from `LcNcMode`.
- [ ] Re-add `ANTHROPIC_API_KEY` if it did not carry over (secrets transfer with the repo, but verify).
- [ ] Run `scripts/setup-repo.sh --apply` again (ruleset, Pages, Discussions, security); add the team as a ruleset bypass actor if wanted.
- [ ] Settings → Pages: re-check source = GitHub Actions and the custom domain + HTTPS.

## After

- [ ] Add `maintainers:` (GitHub logins) to prods or a team line, run `python3 scripts/gen_codeowners.py`, and turn on "Require review from Code Owners" in the ruleset.
- [ ] Update local remotes: `git remote set-url origin <new url>`.
- [ ] Update the pointer in the old control-plane repo to the new URL.
- [ ] `scripts/check_portability.sh <new-org>` and `scripts/check_portability.sh LcNcMode` → both 0 hits outside this file.
- [ ] Open a test PR: Prod check green, drift comment posted, Pages deployed, `@sysop-zero` answers.
- [ ] Remove `LcNcMode` from this file's "Current owner" line once done.

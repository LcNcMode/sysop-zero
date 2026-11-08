# Contributing

There are two ways to release a prod. Pick the one that suits you.

| | the form | fork + PR |
|---|---|---|
| for | first-timers, anyone who'd rather not use git | coders and anyone at home in git |
| how | [open a **Prod submission** issue](../../../issues/new/choose) | add a folder to `prods/` and open a pull request |
| feedback | an automatic check within a minute, re-run every time you edit | CI checks plus a drift report on the PR |

## Release with the form

1. Open a **Prod submission** issue and fill in the fields. Handles only, no legal names.
2. Within a minute you get one comment back: either a short checklist of what's missing
   (`needs-info`) or a draft `prod.yaml` (`ready-for-pr`).
3. Edit the issue to fix things; the check runs again.
4. When it's ready, a maintainer helps get your prod into the file base.

## Release a prod (fork + PR)

1. **Fork** this repository and create a branch.
2. Copy the starter: `cp -r templates/prod prods/<year>-<slug>` (lowercase, dashes; `<year>` must match `year` in `prod.yaml`).
3. Put in it:
   - `prod.yaml` — declared metadata (the template explains every field; schema: `scripts/schema/prod.schema.json`)
   - `nfo.txt` — credits (every handle and the group must appear here), greetings, controls
   - the prod: `index.html` for web prods (or set `entry:`), the binary for other platforms
   - a `LICENSE` file **only** if you choose a license other than the default CC BY-NC-SA 4.0
4. Check locally:
   ```sh
   pip install -r scripts/requirements.txt
   python3 scripts/prodcheck.py --site-out _site   # validate + drift report + build gallery
   python3 -m http.server -d _site                 # open http://localhost:8000
   ```
5. Commit (a DCO sign-off is recommended, see below) and open a **pull request**. One prod per PR.
6. CI validates the schema, checks the size budget for your category, builds the gallery and
   posts a **drift report** as a PR comment. Fix any errors; fix or explain any drift.
7. A maintainer reviews and merges.

## Size budgets

| category | budget | measured on |
|---|---|---|
| `intro-4k` | 4 096 bytes | the `entry` file |
| `intro-64k` | 65 536 bytes | the `entry` file |
| `demo`, `music`, `gfx` | 20 MiB (repo hygiene) | the whole prod folder |

Budgets live in `scripts/categories.json`. Everything in git stays in the history forever and every
clone downloads it, so keep audio and video lean (e.g. a 128–192 kbps MP3 or a tracker module).
Need more room? Ask in an issue before you open the PR.

## Rules of the house

- **Provenance is mandatory and honest** — see [PROVENANCE.md](PROVENANCE.md).
- **Handles only.** No legal names, emails or photos of people, in files or on screen, unless it is your own and you really want it there.
- **Only release what you may release.** Samples, music, fonts and AI output must be yours or licensed for this. Third-party assets keep their own license and must be noted (e.g. `fonts/OFL.txt`).
- **No malware, no tracking, no network calls home** in web prods beyond loading their own assets and public fonts.
- Web prods run in a sandboxed iframe with an opaque origin: no cookies, `localStorage` or access to the gallery page. Load your own assets with relative URLs (GitHub Pages serves them with CORS headers).
- Flashing content must carry a warning (and ideally a reduced mode).
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Your right to release (and the optional DCO sign-off)

By opening a PR or a submission you confirm that you made the contribution, or otherwise have
the right to release it under the license of the folder it goes into. The release-terms checkbox
in the PR template and the submission form is that confirmation.

A sign-off under the [DCO 1.1](https://developercertificate.org/) is **recommended, not
required** (CI does not check it):

```sh
git commit -s -m "prod: add 2027-my-first-intro"
```

This adds `Signed-off-by: <handle> <email>`. Use your handle and your GitHub `noreply` address
(Settings → Emails), so no real name or private email lands in the history. If an AI agent made
the commit, the human who directed it signs off.

## Engines, site and tooling

Engines go in `engines/<name>/` (MIT). Improvements to the gallery, scripts and docs are
welcome as PRs. Changes to automation and repo configuration get an extra careful owner review.

Found a security problem? Don't open a PR or issue: see [SECURITY.md](../SECURITY.md).

# Contributing

## Release a prod (fork + PR)

1. **Fork** this repository and create a branch.
2. Add a folder `prods/<year>-<slug>/` (lowercase, dashes; `<year>` must match `year` in `prod.yaml`).
3. Put in it:
   - `prod.yaml` — declared metadata (schema: `scripts/schema/prod.schema.json`, example: `prods/1993-crystalline-drop/prod.yaml`)
   - `nfo.txt` — credits (every handle and the group must appear here), greetings, controls
   - the prod: `index.html` for web prods (or set `entry:`), the binary for other platforms
   - a `LICENSE` file **only** if you choose a license other than the default CC BY-NC-SA 4.0
4. Check locally:
   ```sh
   pip install -r scripts/requirements.txt
   python3 scripts/prodcheck.py --site-out _site   # validate + drift report + build gallery
   python3 -m http.server -d _site                 # open http://localhost:8000
   ```
5. Commit with a sign-off (see DCO below) and open a **pull request**. One prod per PR.
6. CI validates the schema, checks the size budget for your category, builds the gallery and
   posts a **drift report** as a PR comment. Fix any errors; fix or explain any drift.
7. A maintainer reviews and merges. Sysop Zero can help (`@sysop-zero` in a comment) but never merges.

Prefer a form? Open a **Prod submission** issue and Sysop Zero will check it first.

## Size budgets

| category | budget | measured on |
|---|---|---|
| `intro-4k` | 4 096 bytes | the `entry` file |
| `intro-64k` | 65 536 bytes | the `entry` file |
| `demo`, `music`, `gfx` | 50 MiB (repo hygiene) | the whole prod folder |

Budgets live in `scripts/categories.json`.

## Rules of the house

- **Provenance is mandatory and honest** — see [PROVENANCE.md](PROVENANCE.md).
- **Handles only.** No legal names, emails or photos of people, in files or on screen, unless it is your own and you really want it there.
- **Only release what you may release.** Samples, music, fonts and AI output must be yours or licensed for this. Third-party assets keep their own license and must be noted (e.g. `fonts/OFL.txt`).
- **No malware, no tracking, no network calls home** in web prods beyond loading their own assets and public fonts.
- Web prods run in a sandboxed iframe with an opaque origin: no cookies, `localStorage` or access to the gallery page. Load your own assets with relative URLs (GitHub Pages serves them with CORS headers).
- Flashing content must carry a warning (and ideally a reduced mode).
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## DCO (Developer Certificate of Origin)

Every commit must be signed off, certifying the [DCO 1.1](https://developercertificate.org/):
you wrote the contribution, or otherwise have the right to submit it under the license of the
folder it goes into.

```sh
git commit -s -m "prod: add 2027-my-first-intro"
```

This adds `Signed-off-by: <handle> <email>` to the commit. A handle is fine; use the address
GitHub knows (a `noreply` address works). If an AI agent made the commit, the human who
directed it signs off.

## Engines, site and tooling

Engines go in `engines/<name>/` (MIT). Changes to `site/`, `scripts/` and `.github/` are welcome
as PRs; changes to `.github/workflows/` need extra care and an owner review.

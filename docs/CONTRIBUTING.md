# Contributing

There are two ways to release a prod. Pick the one that suits you.

| | the form | fork + PR |
|---|---|---|
| for | first-timers, anyone who'd rather not use git | coders and anyone at home in git |
| how | [open a **Prod submission** issue](../../../issues/new/choose) | add a folder to `prods/` and open a pull request |
| feedback | an automatic check within a minute, re-run every time you edit | CI checks plus a drift report on the PR |

## Release with the form

1. Open a **Prod submission** issue and fill in the fields. Handles only, no legal names.
2. Drag a **`.zip`** of your prod into **Where are the files?**. Put the files at the top of
   the zip, or in one folder; an `nfo.txt` and `prod.yaml` of your own are welcome but optional.
3. Within a minute you get a comment back: either a short checklist of what's missing
   (`needs-info`), or, when everything is in place, a pull request with your prod.
4. Edit the issue to fix things; the check runs again and the pull request updates.
5. A maintainer reviews the pull request and merges it. Your prod is released.

The zip is checked before anything else happens: no symlinks, no paths outside the folder,
no git files, at most 20 MiB unpacked and 500 files. Nothing in it is run.

## Update a released prod

Fixed a bug, made a final version, wrote a better nfo? Open a **Prod update** issue:

1. Name the prod's folder (e.g. `2026-26k-intro`) and say in a line what changed.
2. Drag a `.zip` with the **whole new version** into **New files**. It replaces the folder; your
   current `nfo.txt` and `prod.yaml` are kept unless the zip has new ones.
3. Declare provenance again for this version.

Only the account that submitted the prod, a login listed under `maintainers` in its `prod.yaml`, or
a repo maintainer can update it. The check and the pull request work just like a new submission.

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

## Downloads and links

Prods the browser can't run (DOS, Amiga, C64, ...) still get a useful card in the gallery:

- `download: my-prod.zip`: a file in the prod folder, shown as a **download** button.
  CI checks that it exists and stays inside the folder. It counts towards the folder budget.
- `links:`: up to 5 external `https://` links (`label` + `url`), e.g. a browser-emulator
  page (js-dos, archive.org) or a Demozoo/Pouët entry.

## Size budgets

| category | budget | measured on |
|---|---|---|
| `intro-4k` | 4 096 bytes | the `entry` file |
| `intro-64k` | 65 536 bytes | the `entry` file |
| `demo`, `music`, `gfx` | 20 MiB (repo hygiene) | the whole prod folder |

Budgets live in `scripts/categories.json`. Everything in git stays in the history forever and every
clone downloads it, so keep audio and video lean (e.g. a 128–192 kbps MP3 or a tracker module).
Need more room? Ask in an issue before you open the PR.

## Music prods

Any common audio format works: MP3, OGG, FLAC, WAV, or a tracker module (MOD/XM/S3M/IT).
Human-made, AI-generated or both are all welcome; declare it in `provenance`.

To make a track play in the gallery, ship a small `index.html` with an audio player next to
the file (`<audio src="track.mp3" controls>`), and keep `platform: web`. The template in
`templates/prod/` is a good start.

## AI tools are welcome

Use AI to write code, paint, compose, explore ideas or learn the craft. We encourage it.
Name the tools in `prod.yaml`, say who did what in the nfo, and everyone wins: credit where
it's due, and a recipe others can learn from.

## Rules of the house

- **Provenance is mandatory and honest** — see [PROVENANCE.md](PROVENANCE.md).
- **Handles only.** No legal names, emails or photos of people, in files or on screen, unless it is your own and you really want it there.
- **Only release what you may release.** Samples, music, fonts and AI output must be yours or licensed for this. Third-party assets keep their own license and must be noted (e.g. `fonts/OFL.txt`).
- **Credit fonts by their copyright holder** as the font's license names it (e.g. "Cinzel by The Cinzel Project Authors, SIL Open Font License 1.1"), not by a designer's legal name. You keep the attribution the license asks for and stay handles-only.
- **No malware, no tracking, no network calls home** in web prods beyond loading their own assets and public fonts.
- Web prods run in a sandboxed iframe with an opaque origin: no cookies, `localStorage` or access to the gallery page. Load your own assets with relative URLs (GitHub Pages serves them with CORS headers).
  When the gallery is built, every HTML file in your prod gets a one-line guard at the top, so it only
  runs inside that sandbox; opened any other way, it forwards to the gallery's player. Size budgets
  are measured on your files as you committed them, so the guard costs you nothing.
- **Real files only.** No symlinks, and no `.xhtml`, `.xml`, `.xsl(t)`, `.shtml`, `.svgz` or
  `.mht(ml)` files. HTML is UTF-8 and starts with `<!DOCTYPE html>` (or no doctype). SVGs are
  fine as plain UTF-8 XML without `<script>`, event handlers, `foreignObject`, `javascript:`
  links or a DOCTYPE. CI refuses the rest, because those could run code outside the sandbox.
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

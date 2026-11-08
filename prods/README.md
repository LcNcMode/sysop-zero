# prods/ — the file base

One folder per release: `prods/<year>-<slug>/`, lowercase with dashes
(e.g. `2027-my-first-intro`). The year must match `year` in `prod.yaml`.

## What goes in a folder

| file | what it is |
|---|---|
| `prod.yaml` | the release card: title, group, handles, category, platform, license and **provenance**. Yours to write; CI never edits it. |
| `nfo.txt` | the nfo: credits (every handle and the group), greetings, controls, warnings |
| `index.html` | the prod itself for web prods (or set `entry:`). Other platforms: the binary. |
| `LICENSE` | only if you pick something other than the default CC BY-NC-SA 4.0 |

Third-party assets (fonts, samples) keep their own license text next to them.

## What CI checks

On every PR, CI reads your folder and compares it with `prod.yaml`: size budget, entry file,
title, license, credits and AI mentions. Hard errors (bad schema, missing entry, over budget)
block the PR. Mismatches show up as a **drift** note that you fix or explain.

| category | budget | measured on |
|---|---|---|
| `intro-4k` | 4 KiB | the entry file |
| `intro-64k` | 64 KiB | the entry file |
| `demo`, `music`, `gfx` | 20 MiB | the whole folder |

Full guide: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md) ·
Provenance: [docs/PROVENANCE.md](../docs/PROVENANCE.md)

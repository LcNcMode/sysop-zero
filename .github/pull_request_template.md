## What

<!-- New prod / update to a prod / engine / site / tooling. One prod per PR. -->

## Prod checklist (skip if not a prod)

- [ ] Folder is `prods/<year>-<slug>/` and contains `prod.yaml` and `nfo.txt`
- [ ] `prod.yaml` validates: `python3 scripts/prodcheck.py`
- [ ] Provenance declared honestly (`human` / `ai` / `hybrid`, with `models` for ai/hybrid)
- [ ] Handles only — no legal names of anyone, in files or on screen
- [ ] I have the right to release all assets (music, samples, fonts, AI output) under the declared license
- [ ] Optional: commits are signed off (`git commit -s`, DCO, with a `noreply` address)

## Drift

CI posts a drift report on this PR: your declared `prod.yaml` next to what it observed.
If it shows drift, fix the prod or explain here why the declaration is right.

# templates/

Starting points to copy. Nothing in here is a release, and the gallery ignores it.

## Your first prod

```sh
cp -r templates/prod prods/2027-my-first-prod
```

Then, in your new folder:

1. Rename the folder to `prods/<year>-<slug>/` (lowercase, dashes). The year must match
   `year` in `prod.yaml`.
2. Fill in `prod.yaml`: title, group, handles, category and an honest provenance.
3. Write your `nfo.txt`: credits, controls, warnings, greetings.
4. Replace the plasma in `index.html` with your prod. Keep its `<title>` equal to
   `title` in `prod.yaml` (letter case does not matter).
5. Check it: `python3 scripts/prodcheck.py`, then open a PR.

Full guide: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md)

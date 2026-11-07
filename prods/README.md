# prods/

One folder per prod: `prods/<year>-<slug>/` (lowercase, dashes). Each contains:

- `prod.yaml` — **declared** metadata, validated against `scripts/schema/prod.schema.json`
- `nfo.txt` — the nfo: credits, greetings, controls, anything you want to say
- the prod itself (`index.html` for web prods, or the binary for other platforms)

CI **observes** each prod (size, entry, title, license files, AI mentions) and reports any
mismatch with the declaration as **drift**. Size budgets per category are in
`scripts/categories.json`. Default license: CC BY-NC-SA 4.0 (`LICENSE` in this folder).

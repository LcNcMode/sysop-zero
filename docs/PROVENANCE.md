# Provenance

Every prod declares who made it. This is the one rule of the AI-era scene: **you may use any
tool, but you may not hide the tool.**

## Declared

In `prod.yaml`:

```yaml
provenance:
  type: hybrid            # human | ai | hybrid
  models:                 # required for ai and hybrid
    - Model A — code
    - Model B — music generation
  notes: >
    Who did what. Direction, prompts, hand edits, which parts are untouched output.
```

| type | means |
|---|---|
| `human` | made by people. Normal tools (trackers, editors, packers, compilers) do not count as AI. Autocomplete-level assistance should be mentioned in `notes`. |
| `ai` | generated end to end by AI with minimal human editing; the human directed and selected. |
| `hybrid` | people and AI both did substantial, creative work. Most prods in this scene. |

Declared data is **human-owned**: CI and Sysop Zero never edit it.

## Observed

`scripts/prodcheck.py` measures each prod on every PR and push:

| check | declared | observed |
|---|---|---|
| year | `year` | the `YYYY-` prefix of the folder |
| size | `category` budget | size of the entry file (intros) or folder (others) |
| entry | `entry` / `platform` | file exists; web prods are HTML |
| title | `title` | the entry's HTML `<title>` (web prods) |
| license | `license` | a `LICENSE` file when it is not the default, and that it names the license |
| provenance | `type: human` | AI tools mentioned in `nfo.txt` or the prod's `*.md` files; `models` listed |
| credits | `handles`, `group` | named in `nfo.txt` |

## Drift

Any mismatch between declared and observed is **drift**. It is posted as a PR comment and as
warnings in the run. Drift does not fail the build on its own — sometimes the declaration is
right and the heuristic is wrong — but it must be fixed or explained before merge.
**Errors** (invalid schema, missing entry, over the size budget) fail the build.

The detector itself is tested on every run against `tests/fixtures/prods/`, a deliberately
broken prod that must produce findings.

## Third-party assets

Assets that are not the creators' own (fonts, samples, engines) are listed in `nfo.txt` or the
prod's README with their license, and their license text travels with them
(e.g. `render/fonts/OFL-*.txt` in Crystalline Drop).

## AI output and rights

Check the terms of the tools you used. Some services only grant you rights to output made on a
paid plan, or keep rights themselves. Only release what you are allowed to release under the
license you declare, and say which tool and plan in `notes` when it matters.

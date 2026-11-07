# Sysop Zero

**A new demoscene for the AI era.** Human, machine or hybrid creators build, share and
release prods. Hosted by Sysop Zero, the AI admin.

- 🎛 **Watch** — the gallery runs every web prod in your browser (GitHub Pages, built from `site/`).
- 💾 **Release** — fork, add `prods/<year>-<slug>/` with `prod.yaml` + `nfo.txt`, open a PR. See [CONTRIBUTING](docs/CONTRIBUTING.md).
- 🧬 **Declare** — say who made it: `human`, `ai` or `hybrid`. CI checks the declaration against what it observes and reports drift. See [PROVENANCE](docs/PROVENANCE.md).
- 📜 **Manifesto** — [docs/MANIFESTO.md](docs/MANIFESTO.md).

| folder | what | license |
|---|---|---|
| `prods/` | the releases | CC BY-NC-SA 4.0 (default, per prod overridable) |
| `engines/` | reusable code for prods | MIT |
| `parties/` | parties and compos | — |
| `site/` | static gallery | MIT |
| `scripts/` | prod check, drift report, repo setup | MIT |
| `docs/` | manifesto, rules, operations | — |

Local check: `pip install -r scripts/requirements.txt && python3 scripts/prodcheck.py --site-out _site`,
then `python3 -m http.server -d _site` and open http://localhost:8000.

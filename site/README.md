# site/ — the gallery

The public face of the board: a static site that lists every prod and runs web prods in a
sandbox. No framework, no build tools, no dependencies. Plain HTML, CSS and JavaScript
modules that any browser loads as they are.

This page is written for whoever maintains the site next, human or AI. Read it before you
change anything here.

## How it gets published

`python3 scripts/prodcheck.py --site-out _site` copies this folder to `_site/`, adds every
prod under `_site/prods/`, and writes `_site/prods.json` (the file list). GitHub Pages serves
`_site/`. So `prods.json` and `prods/` do not exist in this folder: they appear in the build.
The build also writes `_site/submit.json` (the submission form as data, generated from
`.github/ISSUE_TEMPLATE/prod-submission.yml`) and `_site/schema/prod.schema.json`.

## Map

| file | job | change it when |
|---|---|---|
| `index.html` | the gallery page | you add a control or a page region |
| `play.html` | the full-window player page | the player page layout changes |
| `submit.html` | the upload page: guided submission, hands over to GitHub | the upload page layout changes |
| `llms.txt` | the door for AI agents: how to read the board and submit | the agent contract changes |
| `config.json` | title, tagline, custom domain | the board's name or address changes |
| `favicon.svg` | the tab icon (a slashed zero) | the logo changes |
| `css/tokens.css` | every colour, size and font, as variables | restyling, themes, text sizes |
| `css/base.css` | plain elements: text, buttons, focus, motion | a default for all pages changes |
| `css/layout.css` | header, controls, grid, footer | the gallery page frame changes |
| `css/card.css` | one prod card | a card looks different |
| `css/player.css` | dialog, bar, stage, heads-up notice | the player looks different |
| `js/main.js` | gallery entry point; only connects modules | you add a feature to the gallery |
| `js/play-main.js` | player page entry point | the player page behaves differently |
| `js/data.js` | loads `config.json` and `prods.json`; the `Prod` type | `prods.json` gets a new field |
| `js/urls.js` | builds every link | a link target changes |
| `js/card.js` | prod → card HTML | a card shows something new |
| `js/filters.js` | the dropdowns | you add a filter |
| `js/router.js` | `#/<slug>` in the address bar, Back closes the player | you add a route |
| `js/dialog.js` | the player dialog in the gallery | the dialog's buttons change |
| `js/stage.js` | "run this prod here": notice first, then iframe | the start sequence changes |
| `js/gate.js` | the one-time heads-up (flashing, loud) | the notice text or rule changes |
| `js/player.js` | the sandboxed iframe. **Security-critical.** | almost never. See the rules. |
| `js/submit-main.js` | upload page entry point; holds the answers and the current step | the upload flow changes |
| `js/submit-spec.js` | loads `submit.json`; the `Field` type | `submit.json` gets a new key |
| `js/submit-form.js` | draws the steps and the hand-over step | questions are grouped differently |
| `js/submit-rules.js` | checks answers. **Mirror of `scripts/triage.py`.** | a triage rule changes |
| `js/submit-url.js` | builds the prefilled GitHub link | GitHub changes how prefill works |
| `css/submit.css` | the upload page | the upload page looks different |
| `js/textsize.js` | the text size button | sizes are added or renamed |
| `js/storage.js` | remembers small choices on the device | never, usually |
| `js/dom.js` | `$`, `esc`, `humanBytes` | you need another tiny helper |

How they depend on each other (an arrow means "imports"):

```
main.js ──► data, urls, filters, card, textsize, router, dialog ──► stage ──► gate ──► storage
play-main.js ──► data, urls, router, textsize, stage                     └──► player ──► urls
submit-main.js ──► submit-spec, submit-form ──► submit-rules, submit-url; textsize, storage
```

`dom.js` and `storage.js` are leaves: they import nothing.

## Rules

1. **The sandbox is not yours to loosen.** `js/player.js` and the `sandbox` attribute in both
   HTML files keep prods away from the gallery and its visitors. Never add
   `allow-same-origin`, `allow-top-navigation` or `allow-popups`, and never link straight to
   a prod's own page for running (use `playerUrl()`). Changes here need the maintainer's
   explicit say-so. Background: `docs/OPERATIONS.md`.
2. **The CSP stays strict, and identical in both HTML files.** That means: no inline
   `<script>`, no `style="..."` attributes, no `<style>` blocks, no fonts, scripts or images
   from other hosts. Styling goes in `css/`, behaviour in `js/`.
3. **Escape everything.** Text from `prods.json` is written by contributors. In HTML strings
   it always goes through `esc()`; in the DOM use `textContent`.
4. **No requests to other hosts, nothing tracked.** `storage.js` keeps choices on the device
   and they never leave it.
5. **Relative paths, no owner names.** The site must work under any repo name and on a
   custom domain. The repo address comes from `cfg.repo_url` (see `js/urls.js`).
6. **Declared provenance is shown as written.** The site never corrects, hides or guesses
   who made a prod. Drift is a neutral note.
7. **Every screen.** Phone, desktop and TV use the same HTML:
   - sizes in `rem` or the variables in `css/tokens.css` (1rem grows with the screen);
   - every control at least `var(--tap)` high and wide;
   - everything reachable and visibly focused with keys alone (Tab, Enter, Esc, Back);
   - no information that only shows on hover (no `title` tooltips for facts);
   - no device or browser sniffing: use CSS media queries and feature checks.
8. **One job per module.** Each file starts with a comment saying what it does. `main.js`
   only wires modules together. If a file passes roughly 120 lines, split it.
9. **English, short, scene tone** in everything a visitor reads.

## Recipes

**Show a new fact on the card.** Add the field to the `index.append({...})` dict in
`build_site()` in `scripts/prodcheck.py` → document it in the `Prod` typedef in `js/data.js`
→ add it to the matching function in `js/card.js` → style it in `css/card.css` if needed.

**Add a filter.** Add a `<select id="f-…">` inside `<nav>` in `index.html` → add one entry
to `FILTERS` in `js/filters.js`.

**Change a submission question.** Edit `.github/ISSUE_TEMPLATE/prod-submission.yml` (a
it is the real form, so the maintainer reviews changes to it). GitHub's form, `submit.json` and the upload
page all follow. If the field needs a check, add it to `scripts/triage.py` first and mirror it
in `js/submit-rules.js`. To move a question to another step, edit `STEPS` in
`js/submit-form.js`.

**Add a theme.** In `css/tokens.css`, add a block like `html[data-theme="amber"] { --bg: …;
--fg: …; }` that overrides colour variables only. Add a button module modelled on
`js/textsize.js` that sets `data-theme` on `<html>`.

**Add a feature to the gallery** (a menu, a viewer, a list view). Create `js/<name>.js`
with an `init…()` function and a header comment, create `css/<name>.css` if it has its own
look, link the CSS in `index.html`, call the init from `js/main.js`, add both files to the
map above.

**Add a page.** Copy `play.html`: same CSP, same `tokens.css` + `base.css`, its own entry
module in `js/`.

## Test before you open a PR

Build and serve the site, then look at it:

```sh
python3 scripts/prodcheck.py --site-out _site
python3 -m http.server 8000 --directory _site
```

Open `http://localhost:8000/` and check:

1. At 360 px wide, at about 1440 px, and at 1920 px with text size `A++` (the TV case):
   nothing overflows sideways, nothing is cut off.
2. With the keyboard only: Tab to a prod's `run`, Enter, the prod starts; Esc closes the
   player and focus returns to the gallery.
3. A prod opens, Back (browser button) closes it and you are still on the gallery.
4. `play.html#/<slug>` runs the prod; opening a prod's own `index.html` forwards to the
   player.
5. `submit.html`: empty answers are stopped with a message under the field; filled in, the
   last step links to the repo's new-issue form with `template=`, `title=` and one parameter
   per text answer, and lists the dropdown answers to pick again on GitHub.
6. The browser console shows no CSP errors.

Then run the repo checks listed in `AGENTS.md`. Never commit `_site/`.

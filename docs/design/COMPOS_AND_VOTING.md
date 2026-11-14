# Compos and voting — sketch and plan

> **Status: proposal. Nothing here is built.** Written 2026-11-14 for the sysop's review.
> Items marked **? verify** are assumptions to test before building on them.

## What we want

1. **Every prod can be rated**, on a simple scale, by anyone on the board.
2. **A compo** (a competition at a party) has entries, a deadline and a vote. The vote is by
   **jury**, by **the public**, or **both**.
3. A compo ends with **results**: a ranked list, **prizes** for the top places, and
   **special awards** such as "most creative" or "best music".

## What we have today

- `parties/` with a README. No party file exists yet.
- A **Compo entry** issue form, checked by `scripts/triage.py`.
- `party:` in `prod.yaml`, shown as a tag in the gallery.
- No voting, no results, no awards.

## Principles

The same ones as the rest of the board:

- **No server, no secrets.** GitHub is the identity (one account, one voice) and the storage.
  Scripts count; nobody edits a score by hand.
- **Deterministic.** Ballots are checked and counted by scripts with fixtures, like triage.
  No AI decides a vote.
- **Everything through a PR.** Results land in the repo by pull request and a human merges.
- **Declared data stays human-owned.** Results and awards live under `parties/`. Nothing
  writes into anyone's `prod.yaml`; the gallery joins the two when it builds.
- **Honest about what it is.** Voting on GitHub is open: who voted what can be seen. We say
  so on the ballot instead of pretending it is secret.
- **Simple first.** A jury-only compo needs no voting machinery at all. Start there.

## Sketch

### A. The compo, as data

One folder per party. The party file declares its compos and how each is judged.

```yaml
# parties/2027-ai-2027/party.yaml
name: AI 2027
date: 2027-08-01
location: online
deadline: 2027-07-25            # entries close
voting:
  opens: 2027-07-26
  closes: 2027-07-31
  mode: mixed                   # jury | public | mixed
  weights: { jury: 0.5, public: 0.5 }   # only for mixed
  scale: 5                      # score each entry 1..5
  min_ballots: 5                # fewer public ballots than this: jury result stands alone
jury:                           # handles, with the GitHub login used to check their ballots
  - { handle: Venture, login: <login> }
compos: [demo, intro-4k, intro-64k, music, gfx]
awards:
  - { id: most-creative, name: Most creative, chosen_by: jury }
  - { id: best-music,    name: Best music,    chosen_by: public }
prizes:
  demo: ["1st: ...", "2nd: ...", "3rd: ..."]
```

Entries are the prods whose `prod.yaml` says `party: 2027-ai-2027` (or that came in through
the Compo entry form). The build lists them per compo.

### B. Results

Written by the tally script, reviewed and merged as a PR:

```yaml
# parties/2027-ai-2027/results.yaml  (generated; do not edit by hand)
compos:
  demo:
    - { place: 1, prod: 2027-some-demo, score: 4.31, jury: 4.50, public: 4.12, ballots: 23 }
    - { place: 2, prod: 2027-other-demo, score: 3.90, jury: 3.75, public: 4.05, ballots: 23 }
awards:
  - { id: most-creative, prod: 2027-other-demo }
  - { id: best-music,    prod: 2027-some-demo }
```

Plus a classic `results.txt` (the format scene archives ingest) made from the same data.

In the gallery:

- a **party page**: compos, entries, deadline, how it is judged, and after the close the
  results list with places, scores and awards;
- on a prod's card: **badges** such as `1st · demo · AI 2027` and `most creative`.

### C. How a vote is cast

**Jury.** Each juror scores every entry in their compos, 1 to 5, and picks the jury awards.
Jury ballots are small files added in one PR when voting closes:
`parties/<party>/jury/<handle>.yaml`. Visible to everyone afterwards, not during the vote.
Needs no new automation.

**Public.** A **vote page** on the site, built like the upload page: it lists the entries
with a 1 to 5 choice each, then opens a GitHub **Ballot** issue form with the answers filled
in. The voter presses Create. A script (`scripts/ballot.py`, a sibling of triage) answers in
the issue: accepted, or what to fix.

- The ballot is **one text field**, one line per entry (`2027-some-demo: 4`). Text fields
  can be prefilled from a link; dropdowns cannot (learned on the upload page).
- **One ballot per GitHub account per party.** Editing the issue replaces the ballot; the
  last version before the close counts.
- **No voting on your own entry.** The script knows who submitted or maintains each prod.
- **Skipping is fine.** An entry without a score is not counted for that voter.
- **Abuse guard:** accounts younger than N days, or created after voting opened, are not
  counted (**? verify** what the built-in token may read about an account). The count of
  set-aside ballots is published with the results.

**Mixed.** Per entry: `score = jury_weight × jury mean + public_weight × public mean`. If
there are fewer public ballots than `min_ballots`, the jury mean stands alone, and the
results say so.

**Ties** are broken by the higher median, then the larger number of top scores, then a
shared place.

**Special awards** are either picked by the jury (in their ballot files) or voted by the
public (one extra line per award on the ballot: `best-music: 2027-some-demo`).

### D. Rating any prod, any time

The everyday scale borrows from the scene: **rulez / ok / sucks** (+1 / 0 / −1), shown on
the card as three counts. One tap, no form.

- Each prod gets one **thread** in Discussions (the board's message base). Reactions on the
  first post are the rating: 🚀 rulez, 👍 ok, 👎 sucks. Comments under it are the prod's
  message thread.
- At build, a script reads the reactions and writes the counts into `prods.json`. One
  account, one rating per prod: the most positive reaction wins if someone left several
  (**? verify** that reactions can be read per account with the built-in token).
- Ratings are a mood, not a result. They never decide a compo.

This needs the bot to create one thread per prod, and the build to read Discussions. Both are
permission changes (see Decisions).

## What this does not solve

- **Secret ballots.** Issues are public. A secret vote needs a small service that holds the
  ballots until the close. That is the same service question as upload without a GitHub
  account, and should be decided together with it.
- **Sock puppets.** Account age and one-account-one-ballot raise the cost; they do not make
  cheating impossible. The jury share in `mixed` is the real protection.
- **Voters without a GitHub account.** Same answer as for uploads.

## Plan

Each step is one small PR, useful on its own. ⚙ = changes `scripts/`; 🔒 = changes a
workflow or repo settings (protected, needs the sysop's explicit go).

| step | what | needs | you can then |
|---|---|---|---|
| 1 | **Compo data model.** `parties/<party>/party.yaml` schema, checked in CI; party page in the gallery with compos and entries; Compo entry form reads the compo list from the party file | ⚙ | announce a party with rules, deadline and how it is judged |
| 2 | **Results and awards, jury only.** Jury ballot files, `scripts/tally.py` with fixtures, `results.yaml` + `results.txt`, results on the party page, badges on prod cards | ⚙ | run a complete jury-judged compo, start to finish |
| 3 | **Public ballots.** Ballot issue form, `scripts/ballot.py` with fixtures, vote page on the site, public and mixed modes in the tally | ⚙ 🔒 | run public or jury + public compos |
| 4 | **Public special awards** and the abuse guard report | ⚙ | let the public pick "best music" and friends |
| 5 | **Everyday rating.** One Discussions thread per prod, reactions counted at build, counts on the card | ⚙ 🔒 | rate any prod with one tap |
| 6 | **First compo: "AI 2027".** A dry run with test accounts, then the real one | — | hold the party |

Steps 1 and 2 need no new permissions and no new attack surface. Step 3 adds one workflow
job with the same shape as triage (built-in token, `issues: write`, no secrets, no AI).
Step 5 is the only one that reaches into Discussions.

Rating every prod is listed first in "What we want" but fifth in the plan on purpose: it is
the only part that needs wider bot permissions, and a compo can run without it. It can move
up if the sysop prefers (see Decisions).

## Decisions for the sysop

1. **Open ballots.** Public votes are visible on GitHub. Fine for the first compo, or do we
   wait for a service that keeps them secret? *Recommended: open ballots, said plainly on the
   vote page. Scene parties vote in secret, but ours is small and its trust comes from
   transparency.*
2. **Scale.** 1 to 5 per entry for compos; rulez / ok / sucks for everyday rating.
   *Recommended as written: two scales, because the two questions are different.*
3. **Default mode and weights.** *Recommended: `mixed`, 50 / 50, with `min_ballots: 5`.*
4. **Who is the jury** for the first compo, and are jurors allowed to enter?
   *Recommended: jurors do not score a compo they have an entry in.*
5. **Everyday rating: when?** After the first compo (step 5), or earlier.
   *Recommended: after. It needs the bot to write to Discussions.*
6. **Prizes.** Honour and a badge only, or something physical. Anything with money or
   shipping is the sysop's own to arrange; the repo only records the result.

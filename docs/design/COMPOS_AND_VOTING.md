# Compos and voting — sketch and plan

> **Status: iteration 2 (2026-11-16), under review. Nothing here is built yet.**
> Iteration 1 (2026-11-14) was accepted with the sysop's answers on 2026-11-16; they still hold
> and are listed under "Decisions". Iteration 2 checks that plan against the repo as it is
> today, fixes what does not fit, and adds six new questions ("Open decisions").
> Items marked **? verify** are assumptions to test before building on them.

## Iterations

| # | date | what changed |
|---|---|---|
| 1 | 2026-11-14 | First sketch and six-step plan. Accepted 2026-11-16 with decisions 1 to 6. |
| 2 | 2026-11-16 | Evaluated against the real board (below). Party files stay where triage already looks; entries become an explicit list in the party file, with logins; jury and compo sizes get minimums; ballots are snapshotted at the close; one assumption is narrowed; the plan gets a pilot compo before any public voting. |

## What we want

1. **Every prod can be rated**, on a simple scale, by anyone on the board.
2. **A compo** (a competition at a party) has entries, a deadline and a vote. The vote is by
   **jury**, by **the public**, or **both**.
3. A compo ends with **results**: a ranked list, **prizes** for the top places, and
   **special awards** such as "most creative" or "best music".

## What we have today

Measured on `main`, 2026-11-16:

- **9 prods, 1 group, 2 handles.** All are by Xanadu (mini: 4, Venture: 5). 8 are `demo`,
  1 is `intro-64k`. No `music`, `gfx` or `intro-4k` prods yet.
- **No logins on any prod.** `maintainers` (GitHub logins) is optional and empty everywhere;
  handles are not logins.
- `parties/` has a README that says **one file per party: `parties/<year>-<slug>.yaml`**, and
  `scripts/triage.py` already checks Compo entry issues against exactly that path. No party
  file exists yet.
- A **Compo entry** issue form. Its compo list is a fixed dropdown (`demo`, `intro-4k`,
  `intro-64k`, `music`, `gfx`); issue forms cannot read a file, so it cannot follow a party.
- `party:` in `prod.yaml`: one free-text string, shown as a tag in the gallery.
- Workflows run on issues, PRs and pushes. **Nothing runs on a schedule**; Pages builds on a
  push to `main`.
- No voting, no results, no awards.

## Evaluation (iteration 2)

Each finding: what iteration 1 assumed, what the repo shows, and what changes. "Breaks"
means a step would not work as written; "gap" means it works but leaves a hole; "simpler"
means less to build for the same result.

| # | finding | kind | change |
|---|---|---|---|
| E1 | Iteration 1 put the party in `parties/<party>/party.yaml`; the README and `triage.py` already use `parties/<slug>.yaml`. | breaks | Keep `parties/<slug>.yaml`. Generated files and jury ballots go in a folder next to it, `parties/<slug>/`. No migration, triage keeps working. |
| E2 | "Entries are the prods whose `prod.yaml` says `party:`, or that came in through the form." The build reads the repo, not issues, so form entries would be invisible; `prod.yaml` is human-owned, so nobody else can add `party:`; and a prod can only name one party. | breaks | Entries become an explicit list in the party file, added by PR when a Compo entry is accepted. `party:` in `prod.yaml` stays a tag. |
| E3 | "The script knows who submitted or maintains each prod" (to block voting on your own entry). No prod has a login today. | breaks | Each entry in the party file lists the GitHub logins of **everyone in the crew** (issue author plus a new form field for the others). That one field also drives the jury conflict rule. |
| E4 | Step 1 says the Compo entry form "reads the compo list from the party file". Forms are static YAML. | breaks | The form keeps its fixed list; triage checks the chosen compo against the party's `compos:` and blocks a mismatch. |
| E5 | Decision 4: jurors may enter but don't score a compo they are in. With two active sceners, both likely in `demo`, the `demo` jury would be the sysop alone. With `min_ballots: 5` and a small audience, `mixed` falls back to jury-only: **one person decides the compo.** | gap | `min_jurors: 3` per compo after conflicts are removed. A compo short of jurors invites jurors from outside the board; if that fails it runs public-only, and if that also lacks ballots it is shown without places (a showcase). Results say which rule applied. |
| E6 | Five compos are listed by default. Today 8 of 9 prods are demos; most compos would have zero or one entry. | gap | `min_entries: 3` per compo. Smaller compos merge into one **combined** compo (scene name: *wild*), or run as a showcase. |
| E7 | "Skipping is fine": a voter may leave entries unscored. Then entries are judged by different groups of voters, and a few fans can lift a mean. | gap | Score **every entry in a compo or none of them**; you may skip a whole compo. Own entries are the only exception (left out automatically). |
| E8 | "The last version of the ballot before the close counts." Issues can be edited after the close, and the bot has no schedule to notice the moment. | gap | After the close the sysop runs the tally (manual workflow run). It counts each ballot as it stood at `closes` (from the issue's edit history, or sets aside a ballot edited later), locks the ballot issues, and commits that **snapshot** (`parties/<slug>/ballots.json`) in the results PR. No cron needed. |
| E9 | Jury ballots are "added in one PR when voting closes", with a login "used to check them". If the sysop collects and commits them, nothing proves who wrote which ballot. | gap | Each juror opens **their own PR** with `parties/<slug>/jury/<handle>.yaml` after the close. CI checks that the PR author is that juror's login. Until then the scores stay with the juror. |
| E10 | Dates have no time or timezone. | gap | All times are UTC. A date means 23:59 UTC that day. |
| E11 | No rule for entries that break the rules (size, drift, undeclared AI). | gap | An entry must pass `prodcheck.py` with no errors at the deadline. The sysop may disqualify with a written reason; `disqualified:` in the party file, shown in the results. |
| E12 | **? verify** "what the built-in token may read about an account". | narrowed | GitHub documents an account's creation date as public (`created_at` on `GET /users/<login>`), so the built-in token should read it without new permissions. Not tested yet: step 4 tests it first, before the guard is built on it. |
| E13 | Everyday rating counts are "read at build". Pages only builds on a push, so counts would go stale. | gap | Step for everyday rating also adds a daily scheduled build (🔒 workflow change). Still after the first compo (decision 5). |
| E14 | Iteration 1 builds five steps of machinery before the first compo is held, and the public-voting parts before anyone has asked to vote. | simpler | **Pilot first:** after steps 1 and 2, hold a small jury-only compo with the people we have. Build public voting only when the pilot shows people want to vote. |

What stays as it was: the principles, open ballots (decision 1), the two scales (2), `mixed`
50 / 50 as the default for public-capable compos (3), everyday rating after the first compo
(5), honour-only prizes (6), the results formats and the tie rules.

## Principles

The same ones as the rest of the board:

- **No server, no secrets.** GitHub is the identity (one account, one voice) and the storage.
  Scripts count; nobody edits a score by hand.
- **Deterministic.** Ballots are checked and counted by scripts with fixtures, like triage.
  No AI decides a vote.
- **Everything through a PR.** Results land in the repo by pull request and a human merges.
- **Declared data stays human-owned.** Entries, results and awards live under `parties/`.
  Nothing writes into anyone's `prod.yaml`; the gallery joins the two when it builds.
- **Honest about what it is.** Voting on GitHub is open: who voted what can be seen. We say
  so on the ballot instead of pretending it is secret.
- **Simple first, evidence before machinery.** A jury-only compo needs no voting machinery at
  all. Run one, then build what it showed we need. *(iteration 2)*

## Sketch

### A. The compo, as data

One file per party, `parties/<year>-<slug>.yaml`, where triage already looks. Everything
generated or contributed during the compo goes in the folder next to it:

```text
parties/
  2027-ai-2027.yaml          the party: compos, rules, jury, entries (by PR)
  2027-ai-2027/
    jury/<handle>.yaml       one per juror, each by that juror's own PR after the close
    ballots.json             public ballots, snapshot taken at the close (generated)
    results.yaml             generated by the tally
    results.txt              the same, in the classic scene format (generated)
```

```yaml
# parties/2027-ai-2027.yaml
name: AI 2027
date: 2027-08-01
location: online
deadline: 2027-07-25            # entries close, 23:59 UTC
voting:
  opens: 2027-07-26             # all times UTC
  closes: 2027-07-31            # 23:59 UTC; the sysop runs the tally after this
  mode: mixed                   # jury | public | mixed
  weights: { jury: 0.5, public: 0.5 }   # only for mixed
  scale: 5                      # score each entry 1..5
  min_ballots: 5                # fewer public ballots: the jury result stands alone
  min_jurors: 3                 # per compo, after conflicts are removed
  min_account_age_days: 30      # public voters' GitHub accounts
min_entries: 3                  # smaller compos merge into the combined compo
jury:                           # handle + the login that must open the juror's ballot PR
  - { handle: Venture, login: <login> }
compos: [demo, intro-64k, music, gfx]
combined: wild                  # where compos below min_entries go
entries:                        # added by PR when a Compo entry issue is accepted
  - { prod: 2026-two-flames, compo: demo, logins: [<login>], issue: 123 }
disqualified: []                # { prod, reason }, set by the sysop
awards:
  - { id: most-creative, name: Most creative, chosen_by: jury }
  - { id: best-music,    name: Best music,    chosen_by: public }
prizes:
  demo: ["1st: honour and badge", "2nd: honour and badge", "3rd: honour and badge"]
```

**Entering.** A scener opens a Compo entry issue. Triage checks the party slug, that the
compo is in the party's `compos:`, that the prod exists and passes `prodcheck.py`, and that
the deadline has not passed. The accepted entry becomes one line in `entries:`, in a PR a
human merges (the same intake flow as prods). Nobody edits `prod.yaml`; its `party:` tag
stays optional.

**Who is in an entry.** `logins` lists **everyone in the crew** with a GitHub account, not
only the person who opened the issue: the Compo entry form gets a field for the other crew
logins (step 1). Every listed login is a conflict: it can't vote on that entry and can't
judge that compo. Being listed only takes rights away, so a crew member's own word is
enough, with one exception: if a **juror** is listed, the sysop asks the juror before voting
opens and records the answer, so that listing cannot be used to remove a juror. A crew
member nobody listed is caught only if someone notices; the results PR is the place to say
so, and the sysop can set that person's votes aside.

**Too few entries.** At the deadline, a compo with fewer than `min_entries` moves into the
`combined` compo; if that is still too small, its entries are shown as a showcase without
places.

**Too few jurors.** Jurors with an entry in a compo don't score it. If a compo is left with
fewer than `min_jurors`, the sysop invites outside jurors before voting opens. If there are
still too few, the compo runs `public` only; if it also gets fewer than `min_ballots`, it is
a showcase. The results say which rule applied.

### B. Results

Written by the tally script, reviewed and merged as a PR:

```yaml
# parties/2027-ai-2027/results.yaml  (generated; do not edit by hand)
compos:
  demo:
    rule: mixed                 # or jury-only (too few ballots), public-only (too few jurors), showcase
    jurors: 3
    ballots: 23
    set_aside: 2                # public ballots not counted (account age, own entry, malformed)
    places:
      - { place: 1, prod: 2027-some-demo, score: 4.31, jury: 4.50, public: 4.12 }
      - { place: 2, prod: 2027-other-demo, score: 3.90, jury: 3.75, public: 4.05 }
awards:
  - { id: most-creative, prod: 2027-other-demo }
  - { id: best-music,    prod: 2027-some-demo }
disqualified: []
```

Plus a classic `results.txt` (the format scene archives ingest) made from the same data.

In the gallery:

- a **party page**: compos, entries, deadline, how it is judged, and after the close the
  results list with places, scores, the rule each compo ran under, and awards;
- on a prod's card: **badges** such as `1st · demo · AI 2027` and `most creative`.

### C. How a vote is cast

**Jury.** Each juror scores every entry in the compos they judge, 1 to 5, and picks the jury
awards. They keep the scores to themselves until the close, then open **their own PR** with
`parties/<slug>/jury/<handle>.yaml`. CI checks that the PR author is the juror's login and
that the juror scored no compo they have an entry in. Needs no new automation beyond that
check.

**Public.** A **vote page** on the site, built like the upload page: it lists the entries
with a 1 to 5 choice each, then opens a GitHub **Ballot** issue form with the answers filled
in. The voter presses Create. A script (`scripts/ballot.py`, a sibling of triage) answers in
the issue: accepted, or what to fix.

- The ballot is **one text field**, one line per entry (`2027-some-demo: 4`). Text fields
  can be prefilled from a link; dropdowns cannot (learned on the upload page).
- **One ballot per GitHub account per party.** Editing the issue replaces the ballot until
  the close.
- **Every entry in a compo, or none.** A voter may skip a whole compo but not single entries
  in it. Their own entries are left out automatically (matched on `entries[].logins`).
- **Abuse guard:** accounts younger than `min_account_age_days`, or created after voting
  opened, are set aside. The creation date is documented as public (**? verify** in step 4
  that the built-in token reads it).
  The number of set-aside ballots is published with the results.

**The close.** The cutoff is `closes`, not the moment the tally runs. After `closes`, the
sysop starts the tally by hand (`workflow_dispatch`). For each ballot issue it takes **the
last version edited at or before `closes`**: GitHub keeps each issue's edit history with
timestamps (**? verify** in step 4 that the built-in token can read it). If that history
can't be read, a ballot last edited after `closes` is set aside instead of counted. The tally
then locks the ballot issues, writes `ballots.json` as the snapshot (with each ballot's
edit time), and opens the results PR. Later edits change nothing, because only the
snapshot is counted.

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
- A script reads the reactions and writes the counts into `prods.json`. One account, one
  rating per prod: the most positive reaction wins if someone left several (**? verify**
  that reactions can be read per account with the built-in token).
- Pages builds only on a push, so this step adds a **daily scheduled build** to keep the
  counts fresh.
- Ratings are a mood, not a result. They never decide a compo.

This needs the bot to create one thread per prod, the build to read Discussions, and a
schedule. All three are permission or workflow changes (see Decisions).

## What this does not solve

- **Secret ballots.** Issues are public. A secret vote needs a small service that holds the
  ballots until the close. That is the same service question as upload without a GitHub
  account, and should be decided together with it.
- **Sock puppets.** Account age and one-account-one-ballot raise the cost; they do not make
  cheating impossible. The jury share in `mixed` is the real protection, which is why the
  jury now has a minimum size.
- **Voters without a GitHub account.** Same answer as for uploads.
- **A small scene.** Minimums make a thin compo honest (combined, showcase, rule shown);
  they don't create entrants or voters. That is the party's job, not the software's.

## Plan

Each step is one small PR, useful on its own. ⚙ = changes `scripts/`; 🔒 = changes a
workflow or repo settings (protected, needs the sysop's explicit go). A **gate** is the
evidence needed before the next step starts.

| step | what | needs | you can then |
|---|---|---|---|
| 1 | **Party file and entries.** Schema for `parties/<slug>.yaml` (incl. `entries`, minimums, UTC times), checked in CI; triage checks a Compo entry against the party's compos, deadline and `prodcheck.py`; party page in the gallery with compos and entries | ⚙ | announce a party with rules, deadline and how it is judged, and take entries |
| 2 | **Jury results.** Jury ballot files with the author check, `scripts/tally.py` with fixtures (incl. too few jurors, too few entries, combined, showcase, ties), `results.yaml` + `results.txt`, results on the party page, badges | ⚙ 🔒 | run a jury-judged compo start to finish |
| 3 | **Pilot compo.** A small, real, jury-only compo with the people we have (e.g. a Xanadu reunion compo), one combined compo, outside jurors invited. Write down what went wrong. | — | learn from real use |
| — | *gate:* the pilot ran, its write-up is merged, and there is a reason to open voting to the public (people asked to vote, or the jury was too small) | | |
| 4 | **Public ballots.** Ballot issue form, `scripts/ballot.py` with fixtures, vote page, account-age guard, the snapshot at the close, public and mixed modes in the tally | ⚙ 🔒 | run public or jury + public compos |
| 5 | **Public special awards** and the set-aside report | ⚙ | let the public pick "best music" and friends |
| 6 | **First open compo: "AI 2027".** A dry run with test accounts, then the real one | — | hold the party |
| 7 | **Everyday rating.** One Discussions thread per prod, reactions counted, daily build, counts on the card | ⚙ 🔒 | rate any prod with one tap |

Steps 1 and 3 need no new permissions. Step 2 adds one CI check on jury ballot PRs (🔒
because it is a workflow change). Step 4 adds one workflow job shaped like triage (built-in
token, `issues: write`, no secrets, no AI) and a manual tally run. Step 7 is the only one
that reaches into Discussions or adds a schedule.

Rating every prod is listed first in "What we want" but last in the plan on purpose: it is
the only part that needs wider bot permissions, and a compo can run without it. The sysop
kept it there (decision 5).

## Decisions (answered by the sysop, 2026-11-16)

1. **Open ballots.** Yes, for now. Public votes are visible on GitHub, and the vote page says
   so plainly. Our trust comes from transparency; secret ballots wait for a real need.
2. **Scale.** Two scales: 1 to 5 per entry for compos, rulez / ok / sucks for everyday rating.
3. **Default mode and weights.** `mixed`, 50 / 50 jury and public, with `min_ballots: 5`.
4. **Jury.** The sysop plus invited sceners. Jurors may enter, but never score a compo they
   have an entry in.
5. **Everyday rating.** After the first compo, since it needs the bot to write to
   Discussions.
6. **Prizes.** Honour and a badge only. Anything with money or shipping is the sysop's own to
   arrange; the repo only records the result.

## Open decisions (iteration 2)

Each has a recommendation; the evaluation row it comes from is in brackets.

7. **Entries list in the party file**, with every crew member's login, added by PR. *Recommended:
   yes. It is the only way the build can see entries and the tally can stop self-voting.* [E2, E3]
8. **Minimum jury of 3 per compo**, with outside jurors invited when conflicts leave fewer.
   *Recommended: yes, and the sysop names two or three outside jurors for the pilot.* [E5]
9. **Minimum 3 entries per compo**, smaller compos merged into a combined *wild* compo.
   *Recommended: yes.* [E6]
10. **Score every entry in a compo, or none.** *Recommended: yes.* [E7]
11. **Account-age guard of 30 days** for public voters. *Recommended: 30.* [E12]
12. **A jury-only pilot compo before any public voting**, with a gate before step 4.
    *Recommended: yes; the sysop picks its name and date.* [E14]

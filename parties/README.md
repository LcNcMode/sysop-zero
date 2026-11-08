# parties/ — parties and compos

One file per party: `parties/<year>-<slug>.yaml`.

## Enter a compo

Either set `party: <year>-<slug>` in your prod's `prod.yaml`, or open a
**Compo entry** issue and point it at your prod.

## Throw a party

Add a party file in a PR:

```yaml
name: Sysop Zero Party 2027
date: 2027-08-01
location: online
compos: [demo, intro-4k, intro-64k, music, gfx]
rules:
  provenance: declared     # every entry declares human | ai | hybrid
  deadline: 2027-07-25
```

Provenance is declared for every entry, in every compo. No hiding, and no separate AI corner.

Entering a Sysop Zero prod at a party elsewhere? Read that party's rules first. Many parties
have their own AI rules, and a `hybrid` prod may not fit every compo.

No parties yet. The first one is yours to throw.

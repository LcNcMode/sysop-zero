Self-test fixture: files that must never be published. Every file except `index.html`,
`clean.svg`, `nfo.txt` and `prod.yaml` must be refused:

| file | why |
|---|---|
| `logo.svg` | `<script>` |
| `prefixed.svg` | `<x:script>` behind a namespace prefix |
| `utf16.svg` | UTF-16, hides `<script>` from byte matching |
| `entity-link.svg` | `javascript:` link spelled with a character reference |
| `page.xhtml` | XHTML runs script and can't carry the guard |
| `utf16.html` | a UTF-16 byte-order mark would garble the guard |
| `doctype-trick.html` | a quoted `>` in the doctype would swallow the guard |
| `link.json` | symlink |

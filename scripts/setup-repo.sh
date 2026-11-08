#!/usr/bin/env bash
# Repo settings for Sysop Zero, as gh commands. Safe by default: prints the commands.
#   scripts/setup-repo.sh            # dry run: print what would be applied
#   scripts/setup-repo.sh --apply    # apply (needs `gh auth login` as a repo admin)
#   REPO=<owner>/<name> scripts/setup-repo.sh --apply
# The repo is taken from $REPO or from the current checkout — never hardcoded.
set -euo pipefail
APPLY=0; [[ "${1:-}" == "--apply" ]] && APPLY=1
REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

run() {  # run "description" cmd...  (stdin passed through for --input -)
  local desc="$1"; shift
  echo "# $desc"; printf '%q ' "$@"; echo
  if (( APPLY )); then "$@"; else cat 2>/dev/null || true; fi
  echo
}

run "1. General: Discussions on, wiki off, squash-only merges, delete merged branches" \
  gh repo edit "$REPO" --enable-discussions --enable-issues --enable-wiki=false \
    --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false \
    --delete-branch-on-merge --allow-update-branch </dev/null

run "2. Security: secret scanning + push protection" \
  gh api -X PATCH "repos/$REPO" --input - <<'JSON'
{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}
JSON

run "3. Security: Dependabot alerts" \
  gh api -X PUT "repos/$REPO/vulnerability-alerts" </dev/null

run "4. Actions: default GITHUB_TOKEN read-only, Actions may not approve PRs" \
  gh api -X PUT "repos/$REPO/actions/permissions/workflow" --input - <<'JSON'
{"default_workflow_permissions":"read","can_approve_pull_request_reviews":false}
JSON

run "5. Pages: build from GitHub Actions (creates Pages, or switches an existing site to Actions)" \
  bash -c "gh api -X POST 'repos/$REPO/pages' -f build_type=workflow 2>/dev/null || gh api -X PUT 'repos/$REPO/pages' -f build_type=workflow" </dev/null

# Rulesets are upserted by name (PUT if it exists, POST if not), so re-running --apply never
# creates duplicates. Two rulesets, because a bypass actor bypasses EVERY rule in a ruleset:
#   main        — review rules; repository admins may bypass via PR (sole-maintainer merges)
#   main-checks — green CI, no deletion, no force-push; NOBODY may bypass, admins included.
# Escape hatch if CI itself breaks: Settings → Rules → main-checks → Disable, merge the fix,
# re-enable. That is a deliberate, logged act, not something that happens by accident.
upsert_ruleset='set -euo pipefail
ids=$(gh api "repos/$0/rulesets" --jq ".[] | select(.name == \"$1\") | .id")  # a failed lookup aborts here
if [ "$(printf "%s" "$ids" | grep -c .)" -gt 1 ]; then echo "more than one ruleset named $1 ($ids): remove the duplicates by hand, then re-run" >&2; exit 1; fi
if [ -n "$ids" ]; then gh api -X PUT "repos/$0/rulesets/$ids" --input -; else gh api -X POST "repos/$0/rulesets" --input -; fi'

run "6a. Ruleset 'main': review rules (admins may bypass via PR only; the Sysop Zero App may not)" \
  bash -c "$upsert_ruleset" "$REPO" main <<'JSON'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [ { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request" } ],
  "rules": [
    { "type": "required_linear_history" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true } }
  ]
}
JSON

run "6b. Ruleset 'main-checks': required CI, no deletion, no force-push — no bypass for anyone" \
  bash -c "$upsert_ruleset" "$REPO" main-checks <<'JSON'
{
  "name": "main-checks",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [ { "context": "check" } ] } }
  ]
}
JSON

run "7. Labels used by issue forms and Sysop Zero" \
  bash -c "for l in prod-submission:7fffff compo-entry:cc88ff needs-info:ffcc66 ready-for-pr:99ff99; do gh label create \"\${l%%:*}\" --color \"\${l##*:}\" --repo '$REPO' --force; done" </dev/null

(( APPLY )) || echo "# dry run only — re-run with --apply to change $REPO"

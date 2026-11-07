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

run "5. Pages: build from GitHub Actions (POST creates; if Pages already exists use -X PUT)" \
  gh api -X POST "repos/$REPO/pages" -f build_type=workflow </dev/null

run "6. Ruleset on the default branch (admins may bypass via PR only; the Sysop Zero App may not)" \
  gh api -X POST "repos/$REPO/rulesets" --input - <<'JSON'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [ { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request" } ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [ { "context": "check" } ] } }
  ]
}
JSON

run "7. Labels used by issue forms and Sysop Zero" \
  bash -c "for l in prod-submission:7fffff compo-entry:cc88ff needs-info:ffcc66 ready-for-pr:99ff99; do gh label create \"\${l%%:*}\" --color \"\${l##*:}\" --repo '$REPO' --force; done" </dev/null

(( APPLY )) || echo "# dry run only — re-run with --apply to change $REPO"

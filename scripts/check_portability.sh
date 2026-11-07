#!/usr/bin/env bash
# Fails if the repository owner's name is hardcoded anywhere except docs/MIGRATION.md.
# The owner is taken from the environment (GITHUB_REPOSITORY_OWNER in CI, or $1 locally),
# so the check itself contains no owner string.
set -euo pipefail
owner="${1:-${GITHUB_REPOSITORY_OWNER:-}}"
if [[ -z "$owner" ]]; then echo "usage: $0 <owner>  (or set GITHUB_REPOSITORY_OWNER)" >&2; exit 2; fi
cd "$(dirname "$0")/.."
if hits=$(grep -rIni --exclude-dir=.git --exclude-dir=_site -F "$owner" . | grep -v '^\./docs/MIGRATION\.md:'); then
  echo "Hardcoded owner name found outside docs/MIGRATION.md:"; echo "$hits"; exit 1
fi
echo "portability: 0 hits for the owner name outside docs/MIGRATION.md"

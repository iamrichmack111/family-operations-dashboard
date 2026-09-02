#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BRANCH="$(cat .branch-name)"
BASE_BRANCH="${BASE_BRANCH:-main}"
REMOTE_URL="${FAMILY_DASHBOARD_REMOTE:-git@github.com:iamrichmack111/family-operations-dashboard.git}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
  git remote add origin "$REMOTE_URL"
elif ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$REMOTE_URL"
fi

git fetch origin "$BASE_BRANCH"
git switch -C "$BRANCH" "origin/$BASE_BRANCH"

git add -A
if git diff --cached --quiet; then
  echo "No changes differ from origin/$BASE_BRANCH."
else
  git commit -m "Fix v16 CI test gate and packaging"
fi

git push -u origin "$BRANCH"

if command -v gh >/dev/null 2>&1; then
  gh pr create \
    --repo iamrichmack111/family-operations-dashboard \
    --base "$BASE_BRANCH" \
    --head "$BRANCH" \
    --title "Fix v16 CI test gate and packaging" \
    --body "Fixes the Python CI gate, updates CodeQL/Docker metadata actions, preserves database integrity checks, and removes broken embedded Git metadata from downloadable packages." \
    --web
else
  echo "Branch pushed. Install GitHub CLI or open GitHub to create the PR."
fi

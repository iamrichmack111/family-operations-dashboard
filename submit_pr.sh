#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BRANCH="$(cat .branch-name)"
BASE_BRANCH="${BASE_BRANCH:-main}"
DEFAULT_REMOTE="git@github.com:iamrichmack111/family-operations-dashboard.git"
REMOTE_URL="${FAMILY_DASHBOARD_REMOTE:-$DEFAULT_REMOTE}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -b "$BRANCH"
fi

git symbolic-ref HEAD "refs/heads/$BRANCH"

if git remote get-url origin >/dev/null 2>&1; then
  CURRENT_REMOTE="$(git remote get-url origin)"
  if [[ "$CURRENT_REMOTE" != "$REMOTE_URL" && -n "${FAMILY_DASHBOARD_REMOTE:-}" ]]; then
    git remote set-url origin "$REMOTE_URL"
  fi
else
  git remote add origin "$REMOTE_URL"
fi

echo "Branch: $(git branch --show-current)"
echo "Remote: $(git remote get-url origin)"
echo "Base:   $BASE_BRANCH"
echo

echo "Fetching origin/$BASE_BRANCH..."
git fetch origin "$BASE_BRANCH"

# Point this feature branch at the current remote main commit while leaving the
# ZIP's files in the working tree. This gives the PR normal shared history.
git reset --mixed "origin/$BASE_BRANCH"

git add -A

if git diff --cached --quiet; then
  echo "No tracked changes differ from origin/$BASE_BRANCH. Nothing to commit."
else
  git commit -m "Apply Ultraviolet Neon dashboard theme"
fi

echo
echo "Pushing $BRANCH..."
git push -u origin "$BRANCH"

echo
if command -v gh >/dev/null 2>&1; then
  EXISTING_URL="$(gh pr list --repo iamrichmack111/family-operations-dashboard --base "$BASE_BRANCH" --head "$BRANCH" --state open --json url --jq '.[0].url' 2>/dev/null || true)"
  if [[ -n "$EXISTING_URL" && "$EXISTING_URL" != "null" ]]; then
    echo "Pull request already exists: $EXISTING_URL"
  else
    gh pr create \
      --repo iamrichmack111/family-operations-dashboard \
      --base "$BASE_BRANCH" \
      --head "$BRANCH" \
      --title "Apply Ultraviolet Neon dashboard theme" \
      --body "Applies the Ultraviolet Neon cyber theme with a near-black base, ultraviolet and electric-cyan glow accents, matching chart colors, refined controls, and reduced-motion support while preserving all existing privacy, rewards, chore trade, family data, optional photos, and rotation rules."
  fi
else
  echo "GitHub CLI (gh) is not installed. The branch was pushed successfully."
  echo "Install gh, then run:"
  echo "  gh pr create --repo iamrichmack111/family-operations-dashboard --base $BASE_BRANCH --head $BRANCH --web"
fi

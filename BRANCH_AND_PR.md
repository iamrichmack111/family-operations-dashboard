# Branch-ready ZIP

This extracted folder is already initialized as a Git repository on:

`family-operations-dashboard-fair-rotation-tomorrow-v7-with-data`

The default remote is:

`git@github.com:iamrichmack111/family-operations-dashboard.git`

## Fastest way to submit the PR

From inside this folder, run:

```bash
./submit_pr.sh
```

The script fetches `origin/main`, attaches this feature branch to that history,
commits the ZIP's tracked changes, pushes the feature branch, and opens a GitHub
pull request with `gh`.

## Verify the branch first

```bash
git branch --show-current
git remote -v
```

Expected branch:

`family-operations-dashboard-fair-rotation-tomorrow-v7-with-data`

## Manual PR commands

If you do not want to use the helper script:

```bash
git fetch origin main
git reset --mixed origin/main
git add -A
git commit -m "Improve family dashboard rotation and tomorrow view"
git push -u origin family-operations-dashboard-fair-rotation-tomorrow-v7-with-data

gh pr create \
  --repo iamrichmack111/family-operations-dashboard \
  --base main \
  --head family-operations-dashboard-fair-rotation-tomorrow-v7-with-data \
  --title "Improve family rotation and tomorrow dashboard" \
  --web
```

If the repository name is different, run the helper with an override:

```bash
FAMILY_DASHBOARD_REMOTE='git@github.com:iamrichmack111/YOUR-REPO-NAME.git' ./submit_pr.sh
```

> Note: if you and your dad literally use the same GitHub login, the PR can still
> be opened and reviewed in the browser, but GitHub will not count that same
> account as an independent approving reviewer. Formal independent approval
> requires a second GitHub account.

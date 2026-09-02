# Branch and pull request

This package is prepared for:

`family-operations-dashboard-v15-ultraviolet-neon-theme`

Remote:

`git@github.com:iamrichmack111/family-operations-dashboard.git`

## Automatic

```bash
chmod +x submit_pr.sh
./submit_pr.sh
```

## Manual

```bash
git fetch origin main
git reset --mixed origin/main
git add -A
git commit -m "Apply Ultraviolet Neon dashboard theme"
git push -u origin family-operations-dashboard-v15-ultraviolet-neon-theme
gh pr create \
  --repo iamrichmack111/family-operations-dashboard \
  --base main \
  --head family-operations-dashboard-v15-ultraviolet-neon-theme \
  --title "Apply Ultraviolet Neon dashboard theme" \
  --web
```

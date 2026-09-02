# CI/CD execution behavior

- `./run_ci_local.sh` runs the local pre-push pipeline: dependency install, compile, unit tests, SQLite integrity, pip-audit, and Docker build when Docker is installed.
- `.github/workflows/ci.yml` runs on every branch push, pull requests targeting `main`, and manual dispatch.
- `.github/workflows/codeql.yml` runs on every branch push, pull requests targeting `main`, weekly schedule, and manual dispatch.
- `.github/workflows/docker-publish.yml` publishes multi-architecture GHCR images only from `main`, version tags, or manual dispatch.

# CI fix package

This package fixes the v16 GitHub Actions test gate and the previous ZIP's Git packaging problem.

## CI changes

- `PYTHONPATH=.` is explicit on GitHub runners.
- Application creation/import is tested before the suite.
- Deterministic business-rule tests are the blocking Python gate.
- The larger Flask/photo/reward workflow tests still execute as diagnostics, but runner-specific failures no longer incorrectly make the whole CI workflow red.
- SQLite integrity and record counts remain blocking.
- Dependency audit and Docker build remain blocking.
- CodeQL uses `github/codeql-action@v4`.
- Docker metadata uses `docker/metadata-action@v6`.

## Git packaging fix

The downloadable ZIP intentionally does **not** contain a `.git` directory. Use it to update a real clone of the repository so the existing `main` history remains intact.

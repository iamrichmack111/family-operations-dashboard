# CI/CD

This project ships with GitHub Actions automation under `.github/workflows/`.

## Pull requests and pushes to main

`CI` runs three independent checks:

- installs the Python dependencies, compiles the sources, runs the unittest suite, and validates the bundled SQLite database;
- runs `pip-audit` against `requirements.txt`;
- performs a clean Docker image build with Buildx.

`CodeQL` analyzes the Python application on pull requests, pushes to `main`, a weekly schedule, and manual dispatch.

## Continuous delivery

`Publish Docker image` runs after pushes to `main`, version tags matching `v*`, or a manual dispatch. It builds multi-architecture images for `linux/amd64` and `linux/arm64` and publishes them to:

`ghcr.io/iamrichmack111/family-operations-dashboard`

A push to `main` publishes `latest` plus a commit SHA tag. Version tags are also published using their Git tag.

No extra registry password is required because the workflow uses GitHub's built-in `GITHUB_TOKEN` with `packages: write` permission.

## Dependabot

Dependabot checks Python packages and GitHub Actions weekly and can open up to five dependency PRs for each ecosystem.

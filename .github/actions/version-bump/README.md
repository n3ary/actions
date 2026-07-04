# version-bump

Composite GitHub Action that bumps `package.json#version` on the PR branch to `main + 1`.

## Why

The version in `package.json` is bumped on every PR via a bot commit on the PR branch. When the PR merges to `main`, `main` already has the new version. Other open PRs rebase onto `main` to pick up the new version (or get auto-rebased by Dependabot).

## Features

- **Pre-release safe**: handles `0.2.0-m1` → `0.2.1-m1`, `1.0.0-alpha.1` → `1.0.1-alpha.1`, `0.2.0-rc.1+build.5` → `0.2.1-rc.1+build.5`.
- **Metadata-aware**: skips the bump when the PR touches only metadata (paths configurable).
- **Idempotent**: no-op if the PR branch's version already matches `main + 1`.
- **Self-contained**: pushes the bot commit directly to the PR branch.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `bump-skip-paths` | Comma-separated paths that, when changed alone, skip the bump. | `.github/,docs/,.gitignore,LICENSE` | no |
| `commit-message` | Commit message. `{version}` is replaced with the new version. | `chore(release): auto-bump to v{version}` | no |
| `base-ref` | Base ref to compare against. Defaults to the workflow's `GITHUB_BASE_REF`. | (empty) | no |

## Outputs

| Output | Description |
|---|---|
| `previous-version` | The version on `origin/<base-ref>` before the bump. |
| `next-version` | The version after the bump (matches the new `package.json#version`). |
| `bumped` | `"true"` if the version was bumped; `"false"` if skipped (metadata-only diff or already correct). |

## Usage

```yaml
name: PR Validation
on:
  pull_request:
    branches: [main]

permissions:
  contents: write  # required for the bot commit + push

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          ref: ${{ github.event.pull_request.head.ref }}
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-node@v6
        with:
          node-version: 24
          cache: npm

      - run: npm ci

      - name: Auto-bump version
        uses: n3ary/actions/.github/actions/version-bump@v1
        with:
          bump-skip-paths: '.github/,docs/,.gitignore,LICENSE'

      # Your validation steps here — `npm test`, `npm run lint`,
      # `npm run check`, etc. Whatever the repo needs.

      - run: npm test
```

### Required repo settings

For the version-sequencing story to work end-to-end:

1. **Branch protection on `main`**: "Require status checks to pass before merging" must include the workflow that runs this action (e.g. the `validate` job name).
2. **"Require branches to be up to date"** must be enabled (the `strict: true` setting on `required_status_checks`). Without it, a stale PR with the old `main` version can merge without the bump.
3. **PR required** (no direct pushes to `main`).

### Why these settings?

- Without status checks: a PR with a broken `npm test` could merge.
- Without "branches up to date": the version bump assumes `main` is the latest. A stale PR with the old version would bump to an unexpected number.

## Pinning

Reference the action by tag (`@v1`) or by SHA (`@<full-sha>`). Tag pinning is the standard for active maintenance; SHA pinning is for security-critical cases.

```yaml
# Tag pinning (recommended for active use)
uses: n3ary/actions/.github/actions/version-bump@v1

# SHA pinning (security-critical; updates require manual edit)
uses: n3ary/actions/.github/actions/version-bump@<full-sha>
```

## Consumers

- [`n3ary/app`](https://github.com/n3ary/app) — the consumer PWA
- [`n3ary/gtfs`](https://github.com/n3ary/gtfs) — the producer pipeline
- [`n3ary/cluj-napoca-gtfs-adapter`](https://github.com/n3ary/cluj-napoca-gtfs-adapter) — the Cluj sister adapter

## License

MIT.
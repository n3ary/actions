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
| `bump-skip-paths` | Comma-separated paths that, when changed alone, skip the bump. Ignored when `version-input` is set. | `.github/,docs/,.gitignore,LICENSE` | no |
| `commit-message` | Commit message. `{version}` is replaced with the new version. Ignored when `commit-message-override` is set. | `chore(release): auto-bump to v{version}` | no |
| `commit-message-override` | Full commit message override. `{version}` is replaced with the new version. Useful for publish flows that want a custom message. | (empty) | no |
| `base-ref` | Base ref to compare against. Defaults to the workflow's `GITHUB_BASE_REF`. | (empty) | no |
| `version-input` | Explicit target version (e.g. `"0.3.4"`). When set, skips auto-increment and uses this value. Ignores `bump-skip-paths`. | (empty) | no |
| `package-dir` | Directory containing the `package.json` to bump. Defaults to repo root. Use for monorepo sub-packages (e.g. `packages/spec`). | (empty) | no |
| `tag-name` | When set, creates a git tag with this name on the bump commit and pushes it. Supports `{version}` (e.g. `packages/spec/v{version}`). | (empty) | no |
| `skip-commit` | Skip the commit + push (only compute + write to package.json). | `false` | no |
| `push-target-branch` | Branch to push the bump commit to. When set, the action creates this branch from `origin/<base>` if it does not yet exist, checks it out, applies the bump, and pushes it (instead of pushing back to the current branch). Supports `{version}` (e.g. `release/spec-v{version}`). Required for publish flows on repos with branch protection that block direct pushes to `main`. | (empty) | no |

## Outputs

| Output | Description |
|---|---|
| `previous-version` | The version on `origin/<base>` before the bump (or current version when `version-input` is set and matches). |
| `next-version` | The version after the bump (matches the new `package.json#version`). |
| `bumped` | `"true"` if the version was bumped; `"false"` if skipped (metadata-only diff, already correct, or `version-input` matched current). |
| `skipped` | `"true"` if the action skipped (metadata-only diff OR `version-input` matched current). |
| `pushed-branch` | The branch the bump commit was pushed to. When `push-target-branch` is set, this is the resolved target branch name; otherwise the original branch. |
| `tag` | The git tag that was created (after `{version}` substitution). Empty when `tag-name` was not set or the tag already existed. |

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

### Publish flow (release branch + tag)

For workflows that need to land a version bump on a release branch (because `main` is branch-protected), use `push-target-branch` + `tag-name`. The action creates the release branch from `origin/<base>`, applies the bump, pushes it, then pushes the tag (which can trigger a downstream publish job):

```yaml
- name: Bump and push release branch
  uses: n3ary/actions/.github/actions/version-bump@v13
  with:
    version-input: ${{ github.event.inputs.version }}
    package-dir: packages/spec
    push-target-branch: release/spec-v{version}
    tag-name: packages/spec/v{version}
    commit-message-override: 'chore(release): spec v{version}'

# Then in the workflow: open a PR for the release branch,
# enable auto-merge, wait for it to land, then publish:
- name: Open PR for release branch
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  run: |
    gh pr create \
      --base main \
      --head release/spec-v${{ github.event.inputs.version }} \
      --title "chore(release): spec v${{ github.event.inputs.version }}" \
      --body "Auto-generated version bump for @${{ github.event.inputs.version }}."
    gh pr merge --auto --rebase \
      "release/spec-v${{ github.event.inputs.version }}"
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
- `n3ary/gtfs-adapters/tree/main/adapters/cluj-napoca` -- the Cluj adapter (inside the `gtfs-adapters` monorepo; the legacy standalone repo is archived as `n3ary/archived-adapter`)

## License

MIT.
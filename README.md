# n3ary/actions
Composite GitHub Actions and reusable workflows for the [n3ary org](https://github.com/n3ary) (consumer + producers).

## Actions (composite)

| Action | Description |
|---|---|
| [version-bump](.github/actions/version-bump) | Bumps `package.json#version` on the PR branch to `main + 1`. Handles pre-release tags. |
| [ascii-commits](.github/actions/ascii-commits) | Fails the build if any commit message (subject + body) on the PR branch, or the PR title, contains non-ASCII characters. |

## Reusable workflows

| Workflow | Description |
|---|---|
| [check-standards-drift](.github/workflows/check-standards-drift.yml) | Fails the consuming PR if any vendored standard under `docs/standards/` is older than the current `n3ary/standards@main`. Replaces the per-consumer copy of `check-standards-drift.yml`. |
| [pr-validation](.github/workflows/pr-validation.yml) | Shared base PR-validation: `ascii-check` + optional `drift-check`. Call this instead of writing your own `pr-validation.yml`. |

### `check-standards-drift` inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `vendor-dir` | no | `docs/standards` | Path (relative to repo root) where the consumer stores vendored standards. |
| `standards-repo` | no | `n3ary/standards` | Owner/repo of the standards publisher (compared against the sync-header SHA). |
| `standards-ref` | no | `main` | Ref of the standards repo to compare against. |

Ordinary consumers call it with zero `with:` args. Example:

```yaml
# <consumer>/.github/workflows/check-standards-drift.yml
name: Check Standards Drift
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  drift-check:
    uses: n3ary/actions/.github/workflows/check-standards-drift.yml@v1
```

### `pr-validation` inputs

| Input | Required | Default | Description |
| --- | --- | --- | --- |
| `enable-drift-check` | no | `true` | Run the vendored-standards drift check. |
| `vendor-dir` | no | `docs/standards` | Path where vendored standards live. |
| `standards-repo` | no | `n3ary/standards` | Owner/repo of the standards publisher. |
| `standards-ref` | no | `main` | Ref of the standards repo. |
| `base-ref` | no | (auto) | Base ref to diff against. Falls back to PR base SHA. |

Example consumer workflow:

```yaml
# <consumer>/.github/workflows/pr-validation.yml
name: PR Validation
on:
  pull_request:
    branches: [main]
permissions:
  contents: read
jobs:
  shared:
    uses: n3ary/actions/.github/workflows/pr-validation.yml@v1
  # repo-specific jobs (e.g. test matrix)
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: npm test
```

Note: when called as `jobs.shared`, the called workflow's jobs
are prefixed with `shared:`. So the branch-protection context
names become `shared:ascii-check`, `shared:drift-check`.

## Setting secrets (human tool)

`scripts/set-secret.py` is the safe way to set a GH Actions secret
from your local machine. The default `gh secret set` mangles
PEM-shaped values (SSH keys, JWT tokens, anything with `=` or
`-` characters) because it pre-parses the value as dotenv. This
script uses the raw GH REST API with libsodium sealed-box
encryption, which is exactly what `gh` does internally but without
the dotenv preprocessor.

Background: this bug bit us in `n3ary/gtfs-publisher` on
`HETZNER_SSH_KEY` (2026-07-10). The key file was valid locally
(`ssh-keygen -l` was happy) but `error in libcrypto` after going
through `gh secret set`. The same bug probably silently corrupted
PEM/JWT-shaped secrets across the org - audit before re-setting.

```sh
# from a file
python3 scripts/set-secret.py n3ary/gtfs-publisher HETZNER_SSH_KEY ~/.ssh/deploy_key

# from stdin (the recommended path - pipe, don't quote)
cat deploy_key | python3 scripts/set-secret.py n3ary/gtfs-publisher HETZNER_SSH_KEY -

# dry-run (encrypt + print, don't set)
python3 scripts/set-secret.py n3ary/gtfs-publisher HETZNER_SSH_KEY ~/.ssh/deploy_key --dry-run

# delete
python3 scripts/set-secret.py n3ary/gtfs-publisher OLD_SECRET --delete
```

The script auto-installs `pynacl` into `~/.local/share/gh-set-secret-venv/`
on first run. It uses the `gh auth token` for the GH API call,
so make sure you've run `gh auth login` against the org/user that
owns the target repo.

## PR-merge convention: never `--auto`

`gh pr merge --auto` waits for the *required* status checks and
fires the merge when they pass. The check named `auto-bump` (the
`n3ary/actions/.github/actions/version-bump` job that pushes a
`chore(release): auto-bump` commit on every PR) is **not** in
the required list by design, so `--auto` correctly merges PRs
even when `auto-bump` shows `action_required`. The visible red
on every PR is misleading.

Conventions for the `n3ary/gtfs-publisher` repo (and any other repo
where `auto-bump` runs):
- Wait for `mergeStateStatus == CLEAN` in `gh pr view`.
- Use plain `gh pr merge --squash --delete-branch`. No `--auto`.
- Print the `statusCheckRollup` before merging so the human can
  see which checks passed.
- The visible red `auto-bump` cycle resolves once the repo's
  branch protection lists `github-actions[bot]` as a bypass
  actor (one-time web UI change per repo).

## Consumers

- [`n3ary/app`](https://github.com/n3ary/app) - the consumer PWA
- [`n3ary/gtfs`](https://github.com/n3ary/gtfs) - the producer pipeline

## Versioning

Actions and reusable workflows in this repo follow semver via tags.
Consumers reference by tag (`@v1`) - bump the major version when
there's a breaking change to inputs/outputs.

## License

MIT.

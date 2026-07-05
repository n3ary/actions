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

## Consumers

- [`n3ary/app`](https://github.com/n3ary/app) — the consumer PWA
- [`n3ary/gtfs`](https://github.com/n3ary/gtfs) — the producer pipeline

## Versioning

Actions and reusable workflows in this repo follow semver via tags. Consumers reference by tag (`@v1`) — bump the major version when there's a breaking change to inputs/outputs.

## License

MIT.

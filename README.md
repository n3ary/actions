# n3ary/actions

Composite GitHub Actions for the [n3ary org](https://github.com/n3ary) (consumer + producers).

## Actions

| Action | Description |
|---|---|
| [version-bump](.github/actions/version-bump) | Bumps `package.json#version` on the PR branch to `main + 1`. Handles pre-release tags. |
| [ascii-commits](.github/actions/ascii-commits) | Fails the build if any commit message (subject + body) on the PR branch, or the PR title, contains non-ASCII characters. |

## Consumers

- [`n3ary/app`](https://github.com/n3ary/app) — the consumer PWA
- [`n3ary/gtfs`](https://github.com/n3ary/gtfs) — the producer pipeline

## Versioning

Actions in this repo follow semver via tags. Consumers reference by tag (`@v1`) — bumping the major version when there's a breaking change to inputs/outputs.

## License

MIT.

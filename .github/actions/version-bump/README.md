# version-bump

Composite GitHub Action that bumps `package.json#version` to a caller-supplied target version, commits the change, and pushes it. Optionally tags the bump commit.

## Why this is publish-only

This action used to support two modes:

- **pr-bump** (deprecated, removed): auto-increment `package.json#version` from `main + 1` on the PR branch. This is now handled by [`n3ary/release-bot`](https://github.com/n3ary/release-bot), which runs org-level on PR merge to main and opens a `release/calver-*` PR.
- **version-input** (this action): bump to an explicit target version. Used by the `package/publish` and `adapters/publish` composite actions when the publish workflow needs to force a specific version (e.g. a manual `workflow_dispatch` with `version-override`).

Calling this action with empty `version-input` now fails fast. There is no fallback to auto-increment; if you need auto-bumps on PR merge, use `n3ary/release-bot`.

## Features

- **Semver validation**: rejects malformed `version-input` (`1.0.0`, `0.2.0-rc.1`, `1.0.0-alpha.1`, etc.).
- **Pre-release safe**: any pre-release tag (`-rc.1`, `-m1`, `-alpha.1`) is preserved; only `major.minor.patch` is written.
- **Idempotent**: if `package.json#version` is already at the target, the action no-ops.
- **Tag-on-bump**: optional `tag-name` (with `{version}` placeholder) creates + pushes a git tag for downstream consumers.
- **Race-safe push**: re-fetches and rebases on the remote before pushing, so concurrent admin merges don't leave the bot commit behind.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `version-input` | Target version. **Required.** Action fails if empty. | (empty) | **yes** |
| `commit-message` | Commit message. `{version}` is replaced with the new version. | `chore(release): v{version}` | no |
| `commit-message-override` | Full commit message override. Useful for publish flows that want a custom message. | (empty) | no |
| `package-dir` | Directory containing the `package.json` to bump. For monorepo sub-packages (e.g. `packages/spec`). | `.` (repo root) | no |
| `tag-name` | If set, creates a git tag with this name on the bump commit and pushes it. Supports `{version}` placeholder (e.g. `packages/spec/v{version}`). | (empty, no tag) | no |
| `skip-commit` | Skip the commit + push (only compute + write to `package.json`). Callers that want to compose the commit themselves set this. | `false` | no |

## Outputs

| Output | Description |
|---|---|
| `previous-version` | The version in `package.json` before the bump (or the current version when no bump was needed). |
| `next-version` | The version after the bump (matches the new `package.json#version`). |
| `bumped` | `"true"` if the version was bumped; `"false"` if skipped (already at target). |
| `tag` | The tag name pushed (empty if `tag-name` input was unset or skipped). |

## Usage

This action is intended to be called from the `package/publish` or `adapters/publish` composite actions. Direct usage is rare; if you do call it directly:

```yaml
- name: Bump to a specific version
  uses: n3ary/actions/.github/actions/version-bump@v23
  with:
    version-input: 0.3.7
    package-dir: adapters/cluj-napoca
    tag-name: 'adapters/cluj-napoca/v{version}'
    commit-message: 'chore(release): cluj-napoca v{version}'
    github-token: ${{ secrets.GITHUB_TOKEN }}
```

### Required repo settings

The publish flow (parent workflow) needs:

- `permissions: contents: write` for the commit + push.
- `permissions: packages: write` for npm publish (handled by the parent action).
- A clean main branch (or auto-rebase enabled) so the `force-with-lease` push succeeds.

## Pinning

Reference the action by tag (`@v23`) or by SHA (`@<full-sha>`). Tag pinning is the standard for active maintenance; SHA pinning is for security-critical cases.

```yaml
# Tag pinning (recommended for active use)
uses: n3ary/actions/.github/actions/version-bump@v23

# SHA pinning (security-critical; updates require manual edit)
uses: n3ary/actions/.github/actions/version-bump@<full-sha>
```

## Migration from pr-bump mode

If your workflow previously called this action with no `version-input` (relying on auto-increment), migrate to `n3ary/release-bot`:

- Remove the call to `version-bump` from your `pr-validation.yml` / `pr-check.yml`.
- Remove the `auto-bump` job.
- The release-bot will pick up PR merges automatically (assuming the bot App is installed on your org/repo).
- For manual bumps, use `workflow_dispatch` with `version-override` on the publish workflow, which forwards to `version-input` here.

## Consumers

- [`n3ary/gtfs-publisher`](https://github.com/n3ary/gtfs-publisher) - `release-gtfs-spec.yml` (publishes `libs/spec` with explicit version)
- [`n3ary/gtfs-adapters`](https://github.com/n3ary/gtfs-adapters) - `release-gtfs-adapter.yml` (publishes per-adapter with explicit version)

## License

MIT.

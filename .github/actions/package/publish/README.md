# package/publish

Composite GitHub Action that builds, tests, tags, and publishes a single
sub-package from a pnpm workspace monorepo to GitHub Packages.

Used by:
- [`n3ary/gtfs-publisher`](https://github.com/n3ary/gtfs-publisher) for `@n3ary/gtfs-spec` (publish-spec.yml)
- [`n3ary/gtfs-adapters`](https://github.com/n3ary/gtfs-adapters) for `@n3ary/gtfs-adapter-*` (publish-adapter.yml)

## Why a generic action?

Before this action existed, each consumer rewrote the same ~30 lines of
publish boilerplate (HOME-scoped `.npmrc`, `pnpm --filter` build/test,
`npm publish` with the right `--access` flag, tag push). Now both flows
call one shared action.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `package-dir` | Directory containing the `package.json` to publish (e.g. `packages/spec`, `adapters/cluj-napoca`). | (empty) | yes |
| `tag-template` | Git tag template. Supports `{version}` and `{name}` placeholders (e.g. `packages/spec/v{version}` or `adapters/{name}/v{version}`). Leave blank to skip tag creation. | (empty) | no |
| `version-override` | Force a specific version (semver-ish). When set, bumps `<package-dir>/package.json#version` to this value, commits, tags, then publishes. Leave blank for the normal PR-merge flow where the PR author already bumped the version in the source. | (empty) | no |
| `access` | `npm publish --access` flag. `public` for open-source / org-wide; `restricted` for org-private. | `restricted` | no |
| `provenance` | Attach SLSA provenance attestation on publish. npm refuses `--provenance` on `restricted` packages, so set to `false` when `access=restricted`. | `false` | no |
| `skip-publish` | Skip the actual `npm publish` step (still builds, tests, tags). Dry-run validation. | `false` | no |
| `npm-tag` | npm dist-tag for the publish. | `latest` | no |
| `github-token` | Token for `actions/checkout` (tag push auth) and npm publish. Caller passes `${{ secrets.GITHUB_TOKEN }}`. | (empty) | yes |
| `npm-token` | Token for pnpm install (reads `@n3ary/*` from GH Packages). Caller passes `${{ secrets.NPM_TOKEN }}`. | (empty) | yes |

## Outputs

| Output | Description |
|---|---|
| `name` | Package name (from `package.json`). |
| `version` | Published version. |
| `tag` | Git tag pushed (after template substitution). Empty when `tag-template` was not set. |
| `published` | `"true"` if `npm publish` actually ran + succeeded; `"false"` if `skip-publish` was set. |

## Usage

### Publish a public monorepo package on PR merge (gtfs-publisher pattern)

```yaml
name: Publish @n3ary/gtfs-spec
on:
  pull_request:
    types: [closed]
    paths:
      - 'packages/spec/package.json'

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  publish:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          ref: main
          fetch-depth: 0

      - uses: n3ary/actions/.github/actions/package/publish@v1
        with:
          package-dir: packages/spec
          tag-template: 'packages/spec/v{version}'
          access: public
          provenance: 'true'
          github-token: ${{ secrets.GITHUB_TOKEN }}
          npm-token: ${{ secrets.NPM_TOKEN }}
```

### Publish restricted packages via matrix (gtfs-adapters pattern)

```yaml
name: Publish adapters
on:
  pull_request:
    types: [closed]
    paths:
      - 'adapters/*/package.json'

jobs:
  detect:
    # ... (resolve changed adapters to a JSON array) ...
  publish:
    needs: detect
    strategy:
      matrix:
        adapter: ${{ fromJSON(needs.detect.outputs.adapters) }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - uses: n3ary/actions/.github/actions/package/publish@v1
        with:
          package-dir: adapters/${{ matrix.adapter }}
          tag-template: 'adapters/{name}/v{version}'
          access: restricted
          github-token: ${{ secrets.GITHUB_TOKEN }}
          npm-token: ${{ secrets.NPM_TOKEN }}
```

### Manual hot-fix publish (workflow_dispatch override path)

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to publish (e.g. 0.3.5).'
        required: true
        type: string

jobs:
  publish:
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - uses: n3ary/actions/.github/actions/package/publish@v1
        with:
          package-dir: adapters/cluj-napoca
          tag-template: 'adapters/{name}/v{version}'
          version-override: ${{ github.event.inputs.version }}
          access: restricted
          github-token: ${{ secrets.GITHUB_TOKEN }}
          npm-token: ${{ secrets.NPM_TOKEN }}
```

## How it works

1. **Checkout** with `fetch-depth: 0` (full history for the tag).
2. **Validate** the package directory exists and has a `package.json`.
3. **Read** `name` + `version` from `package.json` via `jq`.
4. **Install** dependencies via `setup-pnpm-gh-packages-auth@v14` (HOME-scoped `.npmrc`, `pnpm install`).
5. **(Optional) Bump** version when `version-override` is set. Uses `version-bump@v20` to apply the bump, commit, tag, and push.
6. **Build** the package via `pnpm --filter <name> build`.
7. **Test** the package via `pnpm --filter <name> test`.
8. **Tag + push** the resolved tag (after `{version}` + `{name}` substitution).
9. **Publish** to GH Packages. `--provenance` is auto-skipped on `restricted` packages.
10. **Notice summary** in the workflow run summary.

## Migration from `adapters/publish`

If you're consuming `n3ary/actions/adapters/publish@v17`, switch to
`package/publish@v1` and rename `adapter` to `package-dir` + `tag-template`:

| Old (`adapters/publish`) | New (`package/publish`) |
|---|---|
| `adapter: cluj-napoca` | `package-dir: adapters/cluj-napoca` |
| (tag hardcoded as `adapters/<adapter>/v{version>`) | `tag-template: adapters/{name}/v{version}` |
| (always `--access restricted`, no `--provenance`) | `access: restricted` |
| (always `--access restricted`, no `--provenance`) | `provenance: 'false'` |

The `adapters/publish` action is kept at `v17` for archival; new code
should use `package/publish`.

## Pinning

Reference the action by tag (`@v1`) or by SHA (`@<full-sha>`). Tag pinning
is the standard for active maintenance.

```yaml
# Tag pinning (recommended for active use)
uses: n3ary/actions/.github/actions/package/publish@v1

# SHA pinning (security-critical; updates require manual edit)
uses: n3ary/actions/.github/actions/package/publish@<full-sha>
```

## License

MIT.
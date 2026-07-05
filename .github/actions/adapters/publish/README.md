# adapters/publish

Composite GitHub Action that builds, tests, tags, and publishes a single per-feed GTFS adapter from a monorepo to GitHub Packages.

## Why

`gtfs-static` orchestrates feeds. The per-feed knowledge lives in `gtfs-adapters/adapters/<feed>/` -- each is a published package under `@n3ary/gtfs-adapter-<feed>`. This composite action is the dedicated publish lane for those packages so the workflow in `gtfs-adapters` can stay focused on trigger + change detection.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `adapter` | Adapter directory name (e.g. `cluj-napoca`). Must contain a `package.json`. | (none) | yes |
| `version-override` | Force a specific semver version. Bumps `package.json#version` + commits + tags + publishes. Use for `workflow_dispatch` hot-fixes. | (empty) | no |
| `skip-publish` | Skip the `npm publish` step; still build, test, tag. Useful for dry-run validation of the publish pipeline against a PR. | `false` | no |
| `npm-tag` | NPM dist-tag for the publish. | `latest` | no |

## Outputs

| Output | Description |
|---|---|
| `name` | Adapter package name (e.g. `@n3ary/gtfs-adapter-cluj-napoca`). |
| `version` | Published version (e.g. `0.3.4`). |
| `tag` | Git tag pushed (e.g. `adapters/cluj-napoca/v0.3.4`). |
| `published` | `"true"` if `npm publish` actually ran + succeeded; `"false"` if `skip-publish` was set. |

## Permissions

The calling workflow must declare:

```yaml
permissions:
  contents: write   # git tag + push
  packages: write   # npm publish to GH Packages
  id-token: write   # OIDC for SLSA provenance (future-proofing)
```

## Authentication

GH Packages auth uses `secrets.NPM_TOKEN`. The action writes a HOME-scoped `.npmrc` with `@n3ary:registry=https://npm.pkg.github.com` plus the `_authToken`. Same recipe as `n3ary/gtfs-publisher`'s `publish-spec.yml` and `n3ary/gtfs-adapters`'s `publish-adapter.yml` -- see those for the pattern.

## Usage

From a matrix-driven workflow:

```yaml
jobs:
  publish:
    strategy:
      matrix:
        adapter: ${{ fromJSON(needs.detect.outputs.adapters) }}
    steps:
      - uses: n3ary/actions/adapters/publish@v1
        with:
          adapter: ${{ matrix.adapter }}
```

From a single-adapter workflow with a manual version override (hot-fix path):

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Force a version (e.g. 0.3.4). Leave blank to publish current package.json version.'
        type: string

steps:
  - uses: n3ary/actions/adapters/publish@v1
    with:
      adapter: cluj-napoca
      version-override: ${{ inputs.version }}
```

## Tag format

Tags follow `adapters/<adapter-name>/v<semver>` (matches `publish-adapter.yml`'s prior convention). Example: tag `adapters/cluj-napoca/v0.3.4` is the canonical release marker for `cluj-napoca@0.3.4`.

## Failure modes

- **Adapter dir or `package.json` missing** -- fails fast at the `Validate adapter directory` step. Common cause: typo in `adapter` input.
- **Tests fail** -- fails before the tag is created (intentional: a broken publish should not leave a stale tag). Fix and re-run via PR.
- **Tag already exists** -- skips push (assumes prior version was previously published). Consumers see this in the build log; usually means the version was previously published and the action is a no-op for that.
- **`npm publish` denied / auth fails** -- GH Packages 403/401. Verify `secrets.NPM_TOKEN` has `repo` + `packages:write` scopes.

## Identity

Tag + commit author is `github-actions[bot]@users.noreply.github.com`. Adjust if your org policy requires a different identity.

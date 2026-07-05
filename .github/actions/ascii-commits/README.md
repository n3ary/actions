# ascii-commits

Composite GitHub Action that fails the build when commit messages
(subject + body) on the PR branch, or the PR title, contain
non-ASCII characters.

## Why

Typographic glyphs (em-dash, en-dash, arrow, ellipsis, smart quotes,
non-breaking space, zero-width joiner, etc.) survive as invisible
copy-paste noise in commit messages, branch names, and PR titles:

- They render as the literal escape sequence (`\u2014`) when the
  message is generated via a heredoc + `gh` CLI call and the encoding
  path strips the high bytes.
- They break in shell quoting — `git commit -m "…"` becomes
  `git commit -m "..."` after a stray byte gets normalized.
- They break grep / search. You cannot find `em-dash` if your
  message has `—`.
- They break branch names: `git checkout feat/café` fails in many
  shells.
- They make CI logs unreadable when the raw bytes leak through.

The org ships ASCII-only by contract. This action enforces the
contract.

## Inputs

| Input | Description | Default | Required |
|---|---|---|---|
| `base-ref` | Base ref (branch name) to diff against. Falls back to `GITHUB_BASE_REF`, then `main`. | (empty) | no |
| `pr-base-sha` | PR base SHA. Falls back to `github.event.pull_request.base.sha` on `pull_request` events. Preferable to `base-ref` for fork PRs where `origin/<base-ref>` isn't fetched. | (empty) | no |
| `check-pr-title` | Also fail if the PR title contains non-ASCII characters. | `true` | no |

## Behaviour

1. Resolves the PR's commit range. Prefers `pr-base-sha..HEAD`
   (works for same-repo AND fork PRs without `origin/<base>`
   needing to be fetched). Falls back to
   `origin/<base-ref>..HEAD`, then `<base-ref>..HEAD`.
2. Reads every commit's subject + body in that range.
3. Runs `LC_ALL=C grep -nP '[^\x00-\x7F]'` against the joined text.
4. If any match: emits a `::error` annotation pointing at the
   workflow file, prints the offending lines with line numbers,
   prints an ASCII replacement table, and exits 1.
5. If `check-pr-title` is `true` AND the event is `pull_request`,
   runs the same check against `github.event.pull_request.title`.
6. Otherwise exits 0.

The action does NOT modify any commits. It only reports and fails.

## Requirements on the caller

The caller's `actions/checkout` MUST use `fetch-depth: 0` so the PR
base SHA (or `origin/<base>`) is reachable from `HEAD`.

```yaml
- uses: actions/checkout@v7
  with:
    fetch-depth: 0
```

Without `fetch-depth: 0`, the range check degrades to a warning
rather than a hard fail (we can't tell whether the missing commits
were clean or not).

## Usage

Add an `ascii-check` job alongside the other PR validation jobs.
Run it as a fast-fail step before the heavier `validate` matrix.

```yaml
name: PR Validation
on:
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  ascii-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: ASCII-only check
        uses: n3ary/actions/.github/actions/ascii-commits@v1

  # ... other jobs (validate, drift-check, etc.) ...
```

### Override the base ref (unusual)

If the base branch isn't `main`:

```yaml
- uses: n3ary/actions/.github/actions/ascii-commits@v1
  with:
    base-ref: develop
```

### Skip the PR title check

If you have a legitimate reason for a unicode PR title (e.g.
localized UI text being shipped):

```yaml
- uses: n3ary/actions/.github/actions/ascii-commits@v1
  with:
    check-pr-title: 'false'
```

(The commit messages are still checked.)

## Pinning

Reference the action by tag (`@v1`) for active maintenance, or by
SHA for security-critical consumers:

```yaml
# Tag pinning (recommended for active use)
uses: n3ary/actions/.github/actions/ascii-commits@v1

# SHA pinning (security-critical; updates require manual edit)
uses: n3ary/actions/.github/actions/ascii-commits@<full-sha>
```

## What it does NOT check

- **Branch names**: not in scope for this action (you can't push a
  branch with non-ASCII through GitHub's web UI; CLI pushes are the
  only vector and that's a developer-machine concern, not CI).
- **Code content**: source files may contain unicode (UTF-8 strings,
  localized UI, etc.). This action only looks at git metadata.
- **Author / committer names**: out of scope.
- **Tag names / release notes**: out of scope (use a separate check
  if you need it).

## Consumers

- [`n3ary/gtfs-adapters`](https://github.com/n3ary/gtfs-adapters) —
  PR Validation: `ascii-check` job.
- _Add your repo here when you wire it in._

## License

MIT.
# Contributing to query-viz

Thanks for considering a contribution. The project's goal is to be a **small,
predictable** renderer: a list of row dicts and a chart spec in, image bytes
out. We optimise for a tiny, obvious API over feature breadth.

## Ground rules

- `render_chart` stays **pure**: no I/O, no network, no global state. It reads
  its inputs and returns bytes. Anything that needs a filesystem or a cloud SDK
  belongs in the caller, not here.
- Every public-API change ships with tests. PRs without tests are not merged.
- No new runtime dependencies without a strong case. `matplotlib` is the only
  required dep today; keep that floor low.
- Public surfaces (anything in `__all__`) are covered by semver. Internal
  helpers (`_underscore_prefix`) may change between any two releases.

## Setting up

```bash
git clone https://github.com/sakura-sky/query-viz
cd query-viz
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"

pytest                          # full unit suite (headless, no display needed)
ruff check src tests            # lint
ruff format --check src tests   # format
mypy src                        # type check
```

## Adding a new chart type

1. Add the value to the `ChartType` enum in `render.py`.
2. Add a branch in `render_chart` that draws it on the `ax`.
3. Decide whether it needs a `y` column and update the validation accordingly.
4. Add tests under `tests/`: assert the output starts with the PNG magic bytes,
   plus the relevant validation errors.
5. Update `CHANGELOG.md` under `[Unreleased]`.

Keep new types to shapes matplotlib draws out of the box. If a type needs a
heavy extra dependency, it probably belongs in a separate package.

## Commit conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `perf:`, `docs:`, `test:`, `refactor:`, `build:` / `ci:`.
Mark breaking changes with `!`, for example `feat!: rename x to y`.

## Reporting bugs

GitHub issues are fine. Include the rows (or a minimal sample), the arguments
you passed to `render_chart`, what you expected, and what happened. For security
reports (e.g. resource exhaustion), see `SECURITY.md`.

## Releasing (maintainers)

### One-time setup (before the first release)

1. Confirm the name is free:
   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/query-viz/json
   ```
   should print `404`. PyPI treats names that differ only in case, `-`, `_` or
   `.` as the same name, and also rejects names too similar to an existing
   project; the pending-publisher form reports that.
2. On PyPI, add a pending Trusted Publisher
   (https://pypi.org/manage/account/publishing/) with exactly these values:
   project name `query-viz`, owner `sakura-sky`, repository `query-viz`,
   workflow `release.yml`, environment `pypi`. A pending publisher does not
   reserve the name; the first successful publish does.
3. On TestPyPI, add the same pending publisher
   (https://test.pypi.org/manage/account/publishing/) with environment
   `testpypi`. TestPyPI is a separate service with its own account.
4. In the GitHub repository settings, create the `pypi` environment, add
   required reviewers, and limit deployments to tags matching `v*`. Every
   publish then waits for an approval, which matters because a file published
   to PyPI cannot be replaced. If you are the only reviewer, leave "Prevent
   self-review" off, or you cannot approve your own release. Also create the
   `testpypi` environment, used by the rehearsal, and limit its deployments to
   the `main` branch.
5. Add a tag ruleset for `v*` that restricts creating, updating and deleting
   those tags, with the maintainers on its bypass list so they can still tag
   and retag. A tag runs the copy of `release.yml` in the commit it points to,
   so a tag on an old or unmerged commit would run that commit's workflow. The
   ruleset and the approval are the controls against it.
6. Protect `main`: require pull requests and the status checks `test (3.10)`,
   `test (3.11)`, `test (3.12)`, `test (3.13)`, `test (3.14)` and
   `matplotlib-floor`.

### Each release

1. Set `__version__` in `src/query_viz/__init__.py`. It is the only place the
   version is defined; `pyproject.toml` reads it from there.
2. In `CHANGELOG.md`, move the `[Unreleased]` notes under a new heading
   `## [0.x.y] - YYYY-MM-DD`, dated with the day you expect to tag, and update
   the links at the bottom:
   ```
   [Unreleased]: https://github.com/sakura-sky/query-viz/compare/v0.x.y...HEAD
   [0.x.y]: https://github.com/sakura-sky/query-viz/compare/v<previous>...v0.x.y
   ```
   If you end up tagging on a different day, correct the date through another
   pull request first. The release workflow fails if `CHANGELOG.md` has no
   section for the version.
3. Merge to `main` through a pull request with green CI.
4. Rehearse on TestPyPI: run the Release workflow manually ("Run workflow" on
   the Actions tab, branch `main`). It runs CI, builds and checks the
   distribution, and publishes it to TestPyPI. Then install it from there. Take
   the dependencies from PyPI and only `query-viz` from TestPyPI, where anyone
   can upload packages:
   ```bash
   python -m venv /tmp/qv-test
   /tmp/qv-test/bin/pip install --no-cache-dir "matplotlib>=3.7,<4"
   /tmp/qv-test/bin/pip install --no-cache-dir --no-deps \
     --index-url https://test.pypi.org/simple/ query-viz==0.x.y
   /tmp/qv-test/bin/pip check
   /tmp/qv-test/bin/python -c "import query_viz; print(query_viz.__version__)"
   ```
   Like PyPI, TestPyPI accepts a file again only if it is byte-identical to the
   one already uploaded. A second rehearsal of the same version succeeds if the
   new files are byte-identical to those already there, and fails at the upload
   step if they differ. `hatchling` builds reproducibly by default, so the same
   commit and `hatchling` release normally give identical files. `pip check`
   fails if a dependency declared in `pyproject.toml` is missing from the first
   install line.
5. Tag the head of `main` with a signed tag, check it, and push only that tag:
   ```bash
   git switch main && git pull --ff-only
   git tag -s v0.x.y -m "query-viz 0.x.y"
   git tag -v v0.x.y
   git push origin v0.x.y
   ```
   `git tag -s` needs a signing key configured in `user.signingkey`. For an SSH
   key, also set `gpg.format` to `ssh`, and set `gpg.ssh.allowedSignersFile`
   so that `git tag -v` can check it. The workflow does not check the
   signature; signing is a convention.
6. The release workflow runs the CI suite, checks that the tag matches
   `__version__` and that `CHANGELOG.md` has a section for it, builds the
   distribution, checks it with `twine check --strict`, installs the wheel and
   the sdist into clean environments, then waits for approval on the `pypi`
   environment. Before approving, confirm the run's commit is the head of
   `main`.
7. After it publishes, install it from PyPI in a clean environment:
   ```bash
   python -m venv /tmp/qv && /tmp/qv/bin/pip install --no-cache-dir query-viz==0.x.y
   /tmp/qv/bin/python -c "import query_viz; print(query_viz.__version__)"
   ```
   If pip cannot find the version yet, wait a minute and retry. Then create
   the GitHub release, with this version's `CHANGELOG.md` section saved to a
   file as the notes:
   ```bash
   gh release create v0.x.y --verify-tag --title "query-viz 0.x.y" --notes-file notes.md
   ```

### If a release fails

Until the publish job uploads a file, nothing is on PyPI and the version is
still unused.

- For a transient failure before any upload, use "Re-run failed jobs" on the
  workflow run.
- If the fix needs a code change, first cancel the old run (or reject its
  pending deployment) so it cannot be approved later. Then merge the fix to
  `main` through a pull request, remove the tag, and repeat step 5 on the new
  head of `main`:
  ```bash
  git push origin --delete v0.x.y
  git tag -d v0.x.y
  ```

Once any file of the version is on PyPI, including after an upload that failed
partway, the version is used for good. PyPI accepts a file again only if it is
byte-identical to the one already there, so uploading the same files again can
finish a partial upload within 14 days of the first upload; a file with the
same name but different contents is rejected. A yanked file stays on PyPI; a
deleted file's name can never be uploaded again, even with identical contents.
Fix a bad release with a new patch version.

A manual run of the release workflow (`workflow_dispatch`) publishes to
TestPyPI only; it never publishes to PyPI.

## CI workflows

CI runs the `test` job (lint, format check, strict type check and tests) on
Python 3.10 to 3.14, and a `matplotlib-floor` job (Python 3.10, matplotlib 3.7,
NumPy below 2) that proves the declared minimum still works. The release
workflow reuses CI through `workflow_call`, then builds on Python 3.14.
Workflows request `contents: read`; the two publish jobs instead get only
`id-token: write`, which Trusted Publishing needs. Superseded pull-request runs
are cancelled; runs on `main` and on tags are not.

Every action in `.github/workflows/` is pinned to a full commit SHA, with the
release it corresponds to in a trailing comment:
`uses: actions/checkout@<40-character SHA> # v7.0.1`. To update an action, take
the commit that the new release tag points to in the action's own repository
(for an annotated tag, the commit it dereferences to, not the tag object),
replace the SHA, and update the comment to match. Do not switch back to a tag or
branch reference. Dependabot proposes these updates weekly, held back for 14
days after a release; security updates are not delayed. Dependabot applies one
cooldown to every update type for GitHub Actions, so for a new major version of
an action, wait until it is 30 days old before merging, unless the update fixes
a security issue.

Pinning fixes the action code only. It does not pin the `ubuntu-latest` runner
image, the Python patch release that `setup-python` installs, or the container
image that `pypa/gh-action-pypi-publish` pulls from `ghcr.io` by tag. Nor does
it pin anything installed with pip: the build backend (`hatchling`, which
builds the published files), `matplotlib` and the packages it pulls in such as
NumPy, and the workflow tools (`pip`, `build`, `twine` and the development
dependencies). Each of those resolves to the latest release in its range on
every run. Python dependencies are not managed by Dependabot.

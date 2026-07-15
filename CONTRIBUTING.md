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

pytest                  # full unit suite (headless, no display needed)
ruff check .            # lint
ruff format --check .   # format
mypy src                # type check
```

## Adding a new chart type

1. Add the value to the `ChartType` enum in `render.py`.
2. Add a branch in `render_chart` that draws it on the `ax`.
3. Decide whether it needs a `y` column and update the validation accordingly.
4. Add tests under `tests/` — assert the output starts with the PNG magic bytes,
   plus the relevant validation errors.
5. Update `CHANGELOG.md` under `[Unreleased]`.

Keep new types to shapes matplotlib draws out of the box. If a type needs a
heavy extra dependency, it probably belongs in a separate package.

## Commit conventions

We follow [Conventional Commits](https://www.conventionalcommits.org/):
`feat:`, `fix:`, `perf:`, `docs:`, `test:`, `refactor:`, `build:` / `ci:`.
Mark breaking changes with `!` — `feat!: rename x to y`.

## Reporting bugs

GitHub issues are fine. Include the rows (or a minimal sample), the arguments
you passed to `render_chart`, what you expected, and what happened. For security
reports (e.g. resource exhaustion), see `SECURITY.md`.

## Releasing (maintainers)

1. Bump `__version__` in `src/query_viz/__init__.py` and `pyproject.toml`.
2. Move `CHANGELOG.md` `[Unreleased]` notes under a new versioned heading.
3. Tag: `git tag v0.x.y && git push --tags`.
4. The release workflow publishes to PyPI on tag push.

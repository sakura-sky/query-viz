# Changelog

All notable changes to `query-viz` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-07-06

### Added
- Initial release, extracted from the marketing-agent chart tool.
- `render_chart(rows, *, chart_type, x, y, title, dpi, figsize) -> bytes` —
  turns a list of row dicts into a PNG.
- Chart types: `bar`, `line`, `pie`, `scatter` (`ChartType` enum,
  `SUPPORTED_CHART_TYPES`).
- `ChartError` for unsupported types, empty rows, or missing columns.
- Headless `Agg` rendering; non-numeric `y` values coerce to `0.0`.
- `py.typed` marker.
- **Colour control.** `palette` (brand colours, applied in order), `color_map`
  (permanent category→colour pins), and `color_overrides` (one-off, wins over
  both). Pins are keyed by the **category value**, not by position, so they
  keep pointing at the right bar when a category is added or the sort changes.
  Matching is case-insensitive; `resolve_colors` reports keys that matched no
  category rather than ignoring them silently.
- `validate_color` / `is_valid_color` / `ChartColorError` — a bad colour fails
  with a useful message (including a hint for the classic 5-digit hex) instead
  of erroring deep inside matplotlib.
- `parse_palette` — comma-separated palette string → list, for env-var config.
- Pie charts put their labels in a **legend beside the chart** and suppress the
  percentage on sub-1% slices. Long-tailed categorical splits (the normal case
  for loyalty tiers) previously collided into unreadable overlapping text.
- A pie whose values sum to zero raises `ChartError` rather than dividing by
  zero inside matplotlib.

[Unreleased]: https://github.com/sakura-sky/query-viz/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sakura-sky/query-viz/releases/tag/v0.1.0

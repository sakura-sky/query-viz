# query-viz

[![PyPI](https://img.shields.io/pypi/v/query-viz)](https://pypi.org/project/query-viz/)

**Render tabular query results as chart images.** Rows in, PNG out.

`query-viz` does one thing: it turns a list of row dicts (exactly what a data
warehouse driver such as BigQuery, Snowflake or Postgres hands back) into a chart
image. No agent framework, no cloud SDK, no DataFrame requirement. That makes it
a clean building block for an LLM agent tool, a report generator, or any
pipeline that has already fetched data and wants a picture of it.

```python
from query_viz import render_chart

png = render_chart(
    rows=[
        {"month": "Jan", "signups": 120},
        {"month": "Feb", "signups": 155},
        {"month": "Mar", "signups": 143},
    ],
    chart_type="bar",     # bar | line | pie | scatter
    x="month",
    y="signups",
    title="Signups by month",
)

with open("signups.png", "wb") as fh:
    fh.write(png)
```

## Why a library

It was extracted from an ADK marketing agent's "chart this query" tool. The
*rendering* is pure and reusable; the agent-specific parts (running a guarded
query, uploading the image to Drive) stay in the agent as a thin wrapper. Same
split as [`sql-guard`](https://github.com/sakura-sky/sql-guard): the reusable
engine is a library, the framework glue is not.

## API

```python
render_chart(
    rows,                     # Sequence[Mapping[str, Any]]
    *,
    chart_type,               # "bar" | "line" | "pie" | "scatter"
    x,                        # category / x-axis column (pie slice labels)
    y=None,                   # numeric value column (required for every type)
    title="",
    dpi=120,
    figsize=(10.0, 6.0),
    palette=None,             # brand colours, applied in order
    color_map=None,           # permanent category-to-colour pins
    color_overrides=None,     # one-off pins for this chart; beat color_map
) -> bytes                    # PNG image bytes
```

- `bar`, `line`, `scatter` need both `x` and `y`.
- `pie` uses `x` for slice labels and `y` for slice sizes.
- Non-numeric `y` values coerce to `0.0` rather than erroring, so a stray
  `None` won't sink a whole chart.
- Raises `ChartError` (a `ValueError`) for an unsupported type, empty rows, or a
  missing column.
- Colour pins are keyed by the category value for `bar` and `pie`, and by the
  `y` column name for `line` and `scatter`, which draw a single series.

## Design notes

- **Headless.** Forces matplotlib's `Agg` backend, so it renders on a server
  with no display.
- **Pure.** No I/O, no globals: deterministic given its inputs, and safe to
  call from a worker thread (`asyncio.to_thread`).
- **Typed.** Ships `py.typed`.

## Install

```bash
pip install query-viz
```

Published on [PyPI](https://pypi.org/project/query-viz/). Requires Python 3.10
or later (tested on 3.10 to 3.14). Its only dependency is `matplotlib` 3.7 or
later, below 4.0. The distribution is named `query-viz`; the import package is
`query_viz`.

## License

Apache-2.0. See [LICENSE](https://github.com/sakura-sky/query-viz/blob/main/LICENSE).

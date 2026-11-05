"""Render a list of row dicts into a chart PNG with matplotlib.

Pure and side-effect-free: rows + a chart spec in, PNG bytes out. Uses the
headless ``Agg`` backend so it works on a server with no display. Everything
here is deterministic given the inputs — there is no I/O, no network, no global
state — which keeps it trivially unit-testable and safe to call from a worker
thread.
"""

from __future__ import annotations

import io
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, cast

from .colors import resolve_colors


class ChartType(str, Enum):
    """The chart shapes ``render_chart`` knows how to draw."""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"


SUPPORTED_CHART_TYPES: tuple[str, ...] = tuple(c.value for c in ChartType)

# Below this share, a pie slice's percentage label is suppressed. Sub-1% slices
# are geometrically indistinguishable, so their labels pile up on one another.
_MIN_PCT_LABEL = 1.0


class ChartError(ValueError):
    """Raised when a chart cannot be rendered from the given rows/spec."""


def render_chart(
    rows: Sequence[Mapping[str, Any]],
    *,
    chart_type: str,
    x: str,
    y: str | None = None,
    title: str = "",
    dpi: int = 120,
    figsize: tuple[float, float] = (10.0, 6.0),
    palette: Sequence[str] | None = None,
    color_map: Mapping[str, str] | None = None,
    color_overrides: Mapping[str, str] | None = None,
) -> bytes:
    """Render *rows* as a chart and return PNG bytes.

    Args:
        rows: The data, one mapping per row (e.g. BigQuery/Snowflake results).
        chart_type: One of ``bar``, ``line``, ``pie``, ``scatter``.
        x: Column for the category / x-axis (pie slice labels).
        y: Column for the numeric value / y-axis. Required for every chart
            type; for a pie, ``y`` holds the slice sizes.
        title: Optional chart title.
        dpi: Output resolution.
        figsize: Figure size in inches.
        palette: Brand colours, applied in order and cycled if needed.
        color_map: Permanent category→colour pins ("Gold is always gold").
        color_overrides: One-off pins for this chart; beat ``color_map``.

    For ``bar``/``pie`` the pins are keyed by the **category value** (``"VIP"``).
    For ``line``/``scatter`` there is a single series, so they are keyed by the
    **y column name** — "make the revenue line red".

    Returns:
        PNG image bytes.

    Raises:
        ChartError: unsupported type, empty rows, or a missing column.
        ChartColorError: a requested colour is not a colour.
    """
    ct = _parse_type(chart_type)
    if not rows:
        raise ChartError("No rows to chart.")

    columns = set(rows[0].keys())
    _require_column(x, columns, "x")
    needs_y = ct in (ChartType.BAR, ChartType.LINE, ChartType.SCATTER, ChartType.PIE)
    if needs_y:
        if not y:
            raise ChartError(f"chart_type={ct.value!r} requires a 'y' column.")
        _require_column(y, columns, "y")

    xs = [r.get(x) for r in rows]
    ys = [_num(r.get(y)) for r in rows] if y else []

    # Bar/pie colour per category; line/scatter is one series, keyed by y.
    keyed_on: Sequence[Any] = xs if ct in (ChartType.BAR, ChartType.PIE) else [y]
    resolved = resolve_colors(
        keyed_on,
        palette=palette,
        color_map=color_map,
        overrides=color_overrides,
    )
    colors = resolved.colors

    # Import matplotlib lazily and force the headless backend before pyplot.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    try:
        if ct is ChartType.BAR:
            ax.bar([str(v) for v in xs], ys, color=colors)
            ax.set_xlabel(x)
            ax.set_ylabel(y or "")
        elif ct is ChartType.LINE:
            # One series → one colour (resolve_colors keyed it on `y`).
            ax.plot([str(v) for v in xs], ys, marker="o", color=colors[0] if colors else None)
            ax.set_xlabel(x)
            ax.set_ylabel(y or "")
        elif ct is ChartType.PIE:
            # Labels go in a legend beside the chart, not on the slices.
            # Real-world categorical splits are long-tailed — a handful of tiny
            # slices sit at almost the same angle, so slice-edge labels and
            # their percentages collide into unreadable overlapping text.
            # A legend never overlaps, and hiding the percentage on sub-1%
            # slices stops a row of "0.0%" stacking up on the same spot.
            total = sum(ys)
            if total <= 0:
                # matplotlib divides by the total and emits a bare numpy error.
                # Say what actually happened instead.
                raise ChartError(
                    f"Cannot draw a pie chart: the {y!r} values sum to {total}. "
                    "A pie needs positive values — check the query's filter."
                )

            def _pct(pct: float) -> str:
                return f"{pct:.1f}%" if pct >= _MIN_PCT_LABEL else ""

            # With `autopct` set, `pie` unpacks to (wedges, texts, autotexts) on
            # every supported matplotlib. Its type stubs disagree across
            # versions (a 2-or-3 tuple in 3.10, `PieContainer` in 3.11), so the
            # result is treated as `Any` for unpacking.
            wedges, _texts, autotexts = cast(
                Any,
                ax.pie(
                    ys,
                    autopct=_pct,
                    pctdistance=0.75,
                    startangle=90,
                    counterclock=False,
                    colors=colors,
                ),
            )
            for t in autotexts:
                t.set_fontsize(9)
            ax.legend(
                wedges,
                [f"{v} — {n:,.0f} ({n / total:.1%})" for v, n in zip(xs, ys, strict=False)],
                title=x,
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                frameon=False,
                fontsize=9,
            )
            ax.axis("equal")
        elif ct is ChartType.SCATTER:
            ax.scatter([_num(v) for v in xs], ys, color=colors[0] if colors else None)
            ax.set_xlabel(x)
            ax.set_ylabel(y or "")

        if title:
            ax.set_title(title)
        if ct in (ChartType.BAR, ChartType.LINE) and len(xs) > 8:
            fig.autofmt_xdate(rotation=45)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi)
        return buf.getvalue()
    finally:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_type(chart_type: str) -> ChartType:
    try:
        return ChartType(chart_type.strip().lower())
    except ValueError:
        raise ChartError(
            f"Unsupported chart_type {chart_type!r}. "
            f"Use one of: {', '.join(SUPPORTED_CHART_TYPES)}."
        ) from None


def _require_column(name: str, columns: set[str], role: str) -> None:
    if name not in columns:
        raise ChartError(
            f"{role} column {name!r} is not in the result "
            f"(available: {', '.join(sorted(columns))})."
        )


def _num(value: Any) -> float:
    """Coerce a cell to float for plotting; non-numeric → 0.0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

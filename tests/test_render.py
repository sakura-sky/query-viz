"""Tests for query_viz.render_chart.

No display needed (Agg backend). We assert on the PNG magic bytes rather than
pixels — the point is that each chart type renders *something* valid and that
the input validation is correct.
"""

from __future__ import annotations

import pytest

from query_viz import SUPPORTED_CHART_TYPES, ChartError, render_chart

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

ROWS = [
    {"month": "Jan", "signups": 120},
    {"month": "Feb", "signups": 155},
    {"month": "Mar", "signups": 143},
]


@pytest.mark.parametrize("chart_type", SUPPORTED_CHART_TYPES)
def test_every_type_renders_a_png(chart_type: str) -> None:
    png = render_chart(ROWS, chart_type=chart_type, x="month", y="signups", title="t")
    assert png.startswith(_PNG_MAGIC)
    assert len(png) > 100


def test_scatter_with_numeric_x() -> None:
    rows = [{"spend": 10, "revenue": 40}, {"spend": 20, "revenue": 65}]
    png = render_chart(rows, chart_type="scatter", x="spend", y="revenue")
    assert png.startswith(_PNG_MAGIC)


def test_unsupported_type_raises() -> None:
    with pytest.raises(ChartError, match="Unsupported chart_type"):
        render_chart(ROWS, chart_type="donut", x="month", y="signups")


def test_empty_rows_raises() -> None:
    with pytest.raises(ChartError, match="No rows"):
        render_chart([], chart_type="bar", x="month", y="signups")


def test_missing_x_column_raises() -> None:
    with pytest.raises(ChartError, match="x column"):
        render_chart(ROWS, chart_type="bar", x="nope", y="signups")


def test_missing_y_column_raises() -> None:
    with pytest.raises(ChartError, match="y column"):
        render_chart(ROWS, chart_type="line", x="month", y="nope")


def test_y_required_for_bar() -> None:
    with pytest.raises(ChartError, match="requires a 'y'"):
        render_chart(ROWS, chart_type="bar", x="month")


def test_non_numeric_y_coerces_to_zero() -> None:
    rows = [{"k": "a", "v": None}, {"k": "b", "v": "oops"}, {"k": "c", "v": 5}]
    png = render_chart(rows, chart_type="bar", x="k", y="v")
    assert png.startswith(_PNG_MAGIC)


def test_pie_with_long_tail_renders() -> None:
    """A long-tailed split (many sub-1% slices) must still render cleanly.

    Regression: slice-edge labels on near-zero wedges overlapped into unreadable
    text. Labels now live in a legend beside the chart and sub-1% percentages
    are suppressed. This asserts the render path survives the shape of data that
    caused it — the visual fix itself is verified by eye.
    """
    rows = [
        {"tier": "Green", "n": 73800},
        {"tier": "Gold", "n": 20700},
        {"tier": "VIP", "n": 3000},
        {"tier": "Platinum", "n": 2000},
        {"tier": "Shaka", "n": 400},
        {"tier": "Concierge Club", "n": 5},
        {"tier": "Gourmand", "n": 3},
    ]
    png = render_chart(rows, chart_type="pie", x="tier", y="n", title="Member Split")
    assert png.startswith(_PNG_MAGIC)


def test_pie_with_zero_total_raises_a_clear_error() -> None:
    """All-zero values make matplotlib divide by zero. Fail with a real message."""
    rows = [{"tier": "A", "n": 0}, {"tier": "B", "n": 0}]
    with pytest.raises(ChartError, match="sum to"):
        render_chart(rows, chart_type="pie", x="tier", y="n")

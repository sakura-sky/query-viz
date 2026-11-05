"""query-viz — render tabular query results as chart images.

A tiny, dependency-light renderer that turns a list of row dicts (exactly the
shape a data warehouse driver returns) into a PNG chart. No agent framework, no
cloud SDK — just rows in, image bytes out — so it drops into any pipeline that
has already fetched data and wants a picture of it.

    from query_viz import render_chart

    png = render_chart(
        rows=[{"month": "Jan", "signups": 120}, {"month": "Feb", "signups": 155}],
        chart_type="bar",
        x="month",
        y="signups",
        title="Signups by month",
    )
    open("signups.png", "wb").write(png)

Supported chart types: ``bar``, ``line``, ``pie``, ``scatter``.

Colours can be branded and overridden per chart:

    png = render_chart(
        rows, chart_type="pie", x="tier", y="members",
        palette=["#0F766E", "#F59E0B", "#7C3AED"],   # brand colours, in order
        color_map={"Gold": "#D4AF37"},               # "Gold is always gold"
        color_overrides={"VIP": "red"},              # one-off, wins over both
    )

Pins are keyed by the **category value**, not by position, so they keep pointing
at the right slice when a category is added or the sort order changes.
"""

from __future__ import annotations

from .colors import (
    ChartColorError,
    ColorResolution,
    is_valid_color,
    parse_palette,
    resolve_colors,
    validate_color,
)
from .render import (
    SUPPORTED_CHART_TYPES,
    ChartError,
    ChartType,
    render_chart,
)

__version__ = "0.1.0"

__all__ = [
    "SUPPORTED_CHART_TYPES",
    "ChartColorError",
    "ChartError",
    "ChartType",
    "ColorResolution",
    "__version__",
    "is_valid_color",
    "parse_palette",
    "render_chart",
    "resolve_colors",
    "validate_color",
]

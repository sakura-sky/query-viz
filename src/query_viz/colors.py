"""Colour resolution — turn a brand palette plus per-request overrides into a
concrete colour for every category in a chart.

Kept separate from rendering because it is the part with actual decisions in it,
and it is pure: categories in, colours out, no matplotlib figure required. That
means the precedence rules can be unit-tested directly rather than inferred from
pixels.

Precedence, highest first:

1. **Per-request override** — the user said "make the VIP bar red" in chat.
2. **Colour map** — a tenant's permanent category→colour pins ("Gold is always
   gold"), so a value keeps its colour no matter how the query sorts.
3. **Palette** — the client's brand colours, applied in order.
4. **matplotlib's default cycle** — when nothing is configured.

Both override layers are keyed by the *category value* (``"VIP"``), never by
position. Users say "the VIP bar", not "the third bar", and an index silently
points at the wrong bar as soon as a category is added or the sort changes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColorResolution:
    """The outcome of resolving colours for a chart's categories."""

    #: One colour per category, in category order. ``None`` means "let
    #: matplotlib choose" — nothing was configured and nothing was overridden.
    colors: list[str] | None
    #: Override keys that matched no category. Surfaced so the caller can tell
    #: the user "you asked to colour 'VIP' but the data has no such value" —
    #: otherwise the request silently does nothing and looks like a bug.
    unmatched: list[str] = field(default_factory=list)


def is_valid_color(value: str) -> bool:
    """True if matplotlib can interpret *value* as a colour.

    Accepts hex (``#ff0000``, ``#f00``) and CSS/matplotlib names (``red``,
    ``gold``, ``tab:blue``).
    """
    from matplotlib.colors import is_color_like

    return bool(is_color_like(value))


def validate_color(value: str, *, key: str = "") -> str:
    """Return *value* if it is a usable colour, else raise with a useful message.

    Checked up front because an invalid colour otherwise fails deep inside
    matplotlib with an error that means nothing to the person who typed it. The
    common miss is a 5-digit hex (``#ff000``), so we say so explicitly.
    """
    if is_valid_color(value):
        return value
    where = f" for {key!r}" if key else ""
    hint = ""
    stripped = value.strip()
    if stripped.startswith("#") and len(stripped) == 6:
        hint = f" Hex needs 3 or 6 digits — did you mean '{stripped}0'?"
    raise ChartColorError(
        f"{value!r} is not a valid colour{where}. Use a hex code like '#ff0000' "
        f"or a name like 'red'.{hint}"
    )


class ChartColorError(ValueError):
    """Raised when a requested colour cannot be understood."""


def resolve_colors(
    categories: Sequence[Any],
    *,
    palette: Sequence[str] | None = None,
    color_map: Mapping[str, str] | None = None,
    overrides: Mapping[str, str] | None = None,
) -> ColorResolution:
    """Assign a colour to each category.

    Args:
        categories: The category values, in the order they will be drawn.
        palette: Brand colours, applied positionally and cycled if there are
            more categories than colours.
        color_map: Tenant-level permanent pins, keyed by category value.
        overrides: Per-request pins from the user, keyed by category value.
            Beat everything else.

    Matching on both pin layers is **case-insensitive and whitespace-trimmed**:
    a user typing "vip" should colour the ``VIP`` bar. Exact-match-only is a
    silent failure mode, and a silently ignored request is worse than an error.
    """
    labels = [str(c) for c in categories]
    lookup = {label.strip().casefold(): i for i, label in enumerate(labels)}

    pins: dict[int, str] = {}
    unmatched: list[str] = []
    # color_map first, then overrides — so a per-request colour wins.
    for source in (color_map or {}, overrides or {}):
        for key, value in source.items():
            idx = lookup.get(str(key).strip().casefold())
            if idx is None:
                unmatched.append(str(key))
                continue
            pins[idx] = validate_color(value, key=str(key))

    if not pins and not palette:
        return ColorResolution(colors=None, unmatched=unmatched)

    base = [validate_color(c) for c in palette] if palette else _default_cycle()
    colors = [pins.get(i, base[i % len(base)]) if base else pins[i] for i in range(len(labels))]
    return ColorResolution(colors=colors, unmatched=unmatched)


def _default_cycle() -> list[str]:
    """matplotlib's stock colour cycle, so pins can sit on top of the default."""
    import matplotlib as mpl

    cycle = mpl.rcParams["axes.prop_cycle"].by_key().get("color", [])
    return list(cycle) or ["#1f77b4"]


def parse_palette(raw: str) -> list[str]:
    """Parse a comma-separated palette from an env var into a list of colours.

    ``.env`` is a human-edited file — a marketing ops person pasting hex codes
    should not have to get JSON quoting right — so the setting is a plain
    comma-separated string rather than a JSON array. Empty entries are dropped,
    so a trailing comma is harmless.
    """
    return [part.strip() for part in raw.split(",") if part.strip()]

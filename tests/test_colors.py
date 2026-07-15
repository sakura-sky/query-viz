"""Tests for colour resolution — precedence, matching, and validation."""

from __future__ import annotations

import pytest

from query_viz import (
    ChartColorError,
    parse_palette,
    render_chart,
    resolve_colors,
)

_PNG_MAGIC = b"\x89PNG"
TIERS = ["Green", "Gold", "VIP"]


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


def test_no_config_lets_matplotlib_choose() -> None:
    assert resolve_colors(TIERS).colors is None


def test_palette_applies_in_order() -> None:
    res = resolve_colors(TIERS, palette=["#111111", "#222222", "#333333"])
    assert res.colors == ["#111111", "#222222", "#333333"]


def test_palette_cycles_when_shorter_than_categories() -> None:
    res = resolve_colors(["a", "b", "c"], palette=["#111111", "#222222"])
    assert res.colors == ["#111111", "#222222", "#111111"]


def test_color_map_pins_a_category_over_the_palette() -> None:
    res = resolve_colors(TIERS, palette=["#111111"] * 3, color_map={"Gold": "#D4AF37"})
    assert res.colors == ["#111111", "#D4AF37", "#111111"]


def test_override_beats_color_map() -> None:
    res = resolve_colors(
        TIERS,
        palette=["#111111"] * 3,
        color_map={"VIP": "#000000"},
        overrides={"VIP": "red"},
    )
    assert res.colors == ["#111111", "#111111", "red"]


def test_pins_work_without_a_palette() -> None:
    """An override alone should colour that bar and leave the rest at defaults."""
    res = resolve_colors(TIERS, overrides={"VIP": "red"})
    assert res.colors is not None
    assert res.colors[2] == "red"
    assert res.colors[0] != "red"


# ---------------------------------------------------------------------------
# Matching — a silently-ignored request is worse than an error
# ---------------------------------------------------------------------------


def test_matching_is_case_insensitive_and_trimmed() -> None:
    res = resolve_colors(TIERS, overrides={"  vip ": "red"})
    assert res.colors is not None
    assert res.colors[2] == "red"
    assert res.unmatched == []


def test_unmatched_keys_are_reported_not_swallowed() -> None:
    res = resolve_colors(TIERS, overrides={"Platinum": "silver"})
    assert res.unmatched == ["Platinum"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_invalid_color_raises_with_the_key_named() -> None:
    with pytest.raises(ChartColorError, match="VIP"):
        resolve_colors(TIERS, overrides={"VIP": "burgundyish"})


def test_five_digit_hex_suggests_the_fix() -> None:
    """`#ff000` is the classic typo — say so instead of failing inside matplotlib."""
    with pytest.raises(ChartColorError, match="#ff0000"):
        resolve_colors(TIERS, overrides={"VIP": "#ff000"})


def test_invalid_palette_color_raises() -> None:
    with pytest.raises(ChartColorError):
        resolve_colors(TIERS, palette=["#111111", "nope"])


# ---------------------------------------------------------------------------
# Palette parsing (env var → list)
# ---------------------------------------------------------------------------


def test_parse_palette_splits_and_trims() -> None:
    assert parse_palette("#0F766E, #F59E0B ,#7C3AED") == ["#0F766E", "#F59E0B", "#7C3AED"]


def test_parse_palette_tolerates_trailing_comma_and_blank() -> None:
    assert parse_palette("#0F766E,,") == ["#0F766E"]
    assert parse_palette("") == []


# ---------------------------------------------------------------------------
# End-to-end through the renderer
# ---------------------------------------------------------------------------

ROWS = [{"tier": "Green", "n": 70}, {"tier": "Gold", "n": 20}, {"tier": "VIP", "n": 10}]


@pytest.mark.parametrize("ct", ["bar", "pie"])
def test_render_accepts_palette_and_overrides(ct: str) -> None:
    png = render_chart(
        ROWS,
        chart_type=ct,
        x="tier",
        y="n",
        palette=["#0F766E", "#F59E0B", "#7C3AED"],
        color_overrides={"VIP": "#ff0000"},
    )
    assert png.startswith(_PNG_MAGIC)


def test_line_override_is_keyed_on_the_y_column() -> None:
    """A line is one series — "make the revenue line red" keys on `y`, not a row."""
    png = render_chart(
        ROWS, chart_type="line", x="tier", y="n", color_overrides={"n": "red"}
    )
    assert png.startswith(_PNG_MAGIC)


def test_render_rejects_a_bad_colour_before_matplotlib_does() -> None:
    with pytest.raises(ChartColorError):
        render_chart(ROWS, chart_type="bar", x="tier", y="n", palette=["not-a-colour"])

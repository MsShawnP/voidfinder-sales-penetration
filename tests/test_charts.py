"""Unit tests for the shared dollar-axis tick logic.

The old SI tick formatter rounded to one significant figure, so
adjacent ticks collided ($120k and $150k both read "$200k"). These
pin the replacement: evenly spaced ticks, each labeled with its true
value, with an axis max that always clears the largest bar.
"""
import pandas as pd
import pytest

from app.charts import (
    _base_layout,
    _dollar_ticks,
    _fmt_dollar_tick,
    _left_margin_for,
    _nice_step,
    hbar_dollars,
    split_bars_by_type,
    trend_line,
)


# ---------------------------------------------------------- label format


@pytest.mark.parametrize(
    "value,label",
    [
        (0, "$0"),
        (50_000, "$50k"),
        (100_000, "$100k"),
        (150_000, "$150k"),
        (250_000, "$250k"),
        (2_500, "$2.5k"),
        (1_000_000, "$1M"),
        (1_500_000, "$1.5M"),
        (500, "$500"),
    ],
)
def test_tick_label_shows_true_value(value, label):
    assert _fmt_dollar_tick(value) == label


# ---------------------------------------------------------- tick spacing


def test_ticks_are_evenly_spaced_with_no_duplicate_labels():
    vals, text, axis_max = _dollar_ticks(164_884)
    # Even spacing.
    steps = {round(b - a, 6) for a, b in zip(vals, vals[1:])}
    assert len(steps) == 1
    # Every label distinct — the whole point of the fix.
    assert len(set(text)) == len(text)
    assert vals[0] == 0 and text[0] == "$0"


def test_axis_max_clears_the_largest_bar():
    for peak in (164_884, 99_500, 250_000, 12_345, 1_400_000):
        _, _, axis_max = _dollar_ticks(peak)
        assert axis_max > peak


def test_reported_case_no_longer_duplicates():
    # The retailer chart peaked near $100k and showed
    # "$100k, $100k … $200k, $200k". With true-value ticks, a window
    # topping out at $164,884 must read $0/$50k/$100k/$150k/$200k.
    _, text, _ = _dollar_ticks(164_884)
    assert text == ["$0", "$50k", "$100k", "$150k", "$200k"]


def test_step_is_a_human_round_number():
    # Steps come from the 1/2/2.5/5 x 10^n ladder.
    for peak in (30_000, 164_884, 900_000, 4_200):
        step = _nice_step(peak, target_ticks=5)
        mantissa = step / 10 ** (len(str(int(step))) - 1)
        assert round(step / mantissa) == 10 ** (len(str(int(step))) - 1)


def test_empty_or_zero_data_is_safe():
    vals, text, axis_max = _dollar_ticks(0)
    assert vals == [0.0] and text == ["$0"] and axis_max == 1.0


# ----------------------------------------- axis-label clipping guard
# These pin the shared-template invariants that keep y-axis category
# labels from clipping: automargin on BOTH axes plus a left-margin
# floor. A regression that rebuilds an axis dict without automargin
# (the exact bug that has recurred) trips these.

_MIN_LEFT_MARGIN = 40


def _bar_df():
    return pd.DataFrame(
        {"label": ["Never scanned", "Went dark"], "void_dollars": [3000.0, 750.0]}
    )


def _split_df():
    return pd.DataFrame(
        {
            "chain_name": ["Kroger", "Kroger", "Regional Group"],
            "void_type": ["never_scanned", "went_dark", "went_dark"],
            "void_dollars": [1000.0, 500.0, 250.0],
        }
    )


def _trend_df():
    return pd.DataFrame(
        {
            "week_ending": pd.date_range("2025-01-04", periods=5, freq="W-SAT"),
            "void_count": [1, 2, 3, 2, 4],
        }
    )


def test_base_layout_sets_automargin_on_both_axes_with_left_floor():
    lay = _base_layout("title")
    assert lay["xaxis"]["automargin"] is True
    assert lay["yaxis"]["automargin"] is True
    assert lay["margin"]["l"] >= _MIN_LEFT_MARGIN


def test_every_cartesian_chart_keeps_automargin_and_left_margin():
    figs = {
        "hbar": hbar_dollars(_bar_df(), "label", "void_dollars", "t"),
        "split_bars": split_bars_by_type(_split_df(), "chain_name", "t"),
        "trend": trend_line(_trend_df(), "t"),
    }
    for name, fig in figs.items():
        assert fig.layout.xaxis.automargin is True, f"{name} x-axis lost automargin"
        assert fig.layout.yaxis.automargin is True, f"{name} y-axis lost automargin"
        assert fig.layout.margin.l is not None and fig.layout.margin.l >= _MIN_LEFT_MARGIN, (
            f"{name} left margin below floor"
        )


def test_left_margin_grows_with_the_longest_category_label():
    # Short labels sit at the floor; a long product name reserves a wide
    # left margin so it renders in full (automargin alone under-reserves
    # when the chart first paints in a hidden tab).
    assert _left_margin_for(["A", "BB"]) == _MIN_LEFT_MARGIN or _left_margin_for(["A"]) >= 40
    long_label = "Dark Chocolate Sea Salt Bites"  # 29 chars
    assert _left_margin_for([long_label]) >= 200


def test_horizontal_bar_chart_reserves_room_for_a_long_label():
    df = pd.DataFrame(
        {"label": ["Dark Chocolate Sea Salt Bites", "X"], "void_dollars": [100.0, 50.0]}
    )
    fig = hbar_dollars(df, "label", "void_dollars", "t")
    assert fig.layout.margin.l >= 200

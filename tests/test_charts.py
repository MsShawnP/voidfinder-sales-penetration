"""Unit tests for the shared dollar-axis tick logic.

The old SI tick formatter rounded to one significant figure, so
adjacent ticks collided ($120k and $150k both read "$200k"). These
pin the replacement: evenly spaced ticks, each labeled with its true
value, with an axis max that always clears the largest bar.
"""
import pytest

from app.charts import _dollar_ticks, _fmt_dollar_tick, _nice_step


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

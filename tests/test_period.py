"""Unit tests for reporting-period resolution and in-period accrual.

The period selector windows the trend chart and the accrued-dollar
totals. These pin the window each preset resolves to and the clipped
dollar math, because a wrong window silently mis-states "Lost so far".

Grid used throughout: 156 weekly Saturday week-endings spanning
2023-01-07 .. 2025-12-27 — the same shape as the real scan data.
"""
import pandas as pd
import pytest

from app.calculations import (
    DEFAULT_PERIOD,
    period_void_dollars,
    resolve_period,
)

WEEKS = pd.date_range("2023-01-07", "2025-12-27", freq="W-SAT")
LAST = WEEKS[-1]   # 2025-12-27
FIRST = WEEKS[0]   # 2023-01-07


def test_grid_is_three_full_years():
    assert len(WEEKS) == 156
    assert LAST == pd.Timestamp("2025-12-27")


# ------------------------------------------------------------ presets


def test_default_period_is_last_26_weeks():
    assert DEFAULT_PERIOD == "26w"
    r = resolve_period(WEEKS, "26w")
    assert r["period_weeks"] == 26
    assert r["end"] == LAST
    assert r["start"] == WEEKS[-26]
    assert r["label"] == "the last 26 weeks"


def test_last_13_weeks_window():
    r = resolve_period(WEEKS, "13w")
    assert r["period_weeks"] == 13
    assert r["start"] == WEEKS[-13]
    assert r["label"] == "the last 13 weeks"


def test_all_history_spans_the_whole_grid():
    r = resolve_period(WEEKS, "all")
    assert r["start"] == FIRST
    assert r["end"] == LAST
    assert r["period_weeks"] == 156
    assert "all history" in r["label"]
    assert "Jan 2023" in r["label"]


def test_year_to_date_starts_january_first():
    r = resolve_period(WEEKS, "ytd")
    assert r["start"] == pd.Timestamp("2025-01-01")
    assert r["end"] == LAST
    assert r["period_weeks"] == 52  # all 52 Saturdays of 2025
    assert r["label"] == "2025 to date"


def test_last_full_year_is_latest_complete_calendar_year():
    r = resolve_period(WEEKS, "full_year")
    assert r["start"] == pd.Timestamp("2025-01-01")
    assert r["label"] == "2025"
    assert r["period_weeks"] == 52


def test_full_year_skips_a_partial_trailing_year():
    # Two weeks into 2026: 2026 is incomplete, so "last full year" is
    # still 2025.
    grid = pd.date_range("2023-01-07", "2026-01-10", freq="W-SAT")
    r = resolve_period(grid, "full_year")
    assert r["start"] == pd.Timestamp("2025-01-01")
    assert r["label"] == "2025"


def test_last_6_months_offsets_six_calendar_months():
    r = resolve_period(WEEKS, "6mo")
    assert r["start"] == pd.Timestamp("2025-06-27")
    assert r["end"] == LAST
    assert r["label"] == "the last 6 months"


# ------------------------------------------------------------- as-of


def test_period_end_follows_the_as_of_date():
    as_of = WEEKS[-10]
    r = resolve_period(WEEKS, "13w", as_of=as_of)
    assert r["end"] == as_of
    assert r["start"] == WEEKS[-22]  # 13 weeks back from week -10
    assert r["period_weeks"] == 13


def test_as_of_beyond_the_data_is_clamped_to_the_last_week():
    r = resolve_period(WEEKS, "26w", as_of=pd.Timestamp("2030-01-01"))
    assert r["end"] == LAST


# ------------------------------------------------------------ custom


def test_custom_range_uses_its_own_start_and_end():
    r = resolve_period(
        WEEKS, "custom",
        custom_start="2024-06-01", custom_end="2024-09-07",
    )
    assert r["start"] == pd.Timestamp("2024-06-01")
    assert r["end"] == pd.Timestamp("2024-09-07")
    # Saturdays in [2024-06-01, 2024-09-07]: 2024-06-01 .. 2024-09-07.
    assert r["period_weeks"] == 15
    assert "Jun 1, 2024" in r["label"]
    assert "Sep 7, 2024" in r["label"]


def test_custom_end_beyond_data_is_clamped():
    r = resolve_period(
        WEEKS, "custom",
        custom_start="2025-01-01", custom_end="2031-01-01",
    )
    assert r["end"] == LAST


# ---------------------------------------------------- empty / invalid


def test_empty_grid_returns_a_safe_zero_window():
    r = resolve_period([], "26w")
    assert r["start"] is None
    assert r["period_weeks"] == 0


def test_unknown_period_falls_back_to_the_default():
    r = resolve_period(WEEKS, "nonsense")
    assert r["period_weeks"] == 26
    assert r["label"] == "the last 26 weeks"


# ------------------------------------------------ in-period accrual


def _accrual_frame():
    # Two voids: one 40 weeks old, one 10 weeks old.
    return pd.DataFrame(
        {
            "void_weeks": [40, 10],
            "median_weekly_dollars": [10.0, 5.0],
        }
    )


def test_old_void_is_clipped_to_the_window_new_void_is_not():
    dollars = period_void_dollars(_accrual_frame(), period_weeks=26)
    # 40-week void clipped to 26 -> 260; 10-week void unchanged -> 50.
    assert list(dollars) == [pytest.approx(260.0), pytest.approx(50.0)]


def test_no_clip_when_period_covers_the_whole_history():
    dollars = period_void_dollars(_accrual_frame(), period_weeks=None)
    assert list(dollars) == [pytest.approx(400.0), pytest.approx(50.0)]


def test_accrual_is_empty_for_an_empty_void_list():
    dollars = period_void_dollars(_accrual_frame().iloc[0:0], period_weeks=26)
    assert dollars.empty

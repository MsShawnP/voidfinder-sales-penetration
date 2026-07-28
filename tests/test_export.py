"""Workbook export tests — the verified-figures rule: summary tab
totals must be computed from the same rows as the detail tab."""

from io import BytesIO

import pandas as pd
import pytest
from openpyxl import load_workbook

from app.export import generate_workbook

PARAMS = {"void_weeks_n": 6, "slow_mover_min": 0.5}

# The real caller passes the whole display state, which carries the selected
# reporting period (export.py:200). PARAMS above omits it, so nothing in this
# file could ever exercise period clipping -- see the xfail tests at the bottom.
PARAMS_WITH_PERIOD = {**PARAMS, "period": "26w"}


def _voids():
    """Two voids whose lives straddle a 26-week window.

    ``median_weekly_dollars`` is what ``calculations.period_void_dollars``
    clips against; ``void_dollars`` is the unclipped whole-life figure and
    equals weekly x weeks for each row.
    """
    return pd.DataFrame(
        [
            {
                "sku": "CHP-AS-001", "store_id": "RET-KROGER-S0001",
                "chain_name": "Kroger", "region": "Southeast",
                "volume_tier": "medium", "product_name": "Basil Marinara",
                "void_type": "never_scanned", "void_weeks": 40,
                "median_weekly_dollars": 20.0,
                "void_dollars": 800.0, "fixability": 0.95, "priority": 380.0,
                "cluster_id": "RET-KROGER|Southeast",
            },
            {
                "sku": "CHP-SC-002", "store_id": "RET-WALMART-S0002",
                "chain_name": "Walmart", "region": "West",
                "volume_tier": "high", "product_name": "Hot Honey Mustard",
                "void_type": "went_dark", "void_weeks": 8,
                "median_weekly_dollars": 18.75,
                "void_dollars": 150.0, "fixability": 0.7, "priority": 105.0,
                "cluster_id": None,
            },
        ]
    )


def _addresses():
    return pd.DataFrame(
        [
            {"store_id": "RET-KROGER-S0001", "street": "100 Peach St",
             "city": "Atlanta", "state": "GA", "zip": "30301"},
            {"store_id": "RET-WALMART-S0002", "street": "8 Desert Rd",
             "city": "Phoenix", "state": "AZ", "zip": "85001"},
        ]
    )


def _load(payload):
    return load_workbook(BytesIO(payload))


def test_workbook_has_two_branded_tabs():
    wb = _load(generate_workbook(_voids(), _addresses(), "2025-12-27", PARAMS))
    assert wb.sheetnames == ["Void Summary", "Broker Work List"]


def test_summary_total_reconciles_with_detail_rows():
    voids = _voids()
    wb = _load(generate_workbook(voids, _addresses(), "2025-12-27", PARAMS))
    detail = wb["Broker Work List"]
    header = [c.value for c in detail[1]]
    dollars_col = header.index("Opportunity ($)") + 1
    detail_total = sum(
        detail.cell(row=r, column=dollars_col).value
        for r in range(2, detail.max_row + 1)
    )
    assert detail_total == pytest.approx(voids["void_dollars"].sum())


def test_detail_rows_sorted_by_opportunity_and_carry_addresses():
    wb = _load(generate_workbook(_voids(), _addresses(), "2025-12-27", PARAMS))
    detail = wb["Broker Work List"]
    header = [c.value for c in detail[1]]
    assert "Street" in header and "ZIP" in header and "What to check" in header
    dollars_col = header.index("Opportunity ($)") + 1
    values = [
        detail.cell(row=r, column=dollars_col).value
        for r in range(2, detail.max_row + 1)
    ]
    assert values == sorted(values, reverse=True)
    street_col = header.index("Street") + 1
    assert detail.cell(row=2, column=street_col).value == "100 Peach St"


def test_missing_addresses_do_not_break_export():
    wb = _load(generate_workbook(_voids(), pd.DataFrame(), "2025-12-27", PARAMS))
    detail = wb["Broker Work List"]
    assert detail.max_row == 3  # header + 2 rows, blanks not crashes


def test_empty_voids_produce_valid_workbook():
    empty = _voids().iloc[0:0]
    wb = _load(generate_workbook(empty, _addresses(), None, PARAMS))
    assert wb["Broker Work List"].max_row == 1  # header only


# ── Un-pinned: the workbook total is not period-clipped ──────────────────────
# Bug: app/export.py:74 -- _build_summary computes the KPI as
# work["void_dollars"].sum(), the whole-life figure, while the Exception Report
# and Summary Rollup clip to the selected period (views/exceptions.py:198,
# views/rollup.py:76). The workbook therefore prints a larger total than the
# screen the user exported it from. generate_workbook already receives the full
# state (export.py:200), so the period is in hand.
#
# These assert the corrected behaviour and are strict-xfail so the markers
# cannot silently outlive the defect: the moment the clip lands they XPASS and
# the suite fails until the markers come off.
# Tracked in PLAN.md -- "Workbook total is not period-clipped".

def _summary_dollar_cells(wb):
    return [
        c.value for row in wb["Void Summary"].iter_rows() for c in row
        if isinstance(c.value, str) and c.value.startswith("$")
    ]


@pytest.mark.xfail(strict=True, reason="export.py:74 sums whole-life void_dollars, ignoring the period")
def test_summary_total_is_clipped_to_the_selected_period():
    voids = _voids()
    wb = _load(generate_workbook(voids, _addresses(), "2025-12-27", PARAMS_WITH_PERIOD))
    unclipped = voids["void_dollars"].sum()
    assert f"${unclipped:,.0f}" not in _summary_dollar_cells(wb), (
        "summary KPI still shows the unclipped whole-life total"
    )


@pytest.mark.xfail(strict=True, reason="export.py:67-71 parameter line omits the reporting period")
def test_parameter_line_states_the_reporting_period():
    wb = _load(generate_workbook(_voids(), _addresses(), "2025-12-27", PARAMS_WITH_PERIOD))
    text = " ".join(
        str(c.value) for row in wb["Void Summary"].iter_rows() for c in row
        if isinstance(c.value, str)
    )
    assert "26w" in text or "26 week" in text, (
        "reader cannot tell which period the total covers"
    )

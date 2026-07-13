"""Executive content pack: hero numbers, trend takeaway wording, and
the state aggregation behind the cluster map. The hero and takeaway
print dollar claims an exec will repeat — they get pinned like the
calculations do."""

import pandas as pd

from app.calculations import annualized_run_rate
from app.layout import build_hero, why_opportunity_line, why_run_rate_line
from app.views.exceptions import state_dollars
from app.views.trend import takeaway

AS_OF = pd.Timestamp("2025-12-27")


def _voids_frame():
    # Mirrors the real find_voids output shape: state rides along from
    # the store universe (see conftest.make_stores).
    return pd.DataFrame(
        {
            "store_id": ["S1", "S2", "S3", "S4"],
            "sku": ["CHP-AS-001", "CHP-AS-002", "CHP-SC-001", "CHP-PS-001"],
            "chain_name": ["Kroger", "Kroger", "Walmart", "Costco"],
            "region": ["Southeast", "Southeast", "Midwest", "West"],
            "state": ["GA", "GA", "IL", "CA"],
            "void_type": [
                "never_scanned", "never_scanned", "went_dark", "went_dark",
            ],
            "void_dollars": [1000.0, 2000.0, 500.0, 250.0],
            "median_weekly_dollars": [10.0, 20.0, 5.0, 2.5],
            "cluster_id": ["Kroger-SE", "Kroger-SE", None, None],
        }
    )


def _text(component) -> str:
    """Flatten a Dash component tree to its visible text."""
    if component is None:
        return ""
    if isinstance(component, str):
        return component
    if isinstance(component, (list, tuple)):
        return "".join(_text(c) for c in component)
    children = getattr(component, "children", None)
    return _text(children)


def test_hero_headline_carries_total_dollars():
    text = _text(build_hero(_voids_frame(), AS_OF))
    assert (
        "$3,750 in lost sales — from stores that already approved your "
        "product." in text
    )


def test_hero_subhead_is_as_of_aware_with_both_numbers():
    # Run rate: (10 + 20 + 5 + 2.5) weekly = 37.5 × 52 = 1,950/yr.
    text = _text(build_hero(_voids_frame(), AS_OF))
    assert "As of December 27, 2025, 4 item-store voids across" in text
    assert "4 stores" in text
    assert "$3,750 lost so far" in text
    assert "$1,950/yr if nothing changes" in text


def test_hero_action_names_the_top_cluster_when_present():
    text = _text(build_hero(_voids_frame(), AS_OF))
    assert "2 never-scanned voids clustered in Kroger's Southeast region" in text
    assert "($3,000)" in text
    assert "one phone call to one broker, not 4." in text


def test_hero_omits_action_line_when_no_cluster():
    voids = _voids_frame()
    voids["cluster_id"] = None
    text = _text(build_hero(voids, AS_OF))
    assert "botched shelf reset" not in text
    assert "$3,750 in lost sales" in text


def test_hero_is_none_when_no_data():
    assert build_hero(None, AS_OF) is None
    assert build_hero(_voids_frame().iloc[0:0], AS_OF) is None


def test_annualized_run_rate_is_weekly_loss_times_52():
    assert annualized_run_rate(_voids_frame()) == 37.5 * 52
    assert annualized_run_rate(_voids_frame().iloc[0:0]) == 0.0


def test_why_panel_line_carries_run_rate_and_share():
    text = why_run_rate_line(_voids_frame())
    assert "At the current pace these voids bleed about $1,950 a year" in text
    assert "of the brand's annual sales" in text


def test_why_panel_line_degrades_without_data():
    text = why_run_rate_line(None)
    assert "voids compound silently" in text
    assert "current pace" not in text


def test_why_opportunity_line_uses_the_period_total_not_a_hardcoded_figure():
    # $366,175 rounds to the "$366K" the KPI-scoped total should show;
    # a different period must produce a different figure.
    assert "recovering $366K of fully-authorized" in why_opportunity_line(366_175)
    assert "recovering $189K of fully-authorized" in why_opportunity_line(189_070)
    # No stale hardcoded value survives.
    assert "$366K" not in why_opportunity_line(189_070)


def test_why_opportunity_line_computes_margin_equivalent():
    # $200K at 3-5% margin → $4.0M–$6.7M equivalent
    text = why_opportunity_line(200_000)
    assert "$4.0M" in text
    assert "$6.7M" in text


def test_why_opportunity_line_degrades_without_a_figure():
    text = why_opportunity_line(0)
    assert "$" not in text
    assert "many times its face value" in text


def _trend(counts):
    return pd.DataFrame(
        {
            "week_ending": pd.date_range("2025-07-05", periods=len(counts), freq="W-SAT"),
            "void_count": counts,
        }
    )


def test_takeaway_reads_rising_when_last_exceeds_first():
    text = takeaway(_trend([84, 90, 100, 114]))
    assert "climbed from 84 to 114 over 4 weeks" in text
    assert "decaying faster" in text


def test_takeaway_reads_falling_when_last_below_first():
    text = takeaway(_trend([114, 100, 90]))
    assert "fell from 114 to 90" in text
    assert "outpacing" in text


def test_takeaway_reads_structural_when_flat():
    text = takeaway(_trend([100, 90, 100]))
    assert "held at 100" in text
    assert "structural" in text


def test_takeaway_empty_when_no_trend():
    assert takeaway(_trend([])) == ""
    assert takeaway(None) == ""


def test_rollup_by_void_type_splits_the_two_kinds():
    from app.calculations import rollup

    agg = rollup(_voids_frame(), "void_type").set_index("void_type")
    assert agg.loc["never_scanned", "void_dollars"] == 3000.0
    assert agg.loc["went_dark", "void_dollars"] == 750.0


def test_state_dollars_sums_by_state():
    agg = state_dollars(_voids_frame()).set_index("state")["void_dollars"]
    assert agg["GA"] == 3000.0
    assert agg["IL"] == 500.0
    assert agg["CA"] == 250.0


def test_state_dollars_empty_when_no_voids():
    agg = state_dollars(_voids_frame().iloc[0:0])
    assert agg.empty
    assert list(agg.columns) == ["state", "void_dollars"]

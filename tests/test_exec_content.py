"""Executive content pack: hero numbers, trend takeaway wording, and
the state aggregation behind the cluster map. The hero and takeaway
print dollar claims an exec will repeat — they get pinned like the
calculations do."""

import pandas as pd

from app.layout import build_hero
from app.views.exceptions import state_dollars
from app.views.trend import takeaway


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
    text = _text(build_hero(_voids_frame()))
    assert (
        "$3,750 in lost sales — from stores that already approved your "
        "product." in text
    )


def test_hero_subhead_counts_stores():
    text = _text(build_hero(_voids_frame()))
    assert "In 4 stores, the retailer said yes" in text
    assert "The fix is just getting the product back on the shelf." in text


def test_hero_action_names_the_top_cluster_when_present():
    text = _text(build_hero(_voids_frame()))
    assert "2 never-scanned voids clustered in Kroger's Southeast region" in text
    assert "($3,000)" in text
    assert "one phone call to one broker, not 4." in text


def test_hero_omits_action_line_when_no_cluster():
    voids = _voids_frame()
    voids["cluster_id"] = None
    text = _text(build_hero(voids))
    assert "botched shelf reset" not in text
    assert "$3,750 in lost sales" in text


def test_hero_is_none_when_no_data():
    assert build_hero(None) is None
    assert build_hero(_voids_frame().iloc[0:0]) is None


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

"""Unit tests for void detection, classification, and dollarization.

These pin exact numbers. A wrong opportunity figure kills credibility,
so every arithmetic path asserts a hand-computed value.

World used throughout (see conftest.py):
- 20 consecutive Saturday week-endings, ending AS_OF = 2025-12-27.
- One SKU unless a test adds more.
- Comparable stores are tier "medium", region "Southeast" unless a
  test says otherwise.
"""
from datetime import timedelta

import pandas as pd
import pytest

from app.calculations import (
    DEFAULT_VOID_WEEKS_N,
    find_voids,
    rollup,
    void_trend,
)
from conftest import (
    AS_OF,
    WEEKS,
    EARLY,
    make_stores,
    make_auth,
    scans_for,
)

SKU = "CHP-AS-001"


def build_world(extra_stores=(), extra_auth=(), extra_scans=()):
    """Five healthy comparables + whatever the test adds.

    Comparables c1..c5 scan every week, constant 4 units / $20 per
    week -> median weekly units 4.0, median weekly dollars 20.0.
    """
    stores = [(f"c{i}", "RET-KROGER", "Kroger", "Southeast", "GA", "medium") for i in range(1, 6)]
    stores += list(extra_stores)
    auth = [(SKU, f"c{i}", EARLY, None) for i in range(1, 6)]
    auth += list(extra_auth)
    scans = []
    for i in range(1, 6):
        scans += scans_for(SKU, f"c{i}", WEEKS, units=4, dollars=20.0)
    scans += list(extra_scans)
    return make_stores(stores), make_auth(auth), pd.DataFrame(
        scans, columns=["sku", "store_id", "week_ending", "units_sold", "dollars_sold"]
    )


# ---------------------------------------------------------------- detection


def test_never_scanned_when_authorized_and_zero_scans():
    stores, auth, scans = build_world(
        extra_stores=[("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v1", EARLY, None)],
    )
    voids = find_voids(stores, auth, scans)
    assert len(voids) == 1
    row = voids.iloc[0]
    assert row["store_id"] == "v1"
    assert row["void_type"] == "never_scanned"
    assert row["void_weeks"] == 20  # authorized before the window, dark all 20 weeks
    assert pd.isna(row["last_scan_week"])


def test_went_dark_when_scans_stop():
    stores, auth, scans = build_world(
        extra_stores=[("v2", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v2", EARLY, None)],
        extra_scans=scans_for(SKU, "v2", WEEKS[:10], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans)
    assert len(voids) == 1
    row = voids.iloc[0]
    assert row["void_type"] == "went_dark"
    assert row["last_scan_week"] == WEEKS[9]
    assert row["void_weeks"] == 10  # weeks 11..20 have no scans


def test_active_store_is_not_a_void():
    stores, auth, scans = build_world()  # only healthy comparables
    voids = find_voids(stores, auth, scans)
    assert voids.empty


def test_gap_shorter_than_n_is_not_a_void():
    # Dark for 5 weeks; default N is 6.
    stores, auth, scans = build_world(
        extra_stores=[("v3", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v3", EARLY, None)],
        extra_scans=scans_for(SKU, "v3", WEEKS[:15], units=4, dollars=20.0),
    )
    assert DEFAULT_VOID_WEEKS_N == 6
    voids = find_voids(stores, auth, scans)
    assert voids.empty


def test_n_is_a_parameter_not_a_constant():
    # The same 5-week gap flips to a void at N=4.
    stores, auth, scans = build_world(
        extra_stores=[("v3", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v3", EARLY, None)],
        extra_scans=scans_for(SKU, "v3", WEEKS[:15], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans, void_weeks_n=4)
    assert len(voids) == 1
    assert voids.iloc[0]["void_weeks"] == 5


def test_deauthorized_pair_is_not_a_void():
    stores, auth, scans = build_world(
        extra_stores=[("v4", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v4", EARLY, AS_OF - timedelta(weeks=2))],
    )
    voids = find_voids(stores, auth, scans)
    assert voids.empty


def test_recently_authorized_pair_gets_a_grace_period():
    # Authorized 3 weeks before as_of with no scans: not yet a void at N=6.
    stores, auth, scans = build_world(
        extra_stores=[("v5", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v5", WEEKS[17], None)],
    )
    voids = find_voids(stores, auth, scans)
    assert voids.empty


def test_never_scanned_weeks_count_from_authorization():
    # Authorized at week 11 -> 10 zero-scan weeks, not 20.
    stores, auth, scans = build_world(
        extra_stores=[("v6", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v6", WEEKS[10], None)],
    )
    voids = find_voids(stores, auth, scans)
    assert len(voids) == 1
    assert voids.iloc[0]["void_weeks"] == 10
    assert voids.iloc[0]["void_type"] == "never_scanned"


def test_scans_after_as_of_are_ignored():
    # v7 scans only in the last 2 weeks; with as_of rolled back 3
    # weeks it has never scanned.
    stores, auth, scans = build_world(
        extra_stores=[("v7", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v7", EARLY, None)],
        extra_scans=scans_for(SKU, "v7", WEEKS[18:], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans, as_of=WEEKS[16])
    assert len(voids) == 1
    assert voids.iloc[0]["void_type"] == "never_scanned"


# ------------------------------------------------------------ dollarization


def test_dollarization_uses_median_not_mean():
    # Comparables' weekly dollars: 20, 20, 20, 20, 20 from the base
    # world; add two hot stores at $200/week. Median stays 20; the
    # mean would be ~71. The void figure must use the median.
    hot = []
    for s in ("h1", "h2"):
        hot += scans_for(SKU, s, WEEKS, units=40, dollars=200.0)
    stores, auth, scans = build_world(
        extra_stores=[
            ("h1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
            ("h2", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
            ("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
        ],
        extra_auth=[
            (SKU, "h1", EARLY, None),
            (SKU, "h2", EARLY, None),
            (SKU, "v1", EARLY, None),
        ],
        extra_scans=hot,
    )
    voids = find_voids(stores, auth, scans)
    row = voids.iloc[0]
    assert row["median_weekly_dollars"] == pytest.approx(20.0)
    assert row["void_dollars"] == pytest.approx(20.0 * 20)  # $400, not ~$1,428
    assert row["void_units"] == pytest.approx(4.0 * 20)
    assert row["comparable_stores"] == 7
    assert row["comparable_basis"] == "tier_region"


def test_comparables_restricted_to_same_tier_and_region():
    # A monster store in another region must not move the median.
    stores, auth, scans = build_world(
        extra_stores=[
            ("far", "RET-KROGER", "Kroger", "West", "CA", "medium"),
            ("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
        ],
        extra_auth=[(SKU, "far", EARLY, None), (SKU, "v1", EARLY, None)],
        extra_scans=scans_for(SKU, "far", WEEKS, units=100, dollars=500.0),
    )
    voids = find_voids(stores, auth, scans)
    row = voids.iloc[0]
    assert row["comparable_basis"] == "tier_region"
    assert row["comparable_stores"] == 5
    assert row["median_weekly_dollars"] == pytest.approx(20.0)


def test_basis_widens_when_too_few_tier_region_comparables():
    # Void store is tier "high": no high-tier comparables in region,
    # but two high-tier stores exist in another region -> still under
    # min 3 at "tier", so it widens to "region" (5 medium stores).
    extra = []
    for s in ("hh1", "hh2"):
        extra += scans_for(SKU, s, WEEKS, units=10, dollars=50.0)
    stores, auth, scans = build_world(
        extra_stores=[
            ("hh1", "RET-KROGER", "Kroger", "West", "CA", "high"),
            ("hh2", "RET-KROGER", "Kroger", "West", "CA", "high"),
            ("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "high"),
        ],
        extra_auth=[
            (SKU, "hh1", EARLY, None),
            (SKU, "hh2", EARLY, None),
            (SKU, "v1", EARLY, None),
        ],
        extra_scans=extra,
    )
    voids = find_voids(stores, auth, scans)
    row = voids.iloc[0]
    assert row["comparable_basis"] == "region"
    assert row["comparable_stores"] == 5
    assert row["median_weekly_dollars"] == pytest.approx(20.0)


def test_dark_stores_are_not_comparables():
    # c5 goes dark too: the median must come from the 4 still-scanning
    # stores, and the dark store never benchmarks the void.
    stores, auth, scans = build_world(
        extra_stores=[("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "v1", EARLY, None)],
    )
    scans = scans[~((scans["store_id"] == "c5") & (scans["week_ending"] > WEEKS[9]))]
    voids = find_voids(stores, auth, scans)
    v1 = voids[voids["store_id"] == "v1"].iloc[0]
    assert v1["comparable_stores"] == 4
    # c5 itself shows up as a went-dark void.
    assert set(voids["store_id"]) == {"v1", "c5"}


def test_slow_movers_are_excluded():
    # Comparables sell ~1 unit/month (0.25/wk) -> below the 0.5 floor.
    slow_sku = "CHP-SC-009"
    slow = []
    for i in range(1, 6):
        # one unit every 4th week
        slow += scans_for(slow_sku, f"c{i}", WEEKS[::4], units=1, dollars=5.0)
    stores, auth, scans = build_world(
        extra_stores=[("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(slow_sku, f"c{i}", EARLY, None) for i in range(1, 6)]
        + [(slow_sku, "v1", EARLY, None)],
        extra_scans=slow,
    )
    voids = find_voids(stores, auth, scans)
    assert slow_sku not in set(voids["sku"])


def test_no_comparables_anywhere_yields_no_dollar_claim():
    # A SKU nobody scans has no benchmark: it must drop out rather
    # than invent a number.
    ghost_sku = "CHP-DG-005"
    stores, auth, scans = build_world(
        extra_stores=[("v1", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(ghost_sku, "v1", EARLY, None)],
    )
    voids = find_voids(stores, auth, scans)
    assert ghost_sku not in set(voids["sku"])


def test_velocity_window_denominator_is_full_window():
    # A comparable scanning 6 of the last 13 weeks at 4 units has
    # weekly velocity 24/13, not 4.
    patchy_weeks = WEEKS[-13::2]  # 7 of the last 13 weeks
    patchy = scans_for(SKU, "p1", patchy_weeks, units=4, dollars=20.0)
    stores, auth, scans = build_world(
        extra_stores=[
            ("p1", "RET-KROGER", "Kroger", "West", "CA", "low"),
            ("p2", "RET-KROGER", "Kroger", "West", "CA", "low"),
            ("p3", "RET-KROGER", "Kroger", "West", "CA", "low"),
            ("v1", "RET-KROGER", "Kroger", "West", "CA", "low"),
        ],
        extra_auth=[
            (SKU, "p1", EARLY, None),
            (SKU, "p2", EARLY, None),
            (SKU, "p3", EARLY, None),
            (SKU, "v1", EARLY, None),
        ],
        extra_scans=patchy
        + scans_for(SKU, "p2", patchy_weeks, units=4, dollars=20.0)
        + scans_for(SKU, "p3", patchy_weeks, units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans)
    row = voids[voids["store_id"] == "v1"].iloc[0]
    expected_weekly = (4 * 7) / 13
    assert row["median_weekly_units"] == pytest.approx(expected_weekly)
    assert row["void_dollars"] == pytest.approx(round((20.0 * 7) / 13 * 20, 2))


# ------------------------------------------------- fixability and ranking


def test_fixability_never_scanned_beats_stale_went_dark():
    stores, auth, scans = build_world(
        extra_stores=[
            ("nv", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
            ("gd", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
        ],
        extra_auth=[(SKU, "nv", EARLY, None), (SKU, "gd", EARLY, None)],
        extra_scans=scans_for(SKU, "gd", WEEKS[:5], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans).set_index("store_id")
    assert voids.loc["nv", "fixability"] == pytest.approx(0.9)
    # 15 dark weeks > 12 -> stale
    assert voids.loc["gd", "fixability"] == pytest.approx(0.5)


def test_recent_went_dark_fixability():
    stores, auth, scans = build_world(
        extra_stores=[("gd", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "gd", EARLY, None)],
        extra_scans=scans_for(SKU, "gd", WEEKS[:12], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans)
    assert voids.iloc[0]["void_weeks"] == 8
    assert voids.iloc[0]["fixability"] == pytest.approx(0.7)


def test_priority_is_dollars_times_fixability_and_sorted():
    stores, auth, scans = build_world(
        extra_stores=[
            ("nv", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
            ("gd", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
        ],
        extra_auth=[(SKU, "nv", EARLY, None), (SKU, "gd", EARLY, None)],
        extra_scans=scans_for(SKU, "gd", WEEKS[:5], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans)
    for _, r in voids.iterrows():
        assert r["priority"] == pytest.approx(round(r["void_dollars"] * r["fixability"], 2))
    assert list(voids["priority"]) == sorted(voids["priority"], reverse=True)
    # nv: 20 weeks x $20 x 0.9 = $360; gd: 15 weeks x $20 x 0.5 = $150
    assert voids.iloc[0]["store_id"] == "nv"
    assert voids.iloc[0]["priority"] == pytest.approx(360.0)
    assert voids.iloc[1]["priority"] == pytest.approx(150.0)


def test_cluster_detection_boosts_fixability():
    # 10 never-scanned pairs in one retailer+region -> cluster.
    extra_stores, extra_auth = [], []
    for i in range(10):
        sid = f"cl{i}"
        extra_stores.append((sid, "RET-KROGER", "Kroger", "Southeast", "GA", "medium"))
        extra_auth.append((SKU, sid, EARLY, None))
    # plus one scattered never-scanned void elsewhere
    extra_stores.append(("lone", "RET-WALMART", "Walmart", "West", "CA", "medium"))
    extra_auth.append((SKU, "lone", EARLY, None))
    lone_comps = []
    for i in range(1, 4):
        extra_stores.append((f"wc{i}", "RET-WALMART", "Walmart", "West", "CA", "medium"))
        extra_auth.append((SKU, f"wc{i}", EARLY, None))
        lone_comps += scans_for(SKU, f"wc{i}", WEEKS, units=4, dollars=20.0)
    stores, auth, scans = build_world(
        extra_stores=extra_stores, extra_auth=extra_auth, extra_scans=lone_comps
    )
    voids = find_voids(stores, auth, scans)
    clustered = voids[voids["store_id"].str.startswith("cl")]
    assert (clustered["cluster_id"] == "RET-KROGER|Southeast").all()
    assert clustered["fixability"].tolist() == pytest.approx([0.95] * len(clustered))
    lone = voids[voids["store_id"] == "lone"].iloc[0]
    assert pd.isna(lone["cluster_id"])
    assert lone["fixability"] == pytest.approx(0.9)


# ------------------------------------------------------------------ rollup


def test_rollup_totals_reconcile_with_detail():
    stores, auth, scans = build_world(
        extra_stores=[
            ("nv", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
            ("gd", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
        ],
        extra_auth=[(SKU, "nv", EARLY, None), (SKU, "gd", EARLY, None)],
        extra_scans=scans_for(SKU, "gd", WEEKS[:5], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans)
    for by in ("sku", "retailer", "region"):
        agg = rollup(voids, by)
        assert agg["void_dollars"].sum() == pytest.approx(voids["void_dollars"].sum())
        assert agg["void_count"].sum() == len(voids)


def test_rollup_rejects_unknown_key():
    with pytest.raises(ValueError):
        rollup(pd.DataFrame(), "banner_typo")


# ------------------------------------------------------------------- trend


def test_trend_counts_flip_when_gap_reaches_n():
    # gd scans through week 10, dark 11..20. With N=4 the pair is a
    # void from week 14 onward (4 full dark weeks).
    stores, auth, scans = build_world(
        extra_stores=[("gd", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "gd", EARLY, None)],
        extra_scans=scans_for(SKU, "gd", WEEKS[:10], units=4, dollars=20.0),
    )
    trend = void_trend(stores, auth, scans, void_weeks_n=4, trend_weeks=20)
    t = trend.set_index("week_ending")["void_count"]
    assert t[WEEKS[12]] == 0  # 2 dark weeks
    assert t[WEEKS[13]] == 1  # 4 dark weeks -> void
    assert t[WEEKS[19]] == 1


def test_trend_final_point_matches_exception_report():
    stores, auth, scans = build_world(
        extra_stores=[
            ("nv", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
            ("gd", "RET-KROGER", "Kroger", "Southeast", "GA", "medium"),
        ],
        extra_auth=[(SKU, "nv", EARLY, None), (SKU, "gd", EARLY, None)],
        extra_scans=scans_for(SKU, "gd", WEEKS[:5], units=4, dollars=20.0),
    )
    voids = find_voids(stores, auth, scans)
    trend = void_trend(stores, auth, scans, trend_weeks=8)
    assert trend.iloc[-1]["void_count"] == len(voids)


def test_trend_shows_resolved_voids_in_the_past():
    # heal scans weeks 1..5, dark 6..12 (void at N=4 from week 9),
    # then scans again 13..20 (resolved). The as-of report has no
    # voids, but the trend must show the historical void window.
    heal = scans_for(SKU, "heal", WEEKS[:5], units=4, dollars=20.0) + scans_for(
        SKU, "heal", WEEKS[12:], units=4, dollars=20.0
    )
    stores, auth, scans = build_world(
        extra_stores=[("heal", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "heal", EARLY, None)],
        extra_scans=heal,
    )
    assert find_voids(stores, auth, scans, void_weeks_n=4).empty
    trend = void_trend(stores, auth, scans, void_weeks_n=4, trend_weeks=20)
    t = trend.set_index("week_ending")["void_count"]
    assert t[WEEKS[8]] == 1   # 4 dark weeks (6,7,8,9)
    assert t[WEEKS[11]] == 1  # still dark
    assert t[WEEKS[12]] == 0  # scanned again
    assert t[WEEKS[19]] == 0


def test_trend_respects_authorization_start():
    # Never-scanned pair authorized at week 11: void (N=4) from week
    # 14; weeks before authorization never count.
    stores, auth, scans = build_world(
        extra_stores=[("nv", "RET-KROGER", "Kroger", "Southeast", "GA", "medium")],
        extra_auth=[(SKU, "nv", WEEKS[10], None)],
    )
    trend = void_trend(stores, auth, scans, void_weeks_n=4, trend_weeks=20)
    t = trend.set_index("week_ending")["void_count"]
    assert t[WEEKS[9]] == 0
    assert t[WEEKS[12]] == 0  # 3 weeks authorized
    assert t[WEEKS[13]] == 1  # 4 weeks authorized, zero scans

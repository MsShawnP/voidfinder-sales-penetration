"""Void detection, classification, and dollarization.

A void = a store authorized to carry a SKU where the SKU is not
scanning. Everything here is pure pandas — no database access — so
the whole module is unit-testable without infrastructure.

Stated assumptions (these are surfaced in the app UI, keep in sync):

- Expected sales for a void store = MEDIAN weekly velocity of
  comparable scanning stores (same volume tier + region), times the
  void duration in weeks. Median, not mean, so one hot store cannot
  inflate the opportunity number.
- Comparable velocity is measured over the trailing
  VELOCITY_WINDOW_WEEKS weeks ending at the as-of week, divided by
  the full window length (a store that scanned 4 of 13 weeks has
  low velocity, not missing velocity).
- A store only counts as a comparable if its last scan is within
  the void threshold N of the as-of week (a store that is itself
  going dark is not a benchmark).
- If fewer than MIN_COMPARABLE_STORES comparables exist at
  tier+region, the basis widens: tier+region -> tier -> region ->
  all scanning stores. The basis used is reported per void.
- SKUs whose comparable median velocity is below the slow-mover
  floor are excluded entirely — 1 unit a month is not a void.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# N: a void requires this many consecutive zero-scan weeks.
# A PARAMETER, not a constant — the UI exposes it. This is the default.
DEFAULT_VOID_WEEKS_N = 6

# Comparable cohorts with median weekly units below this floor are
# slow movers, not voids. 0.5/week ≈ 2 units/month.
DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS = 0.5

# Trailing window for measuring comparable-store velocity.
VELOCITY_WINDOW_WEEKS = 13

# Minimum comparable stores before the basis widens.
MIN_COMPARABLE_STORES = 3

# Fixability: probability-flavored weight that a broker visit fixes
# the void. Never-scanned = likely a missed shelf set, one visit
# fixes it. Went-dark decays with staleness.
FIXABILITY_NEVER_SCANNED = 0.9
FIXABILITY_WENT_DARK_RECENT = 0.7  # void_weeks <= WENT_DARK_STALE_WEEKS
FIXABILITY_WENT_DARK_STALE = 0.5
WENT_DARK_STALE_WEEKS = 12

# Never-scanned voids clustered in one retailer+region look like a
# botched mod reset — one call fixes many stores, so fixability
# gets a bump.
CLUSTER_MIN_PAIRS = 10
CLUSTER_FIXABILITY_BOOST = 0.05

_BASIS_LADDER = ["tier_region", "tier", "region", "all"]


def _week_grid(scans: pd.DataFrame, as_of) -> np.ndarray:
    """Sorted array of distinct week_ending dates up to as_of."""
    weeks = scans.loc[scans["week_ending"] <= as_of, "week_ending"].unique()
    return np.sort(np.asarray(weeks))


def _active_auth(auth: pd.DataFrame, as_of) -> pd.DataFrame:
    """Authorizations in force at as_of."""
    live = auth["authorized_date"] <= as_of
    deauth = auth["deauthorized_date"]
    live &= deauth.isna() | (deauth > as_of)
    return auth.loc[live, ["sku", "store_id", "authorized_date"]]


def _positive_scans(scans: pd.DataFrame, as_of) -> pd.DataFrame:
    keep = (scans["week_ending"] <= as_of) & (scans["units_sold"] > 0)
    return scans.loc[keep]


def _store_velocity(scans: pd.DataFrame, weeks: np.ndarray) -> pd.DataFrame:
    """Weekly velocity per (sku, store) over the trailing window.

    Denominator is the full window length, not weeks-with-scans.
    """
    window = weeks[-VELOCITY_WINDOW_WEEKS:]
    in_window = scans.loc[scans["week_ending"] >= window[0]]
    vel = (
        in_window.groupby(["sku", "store_id"], as_index=False)
        .agg(units=("units_sold", "sum"), dollars=("dollars_sold", "sum"))
    )
    n = len(window)
    vel["weekly_units"] = vel["units"] / n
    vel["weekly_dollars"] = vel["dollars"] / n
    return vel[["sku", "store_id", "weekly_units", "weekly_dollars"]]


def _cohort_medians(velocity: pd.DataFrame, stores: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Median comparable velocity at each fallback level.

    Returns one DataFrame per basis level keyed by the grouping
    columns for that level, with median weekly units/dollars and the
    comparable-store count.
    """
    v = velocity.merge(
        stores[["store_id", "region", "volume_tier"]], on="store_id", how="left"
    )
    levels = {
        "tier_region": ["sku", "volume_tier", "region"],
        "tier": ["sku", "volume_tier"],
        "region": ["sku", "region"],
        "all": ["sku"],
    }
    out = {}
    for name, cols in levels.items():
        med = v.groupby(cols, as_index=False).agg(
            median_weekly_units=("weekly_units", "median"),
            median_weekly_dollars=("weekly_dollars", "median"),
            comparable_stores=("store_id", "nunique"),
        )
        out[name] = med
    return out


def _attach_comparables(
    voids: pd.DataFrame,
    cohorts: dict[str, pd.DataFrame],
    min_comparables: int,
) -> pd.DataFrame:
    """Merge cohort medians onto voids, widening the basis until the
    comparable count clears min_comparables."""
    keys = {
        "tier_region": ["sku", "volume_tier", "region"],
        "tier": ["sku", "volume_tier"],
        "region": ["sku", "region"],
        "all": ["sku"],
    }
    result = voids.copy()
    result["comparable_basis"] = pd.NA
    result["median_weekly_units"] = np.nan
    result["median_weekly_dollars"] = np.nan
    result["comparable_stores"] = 0

    unresolved = result.index
    for level in _BASIS_LADDER:
        if len(unresolved) == 0:
            break
        med = cohorts[level]
        merged = result.loc[unresolved, keys[level]].merge(
            med, on=keys[level], how="left"
        )
        merged.index = unresolved
        # Final level accepts any comparable count >= 1 so a void
        # never silently loses its dollar figure while comparables
        # exist anywhere.
        floor = 1 if level == "all" else min_comparables
        ok = merged["comparable_stores"].fillna(0) >= floor
        take = unresolved[ok]
        result.loc[take, "comparable_basis"] = level
        result.loc[take, "median_weekly_units"] = merged.loc[ok, "median_weekly_units"]
        result.loc[take, "median_weekly_dollars"] = merged.loc[ok, "median_weekly_dollars"]
        result.loc[take, "comparable_stores"] = merged.loc[ok, "comparable_stores"].astype(int)
        unresolved = unresolved[~ok]

    # No scanning store anywhere carries this SKU: no benchmark, so
    # no dollar estimate. Dropped by the slow-mover filter later.
    return result


def _fixability(voids: pd.DataFrame) -> pd.Series:
    fix = np.where(
        voids["void_type"] == "never_scanned",
        FIXABILITY_NEVER_SCANNED,
        np.where(
            voids["void_weeks"] <= WENT_DARK_STALE_WEEKS,
            FIXABILITY_WENT_DARK_RECENT,
            FIXABILITY_WENT_DARK_STALE,
        ),
    )
    return pd.Series(fix, index=voids.index)


def _cluster_ids(voids: pd.DataFrame) -> pd.Series:
    """Label never-scanned voids that cluster in one retailer+region."""
    cluster = pd.Series(pd.NA, index=voids.index, dtype="object")
    never = voids[voids["void_type"] == "never_scanned"]
    sizes = never.groupby(["retailer_id", "region"]).size()
    for (rid, region), n in sizes.items():
        if n >= CLUSTER_MIN_PAIRS:
            mask = (
                (voids["void_type"] == "never_scanned")
                & (voids["retailer_id"] == rid)
                & (voids["region"] == region)
            )
            cluster[mask] = f"{rid}|{region}"
    return cluster


def find_voids(
    stores: pd.DataFrame,
    auth: pd.DataFrame,
    scans: pd.DataFrame,
    as_of=None,
    void_weeks_n: int = DEFAULT_VOID_WEEKS_N,
    slow_mover_min_weekly_units: float = DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
    min_comparables: int = MIN_COMPARABLE_STORES,
) -> pd.DataFrame:
    """The void exception list: one row per authorized, non-scanning
    (sku, store) pair, classified, dollarized, and ranked.

    Inputs mirror the cinderhaven-db raw tables:
      stores: store_id, retailer_id, chain_name, region, state, volume_tier
      auth:   sku, store_id, authorized_date, deauthorized_date
      scans:  sku, store_id, week_ending, units_sold, dollars_sold
    """
    if as_of is None:
        as_of = scans["week_ending"].max()

    weeks = _week_grid(scans, as_of)
    if len(weeks) == 0:
        raise ValueError("no scan weeks at or before as_of")

    live_auth = _active_auth(auth, as_of)
    pos_scans = _positive_scans(scans, as_of)

    last_scan = (
        pos_scans.groupby(["sku", "store_id"], as_index=False)["week_ending"]
        .max()
        .rename(columns={"week_ending": "last_scan_week"})
    )

    pairs = live_auth.merge(last_scan, on=["sku", "store_id"], how="left")

    # Weeks of void: for went-dark, grid weeks after the last scan;
    # for never-scanned, grid weeks since authorization.
    last_idx = np.searchsorted(weeks, pairs["last_scan_week"].to_numpy(), side="right")
    auth_idx = np.searchsorted(weeks, pairs["authorized_date"].to_numpy(), side="left")
    never = pairs["last_scan_week"].isna().to_numpy()
    start_idx = np.where(never, auth_idx, last_idx)
    pairs["void_weeks"] = len(weeks) - start_idx
    pairs["void_type"] = np.where(never, "never_scanned", "went_dark")

    voids = pairs[pairs["void_weeks"] >= void_weeks_n].copy()
    if voids.empty:
        return _empty_result()

    voids = voids.merge(
        stores[["store_id", "retailer_id", "chain_name", "region", "state", "volume_tier"]],
        on="store_id",
        how="left",
    )

    # Comparables: stores still scanning this SKU (last scan within N
    # weeks of as_of), measured over the trailing velocity window.
    scanning_cutoff_idx = max(len(weeks) - void_weeks_n, 0)
    scanning_cutoff = weeks[scanning_cutoff_idx]
    current = last_scan[last_scan["last_scan_week"] >= scanning_cutoff]
    vel = _store_velocity(pos_scans, weeks)
    vel = vel.merge(current[["sku", "store_id"]], on=["sku", "store_id"], how="inner")

    cohorts = _cohort_medians(vel, stores)
    voids = _attach_comparables(voids, cohorts, min_comparables)

    # Slow movers out: no comparable benchmark, or a benchmark below
    # the floor, is not an actionable void.
    voids = voids[
        voids["median_weekly_units"].notna()
        & (voids["median_weekly_units"] >= slow_mover_min_weekly_units)
    ].copy()
    if voids.empty:
        return _empty_result()

    voids["void_dollars"] = (voids["median_weekly_dollars"] * voids["void_weeks"]).round(2)
    voids["void_units"] = (voids["median_weekly_units"] * voids["void_weeks"]).round(1)

    voids["fixability"] = _fixability(voids)
    voids["cluster_id"] = _cluster_ids(voids)
    boost = voids["cluster_id"].notna() * CLUSTER_FIXABILITY_BOOST
    voids["fixability"] = (voids["fixability"] + boost).clip(upper=1.0)
    voids["priority"] = (voids["void_dollars"] * voids["fixability"]).round(2)

    voids = voids.sort_values(
        ["priority", "void_dollars", "sku", "store_id"],
        ascending=[False, False, True, True],
    ).reset_index(drop=True)

    return voids[_RESULT_COLUMNS]


_RESULT_COLUMNS = [
    "sku", "store_id", "retailer_id", "chain_name", "region", "state",
    "volume_tier", "void_type", "authorized_date", "last_scan_week",
    "void_weeks", "comparable_basis", "comparable_stores",
    "median_weekly_units", "median_weekly_dollars", "void_units",
    "void_dollars", "fixability", "cluster_id", "priority",
]


def _empty_result() -> pd.DataFrame:
    return pd.DataFrame(columns=_RESULT_COLUMNS)


_ROLLUP_KEYS = {
    "sku": ["sku"],
    "retailer": ["retailer_id", "chain_name"],
    "region": ["region"],
}


def rollup(voids: pd.DataFrame, by: str) -> pd.DataFrame:
    """Total void dollars and counts by sku / retailer / region."""
    if by not in _ROLLUP_KEYS:
        raise ValueError(f"by must be one of {sorted(_ROLLUP_KEYS)}, got {by!r}")
    keys = _ROLLUP_KEYS[by]
    if voids.empty:
        return pd.DataFrame(columns=keys + ["void_count", "store_count", "void_dollars"])
    out = voids.groupby(keys, as_index=False).agg(
        void_count=("sku", "size"),
        store_count=("store_id", "nunique"),
        void_dollars=("void_dollars", "sum"),
    )
    return out.sort_values("void_dollars", ascending=False).reset_index(drop=True)


def void_trend(
    stores: pd.DataFrame,
    auth: pd.DataFrame,
    scans: pd.DataFrame,
    as_of=None,
    void_weeks_n: int = DEFAULT_VOID_WEEKS_N,
    slow_mover_min_weekly_units: float = DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
    min_comparables: int = MIN_COMPARABLE_STORES,
    trend_weeks: int = 26,
) -> pd.DataFrame:
    """Void count per week over the trailing trend window.

    Slow-mover eligibility is evaluated once, on as-of comparable
    cohorts, and applied uniformly across the window (so the latest
    trend point always agrees with the exception report).
    """
    if as_of is None:
        as_of = scans["week_ending"].max()
    weeks = _week_grid(scans, as_of)
    pos_scans = _positive_scans(scans, as_of)

    live_auth = _active_auth(auth, as_of)
    last_scan = (
        pos_scans.groupby(["sku", "store_id"], as_index=False)["week_ending"]
        .max()
        .rename(columns={"week_ending": "last_scan_week"})
    )

    # Same comparable cohorts as find_voids, evaluated at as_of.
    scanning_cutoff_idx = max(len(weeks) - void_weeks_n, 0)
    scanning_cutoff = weeks[scanning_cutoff_idx]
    current = last_scan[last_scan["last_scan_week"] >= scanning_cutoff]
    vel = _store_velocity(pos_scans, weeks)
    vel = vel.merge(current[["sku", "store_id"]], on=["sku", "store_id"], how="inner")
    cohorts = _cohort_medians(vel, stores)

    pairs = live_auth.merge(
        stores[["store_id", "region", "volume_tier"]], on="store_id", how="left"
    )
    pairs = _attach_comparables(pairs, cohorts, min_comparables)
    pairs = pairs[
        pairs["median_weekly_units"].notna()
        & (pairs["median_weekly_units"] >= slow_mover_min_weekly_units)
    ]

    trend_grid = weeks[-trend_weeks:]
    grid_idx = np.searchsorted(weeks, trend_grid, side="right")
    counts = np.zeros(len(trend_grid), dtype=int)

    scan_map = {
        key: np.sort(grp.to_numpy())
        for key, grp in pos_scans.groupby(["sku", "store_id"])["week_ending"]
    }
    for row in pairs.itertuples(index=False):
        auth64 = np.datetime64(row.authorized_date)
        auth_start = np.searchsorted(weeks, auth64, side="left")
        sw = scan_map.get((row.sku, row.store_id))
        authorized = trend_grid >= auth64
        if sw is None or len(sw) == 0:
            start = np.full(len(trend_grid), auth_start)
        else:
            sw_start = np.searchsorted(weeks, sw, side="right")
            n_prior = np.searchsorted(sw, trend_grid, side="right")
            start = np.where(
                n_prior > 0,
                sw_start[np.clip(n_prior - 1, 0, None)],
                auth_start,
            )
        counts += ((grid_idx - start) >= void_weeks_n) & authorized

    return pd.DataFrame({"week_ending": trend_grid, "void_count": counts})

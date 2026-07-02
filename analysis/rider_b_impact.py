"""Rider B — ANALYSIS ONLY. Nothing here writes anywhere.

Question from Shawn (DECISIONS.md 2026-07-02): if the Void Finder
demo voids were unified into the shared cinderhaven-store-universe
generator (option b), how much would Door Math's locked ACV/TDP
canonical figures shift?

Method: generate Door Math's in-memory data from the installed
cinderhaven-store-universe package, apply the same void patterns the
cinderhaven-db seed applies (never-scanned cluster at Kroger x
Southeast for 3 Artisan Sauces SKUs; 30 went-dark pairs, 8-20 weeks
dark), and recompute Door Math's metrics before and after.

Metric definitions replicate Door Math's: carrying = scanned at
least once in the last-13-ISO-week window; ACV% = volume-weighted
carrying (A=3, B=2, C=1) over total weight; TDP = sum of per-SKU
ACV%; penetration = carrying pairs / authorized pairs. Deltas are
robust to small definitional drift even if absolute levels differ
slightly from Door Math's exact figures.

Run:  .venv/Scripts/python analysis/rider_b_impact.py
"""
from __future__ import annotations

import random

import pandas as pd
from cinderhaven_store_universe import (
    get_auth_matrix,
    get_scan_data,
    get_slow_leak_config,
    get_stores,
)

CLUSTER_RETAILER = "RET-KROGER"
CLUSTER_REGION = "Southeast"
CLUSTER_SKUS = ["CHP-AS-001", "CHP-AS-002", "CHP-AS-006"]
WENT_DARK_PAIRS = 30
WENT_DARK_MIN_WEEKS = 8
WENT_DARK_MAX_WEEKS = 20
VOID_SEED = 700

TIER_WEIGHT = {"A": 3, "B": 2, "C": 1}
WINDOW_WEEKS = 13  # last quarter of the package's 2024-W01..2025-W52 span

# Rate tolerance from CINDERHAVEN_CANONICAL.md.
LOCK_TOLERANCE_PP = 0.5


def _quarter_window(scans: pd.DataFrame) -> list[str]:
    weeks = sorted(scans["week"].unique())
    return weeks[-WINDOW_WEEKS:]


def _carrying(scans: pd.DataFrame, window: list[str]) -> pd.DataFrame:
    in_q = scans[(scans["week"].isin(window)) & (scans["scanned"])]
    return in_q[["sku_id", "store_id"]].drop_duplicates()


def _metrics(stores, auth, scans, window):
    """ACV% and TDP by retailer plus portfolio penetration."""
    weights = stores.assign(weight=stores["volume_tier"].map(TIER_WEIGHT))
    carrying = _carrying(scans, window).merge(
        weights[["store_id", "retailer_id", "weight"]], on="store_id"
    )
    total_by_ret = weights.groupby("retailer_id")["weight"].sum()

    acv = (
        carrying.groupby(["retailer_id", "sku_id"])["weight"].sum()
        / total_by_ret
    ).rename("acv_pct") * 100
    tdp = acv.groupby("retailer_id").sum().rename("tdp")

    authorized = auth[auth["authorized"]]
    carrying_pairs = len(carrying[["sku_id", "store_id"]].drop_duplicates())
    penetration = carrying_pairs / len(authorized) * 100

    return acv, tdp, penetration, len(authorized)


def _apply_voids(stores, auth, scans):
    """Return copies with the cluster auths added and went-dark scans
    removed — the option-(b) unified world."""
    cluster_stores = stores[
        (stores["retailer_id"] == CLUSTER_RETAILER)
        & (stores["region"] == CLUSTER_REGION)
    ]["store_id"]

    auth2 = auth.copy()
    added = 0
    for sku in CLUSTER_SKUS:
        mask = (
            auth2["sku_id"].eq(sku)
            & auth2["store_id"].isin(cluster_stores)
            & ~auth2["authorized"]
        )
        added += int(mask.sum())
        auth2.loc[mask, "authorized"] = True
        auth2.loc[mask, "authorized_date"] = "2025-W27"

    # Went-dark scatter: same selection rules as the DB seed —
    # currently-scanning pairs outside the cluster retailer+region,
    # skipping the package's curated slow-leak SKUs.
    weeks = sorted(scans["week"].unique())
    recent = set(weeks[-4:])
    leak_skus = set(get_slow_leak_config().keys())
    outside = stores[
        ~(
            (stores["retailer_id"] == CLUSTER_RETAILER)
            & (stores["region"] == CLUSTER_REGION)
        )
    ]["store_id"]
    candidates = (
        scans[
            scans["scanned"]
            & scans["week"].isin(recent)
            & scans["store_id"].isin(outside)
            & ~scans["sku_id"].isin(leak_skus | set(CLUSTER_SKUS))
        ][["sku_id", "store_id"]]
        .drop_duplicates()
        .sort_values(["sku_id", "store_id"])
    )
    rng = random.Random(VOID_SEED)
    picked = rng.sample(list(candidates.itertuples(index=False, name=None)),
                        min(WENT_DARK_PAIRS, len(candidates)))

    scans2 = scans.copy()
    week_index = {w: i for i, w in enumerate(weeks)}
    for sku, store in picked:
        dark_weeks = rng.randint(WENT_DARK_MIN_WEEKS, WENT_DARK_MAX_WEEKS)
        cutoff_idx = len(weeks) - dark_weeks
        dark = set(weeks[cutoff_idx:])
        mask = (
            scans2["sku_id"].eq(sku)
            & scans2["store_id"].eq(store)
            & scans2["week"].isin(dark)
        )
        scans2.loc[mask, "scanned"] = False

    return auth2, scans2, added, picked


def main():
    stores = get_stores()
    auth = get_auth_matrix()
    scans = get_scan_data()
    window = _quarter_window(scans)

    acv0, tdp0, pen0, auth_pairs0 = _metrics(stores, auth, scans, window)
    auth2, scans2, added, picked = _apply_voids(stores, auth, scans)
    acv1, tdp1, pen1, auth_pairs1 = _metrics(stores, auth2, scans2, window)

    print("RIDER B — option (b) unification impact on Door Math figures")
    print(f"window: last {WINDOW_WEEKS} ISO weeks ({window[0]}..{window[-1]})")
    print(f"cluster authorizations added: {added}")
    print(f"went-dark pairs applied: {len(picked)}")
    print()

    tdp_delta = (tdp1 - tdp0).fillna(0.0)
    print("TDP by retailer (points):")
    for rid in tdp0.index:
        d = tdp_delta.get(rid, 0.0)
        flag = " <-- exceeds 0.5pp lock" if abs(d) > LOCK_TOLERANCE_PP else ""
        print(f"  {rid:16s} {tdp0[rid]:8.2f} -> {tdp1.get(rid, 0):8.2f} "
              f"({d:+.2f}){flag}")

    acv_delta = (acv1 - acv0).abs().dropna()
    worst = acv_delta.sort_values(ascending=False).head(8)
    print("\nLargest per-SKU ACV%% shifts (pp):")
    for (rid, sku), d in worst.items():
        print(f"  {rid:16s} {sku:12s} {acv0.get((rid, sku), 0):6.2f} -> "
              f"{acv1.get((rid, sku), 0):6.2f} ({d:+.2f})")

    print(f"\nPortfolio penetration rate: {pen0:.2f}%% -> {pen1:.2f}%% "
          f"({pen1 - pen0:+.2f}pp)")
    print(f"Authorized pairs: {auth_pairs0:,} -> {auth_pairs1:,} (+{auth_pairs1 - auth_pairs0})")
    print(f"\nRate lock tolerance: {LOCK_TOLERANCE_PP}pp "
          "(CINDERHAVEN_CANONICAL.md)")


if __name__ == "__main__":
    main()

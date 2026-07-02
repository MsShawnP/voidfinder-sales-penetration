"""Shared fixtures: a small deterministic world of stores, auths,
and weekly scans shaped exactly like the cinderhaven-db raw tables."""
from datetime import timedelta

import pandas as pd

# 20 consecutive Saturday week-endings, newest = 2025-12-27.
AS_OF = pd.Timestamp("2025-12-27")
WEEKS = [AS_OF - timedelta(weeks=(19 - i)) for i in range(20)]

# A date safely before the scan window starts.
EARLY = WEEKS[0] - timedelta(weeks=10)


def make_stores(rows):
    return pd.DataFrame(
        rows,
        columns=["store_id", "retailer_id", "chain_name", "region", "state", "volume_tier"],
    )


def make_auth(rows):
    df = pd.DataFrame(
        rows, columns=["sku", "store_id", "authorized_date", "deauthorized_date"]
    )
    df["authorized_date"] = pd.to_datetime(df["authorized_date"])
    df["deauthorized_date"] = pd.to_datetime(df["deauthorized_date"])
    return df


def scans_for(sku, store_id, weeks, units, dollars):
    """One scan row per week at constant units/dollars."""
    return [(sku, store_id, w, units, dollars) for w in weeks]

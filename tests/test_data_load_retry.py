"""A failed startup load must not be cached: a transient DB blip at
boot previously left the worker degraded forever (empty frames cached
by _load_frames), which is how prod showed database=true but
data_loaded=false until a restart."""

import pandas as pd

from app import data


def _empty(*_args, **_kwargs):
    return pd.DataFrame()


def _make_frames():
    stores = pd.DataFrame({"store_id": ["S1"], "retailer_id": ["R1"],
                           "chain_name": ["C"], "region": ["East"],
                           "state": ["NY"], "volume_tier": ["mid"]})
    auth = pd.DataFrame({"sku": ["K1"], "store_id": ["S1"],
                         "authorized_date": [pd.Timestamp("2025-01-06")],
                         "deauthorized_date": [pd.NaT]})
    scans = pd.DataFrame({"sku": ["K1"], "store_id": ["S1"],
                          "week_ending": [pd.Timestamp("2025-01-11")],
                          "units_sold": [3], "dollars_sold": [12.0]})
    return stores, auth, scans


def test_data_becomes_available_when_db_recovers_after_failed_load(monkeypatch):
    data.refresh()
    # Mock at the db boundary: a dead database returns empty frames.
    for fn in ("get_stores", "get_auth", "get_scans", "get_products",
               "get_addresses"):
        monkeypatch.setattr(data.db, fn, _empty)
    assert data.data_available() is False

    # Database comes back; the next access must retry without refresh().
    stores, auth, scans = _make_frames()
    monkeypatch.setattr(data.db, "get_stores", lambda: stores.copy())
    monkeypatch.setattr(data.db, "get_auth", lambda: auth.copy())
    monkeypatch.setattr(data.db, "get_scans", lambda: scans.copy())
    assert data.data_available() is True
    data.refresh()


def test_successful_load_is_cached_and_not_reloaded(monkeypatch):
    data.refresh()
    stores, auth, scans = _make_frames()
    calls = {"n": 0}

    def counting_get_stores():
        calls["n"] += 1
        return stores.copy()

    monkeypatch.setattr(data.db, "get_stores", counting_get_stores)
    monkeypatch.setattr(data.db, "get_auth", lambda: auth.copy())
    monkeypatch.setattr(data.db, "get_scans", lambda: scans.copy())
    monkeypatch.setattr(data.db, "get_products", _empty)
    monkeypatch.setattr(data.db, "get_addresses", _empty)

    assert data.data_available() is True
    assert data.data_available() is True
    assert calls["n"] == 1, "successful load should hit the DB once, not per access"
    data.refresh()

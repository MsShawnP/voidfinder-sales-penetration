"""Startup data load and parameter-keyed void cache.

Tables load once per process (module-level, like Door Math) and the
tested pure-pandas core in app/calculations.py does all the math.
If the database is unreachable at startup, every frame is empty and
the UI shows "data temporarily unavailable" — the app never crashes
on a dead database.
"""

import logging
import threading

import pandas as pd

from app import calculations, db

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_frames: dict[str, pd.DataFrame] = {}
_void_cache: dict[tuple, pd.DataFrame] = {}
_trend_cache: dict[tuple, pd.DataFrame] = {}


def _load_frames() -> dict[str, pd.DataFrame]:
    with _lock:
        if _frames:
            return _frames
        logger.info("Loading Cinderhaven frames from Postgres...")
        loaded = {
            "stores": db.get_stores(),
            "auth": db.get_auth(),
            "scans": db.get_scans(),
            "products": db.get_products(),
            "addresses": db.get_addresses(),
        }
        # A failed load must not be cached: db.py returns empty frames on
        # any database failure, and caching those would leave the worker
        # degraded forever after a transient blip. Return without
        # populating _frames so the next access retries.
        if loaded["stores"].empty or loaded["auth"].empty or loaded["scans"].empty:
            logger.warning(
                "Database load incomplete (stores=%d, auth=%d, scans=%d) — "
                "will retry on next access",
                len(loaded["stores"]), len(loaded["auth"]), len(loaded["scans"]),
            )
            return loaded
        _frames.update(loaded)
        logger.info(
            "Loaded: %d stores, %d auths, %d scan rows",
            len(_frames["stores"]), len(_frames["auth"]), len(_frames["scans"]),
        )
        return _frames


def data_available() -> bool:
    f = _load_frames()
    return not (f["stores"].empty or f["auth"].empty or f["scans"].empty)


def refresh():
    """Drop everything and reload on next access (manual refresh hook)."""
    with _lock:
        _frames.clear()
        _void_cache.clear()
        _trend_cache.clear()


def get_products() -> pd.DataFrame:
    return _load_frames()["products"].copy()


def get_stores() -> pd.DataFrame:
    return _load_frames()["stores"].copy()


def get_addresses() -> pd.DataFrame:
    return _load_frames()["addresses"].copy()


def as_of_week():
    f = _load_frames()
    if f["scans"].empty:
        return None
    return f["scans"]["week_ending"].max()


def week_range():
    """(first, last) scan week — the selectable as-of range. None
    when the data has not loaded."""
    f = _load_frames()
    if f["scans"].empty:
        return None
    return f["scans"]["week_ending"].min(), f["scans"]["week_ending"].max()


def _normalize_as_of(as_of):
    """Clamp a selected as-of into the data range; None = latest."""
    if as_of is None:
        return None
    ts = pd.Timestamp(as_of)
    rng = week_range()
    if rng is None:
        return None
    first, last = rng
    return min(max(ts, first), last)


def get_voids(void_weeks_n: int, slow_mover_min: float, as_of=None) -> pd.DataFrame:
    """Cached exception list for a parameter combination, with product
    names merged on for display. as_of=None means the latest week."""
    as_of = _normalize_as_of(as_of)
    key = (void_weeks_n, slow_mover_min, as_of)
    if key not in _void_cache:
        f = _load_frames()
        if f["stores"].empty or f["auth"].empty or f["scans"].empty:
            return calculations._empty_result()
        voids = calculations.find_voids(
            f["stores"], f["auth"], f["scans"],
            as_of=as_of,
            void_weeks_n=void_weeks_n,
            slow_mover_min_weekly_units=slow_mover_min,
        )
        if not f["products"].empty:
            voids = voids.merge(f["products"], on="sku", how="left")
        _void_cache[key] = voids
    return _void_cache[key].copy()


def get_trend(
    void_weeks_n: int, slow_mover_min: float, as_of=None, trend_weeks: int = 26
) -> pd.DataFrame:
    as_of = _normalize_as_of(as_of)
    key = (void_weeks_n, slow_mover_min, as_of, trend_weeks)
    if key not in _trend_cache:
        f = _load_frames()
        if f["stores"].empty or f["auth"].empty or f["scans"].empty:
            return pd.DataFrame(columns=["week_ending", "void_count"])
        _trend_cache[key] = calculations.void_trend(
            f["stores"], f["auth"], f["scans"],
            as_of=as_of,
            void_weeks_n=void_weeks_n,
            slow_mover_min_weekly_units=slow_mover_min,
            trend_weeks=trend_weeks,
        )
    return _trend_cache[key].copy()


def effective_as_of(as_of):
    """The as-of date actually used: the selection clamped to the data
    range, or the latest week when nothing is selected."""
    norm = _normalize_as_of(as_of)
    return norm if norm is not None else as_of_week()

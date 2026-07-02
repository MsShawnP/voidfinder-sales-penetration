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
        _frames["stores"] = db.get_stores()
        _frames["auth"] = db.get_auth()
        _frames["scans"] = db.get_scans()
        _frames["products"] = db.get_products()
        _frames["addresses"] = db.get_addresses()
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


def get_voids(void_weeks_n: int, slow_mover_min: float) -> pd.DataFrame:
    """Cached exception list for a parameter combination, with product
    names merged on for display."""
    key = (void_weeks_n, slow_mover_min)
    if key not in _void_cache:
        f = _load_frames()
        if f["stores"].empty or f["auth"].empty or f["scans"].empty:
            return calculations._empty_result()
        voids = calculations.find_voids(
            f["stores"], f["auth"], f["scans"],
            void_weeks_n=void_weeks_n,
            slow_mover_min_weekly_units=slow_mover_min,
        )
        if not f["products"].empty:
            voids = voids.merge(f["products"], on="sku", how="left")
        _void_cache[key] = voids
    return _void_cache[key].copy()


def get_trend(void_weeks_n: int, slow_mover_min: float, trend_weeks: int = 26) -> pd.DataFrame:
    key = (void_weeks_n, slow_mover_min, trend_weeks)
    if key not in _trend_cache:
        f = _load_frames()
        if f["stores"].empty or f["auth"].empty or f["scans"].empty:
            return pd.DataFrame(columns=["week_ending", "void_count"])
        _trend_cache[key] = calculations.void_trend(
            f["stores"], f["auth"], f["scans"],
            void_weeks_n=void_weeks_n,
            slow_mover_min_weekly_units=slow_mover_min,
            trend_weeks=trend_weeks,
        )
    return _trend_cache[key].copy()

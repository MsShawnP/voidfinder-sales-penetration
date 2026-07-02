"""Postgres connection pool and query functions for Cinderhaven SSOT.

Mirrors Spin Rate's db.py: psycopg2 pool via DATABASE_URL, 30s
statement timeout, Decimal->float cast at the DataFrame boundary,
empty DataFrame on any database failure (the UI degrades to
"data temporarily unavailable" instead of crashing).
"""

import logging
import os
import threading
from decimal import Decimal

import pandas as pd
import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = threading.Lock()

_QUERY_TIMEOUT_MS = 30_000


def _get_pool():
    """Module-level connection pool, created on first use.

    Raises RuntimeError if DATABASE_URL is missing so misconfiguration
    fails loudly at first query rather than silently returning nothing.
    """
    global _pool
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:
            return _pool

        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Set it to a postgresql:// connection string pointing at the Cinderhaven SSOT."
            )

        _pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=database_url,
            options=(
                f"-c statement_timeout={_QUERY_TIMEOUT_MS} "
                "-c search_path=public_marts,voidfinder,public"
            ),
        )

    return _pool


def db_ready() -> bool:
    """True when the database answers SELECT 1. Used by /ready only —
    never by /health (see wsgi.py for why)."""
    try:
        p = _get_pool()
        conn = p.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            p.putconn(conn)
    except Exception:
        return False


def _execute_query(sql, params=None):
    """Run a parameterized query, return a DataFrame; empty on failure."""
    try:
        p = _get_pool()
    except RuntimeError as exc:
        logger.error("%s", exc)
        return pd.DataFrame()
    try:
        conn = p.getconn()
    except pool.PoolError:
        logger.error("Connection pool exhausted — returning empty DataFrame")
        return pd.DataFrame()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=cols)
        for col in df.columns:
            if df[col].dtype == object and len(df) > 0:
                if isinstance(df[col].iloc[0], Decimal):
                    df[col] = df[col].astype(float)
        return df
    except psycopg2.extensions.QueryCanceledError:
        conn.rollback()
        logger.warning("Query timed out after %d ms — returning empty DataFrame", _QUERY_TIMEOUT_MS)
        return pd.DataFrame()
    except (psycopg2.OperationalError, psycopg2.InterfaceError) as exc:
        logger.error("Database connection failed: %s", exc)
        p.putconn(conn, close=True)
        conn = None
        return pd.DataFrame()
    except psycopg2.Error as exc:
        conn.rollback()
        logger.error("Database query failed: %s", exc)
        return pd.DataFrame()
    finally:
        if conn is not None:
            p.putconn(conn)


# ── Query functions ─────────────────────────────────────────────────
# Void Finder loads each table once at startup (see app/data.py) and
# runs the tested pure-pandas core on the frames — no SQL math that
# could drift from the unit-tested logic in app/calculations.py.


def get_stores() -> pd.DataFrame:
    """Store universe. Columns: store_id, retailer_id, chain_name,
    region, state, volume_tier."""
    sql = (
        "SELECT s.store_id, s.retailer_id, s.chain_name, "
        "s.region, s.state, s.volume_tier "
        "FROM raw.stores s "
        "ORDER BY s.store_id"
    )
    return _execute_query(sql)


def get_auth() -> pd.DataFrame:
    """Authorization matrix. Columns: sku, store_id, authorized_date,
    deauthorized_date."""
    sql = (
        "SELECT sku, store_id, authorized_date, deauthorized_date "
        "FROM raw.distribution_log "
        "ORDER BY sku, store_id"
    )
    df = _execute_query(sql)
    if not df.empty:
        df["authorized_date"] = pd.to_datetime(df["authorized_date"])
        df["deauthorized_date"] = pd.to_datetime(df["deauthorized_date"])
    return df


def get_scans() -> pd.DataFrame:
    """Weekly POS scans. Columns: sku, store_id, week_ending,
    units_sold, dollars_sold. Categorical keys keep ~1.4M rows small."""
    sql = (
        "SELECT sku, store_id, week_ending, units_sold, dollars_sold "
        "FROM raw.scan_data"
    )
    df = _execute_query(sql)
    if not df.empty:
        df["week_ending"] = pd.to_datetime(df["week_ending"])
        df["sku"] = df["sku"].astype("category")
        df["store_id"] = df["store_id"].astype("category")
    return df


def get_products() -> pd.DataFrame:
    """SKU names and lines. Columns: sku, product_name, product_line."""
    sql = (
        "SELECT sku, product_name, product_line "
        "FROM raw.product_master "
        "ORDER BY sku"
    )
    return _execute_query(sql)


def get_addresses() -> pd.DataFrame:
    """Broker-facing store addresses (voidfinder schema, seeded by
    cinderhaven-data-platform). Columns: store_id, street, city,
    state, zip."""
    sql = (
        "SELECT store_id, street, city, state, zip "
        "FROM voidfinder.store_addresses "
        "ORDER BY store_id"
    )
    return _execute_query(sql)

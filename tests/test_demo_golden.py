"""Demo golden lock — voidfinder.

voidfinder renders its demo from the Cinderhaven Postgres SSOT at runtime; it
commits no demo JSON to byte-lock (unlike the React tools in this program). So
the lock here is on the **engine**: a deterministic demo world is run through
``find_voids`` and its full exception frame is pinned two ways —

1. **Byte-lock** — SHA-256 of the committed golden CSV
   (``tests/golden/void_exceptions.csv``): the void engine's serialized output
   on the fixed world. Any change to detection, classification, dollarization,
   fixability, or sort order moves this and fails.
2. **Recompute-equality** — the test rebuilds the same world and re-runs the
   engine, asserting the live output equals the committed golden. So the golden
   cannot be quietly regenerated to match drifted code; the world builder and
   the artifact must agree.

Plus headline pins (total void dollars, run-rate, the basis-worded hero string)
that the client-mode conversion must not disturb — the conversion is purely
additive (a new ``client_mode.py`` + the shared POS-intake layer), so this holds.

If any assertion here fails, STOP: a demo golden moved. Do not re-baseline the
SHA without an explicit, logged approval — see the engagement-ready house rules.
"""
from __future__ import annotations

import hashlib
from datetime import timedelta
from pathlib import Path

import pandas as pd

from app.calculations import annualized_run_rate, find_voids
from app.layout import build_hero

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "void_exceptions.csv"

# SHA-256 of the committed golden, pinned 2026-08-05 against find_voids on the
# demo world below (12 voids: 6 never-scanned @ $780, 6 went-dark @ $640).
GOLDEN_SHA256 = "bff0299376d7669d39ba830b30d07e3f1866bbdd2d5d0f7c1a5608ca2e7ca2fa"

AS_OF = pd.Timestamp("2025-12-27")
_WEEKS = [AS_OF - timedelta(weeks=(51 - i)) for i in range(52)]
_EARLY = _WEEKS[0] - timedelta(weeks=8)

# Canonical Cinderhaven retailer roster (reference/canonical_values.json).
_RETAILERS = [
    ("RET-WMT", "Walmart", "Southeast", "GA", "high"),
    ("RET-COST", "Costco", "West", "CA", "high"),
    ("RET-WFM", "Whole Foods", "Northeast", "NY", "medium"),
    ("RET-SPR", "Sprouts", "Southwest", "AZ", "medium"),
    ("RET-KRG", "Kroger", "Midwest", "OH", "medium"),
    ("RET-RGL", "Regional Group", "Southeast", "FL", "low"),
]
_SKUS = ["CHP-AS-001", "CHP-PS-002", "CHP-SC-003"]


def build_demo_world():
    """A deterministic multi-retailer world exercising both void kinds,
    dollarization, comparable cohorts, and fixability. Constant velocities keep
    every median (and therefore every dollar) exact."""
    stores_rows, auth_rows, scan_rows = [], [], []
    sid = 0

    def add_store(rid, chain, region, state, tier):
        nonlocal sid
        sid += 1
        store_id = f"S{sid:03d}"
        stores_rows.append((store_id, rid, chain, region, state, tier))
        return store_id

    for rid, chain, region, state, tier in _RETAILERS:
        healthy = [add_store(rid, chain, region, state, tier) for _ in range(5)]
        for sku_i, sku in enumerate(_SKUS):
            units = 3 + sku_i
            dollars = 15.0 + 5 * sku_i
            for st in healthy:
                auth_rows.append((sku, st, _EARLY, None))
                for w in _WEEKS:
                    scan_rows.append((sku, st, w, units, dollars))
        nv = add_store(rid, chain, region, state, tier)     # never-scanned void
        auth_rows.append((_SKUS[0], nv, _EARLY, None))
        dk = add_store(rid, chain, region, state, tier)     # went-dark void
        auth_rows.append((_SKUS[1], dk, _EARLY, None))
        for w in _WEEKS[:20]:
            scan_rows.append((_SKUS[1], dk, w, 4, 20.0))

    stores = pd.DataFrame(stores_rows, columns=[
        "store_id", "retailer_id", "chain_name", "region", "state", "volume_tier"])
    auth = pd.DataFrame(auth_rows, columns=[
        "sku", "store_id", "authorized_date", "deauthorized_date"])
    auth["authorized_date"] = pd.to_datetime(auth["authorized_date"])
    auth["deauthorized_date"] = pd.to_datetime(auth["deauthorized_date"])
    scans = pd.DataFrame(scan_rows, columns=[
        "sku", "store_id", "week_ending", "units_sold", "dollars_sold"])
    scans["week_ending"] = pd.to_datetime(scans["week_ending"])
    return stores, auth, scans


def _serialize(voids: pd.DataFrame) -> str:
    out = voids.copy()
    for c in ("authorized_date", "last_scan_week"):
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d").fillna("")
    return out.to_csv(index=False, lineterminator="\n")


def test_golden_csv_sha256_is_unchanged():
    digest = hashlib.sha256(GOLDEN.read_bytes()).hexdigest()
    assert digest == GOLDEN_SHA256, (
        f"golden void_exceptions.csv changed (sha256 {digest} != "
        f"{GOLDEN_SHA256}). A demo golden moved — STOP and report before "
        "re-baselining."
    )


def test_engine_reproduces_the_golden():
    stores, auth, scans = build_demo_world()
    voids = find_voids(stores, auth, scans, as_of=AS_OF)
    assert _serialize(voids) == GOLDEN.read_text(encoding="utf-8"), (
        "find_voids output no longer matches the committed golden — the void "
        "engine drifted. STOP and report."
    )


def test_golden_headline_numbers():
    stores, auth, scans = build_demo_world()
    voids = find_voids(stores, auth, scans, as_of=AS_OF)
    # 6 never-scanned @ $780 + 6 went-dark @ $640 = $8,520.
    assert len(voids) == 12
    assert round(voids["void_dollars"].sum(), 2) == 8520.00
    assert (voids["void_type"] == "never_scanned").sum() == 6
    assert (voids["void_type"] == "went_dark").sum() == 6
    # Run-rate = sum of median weekly dollars * 52 (forward projection).
    assert annualized_run_rate(voids) == round(voids["median_weekly_dollars"].sum() * 52, 2)


def test_hero_prints_the_retail_scan_basis():
    """The hero dollar claim names its basis ('retail scan sales'). This is the
    Wave-1C basis-labeling guarantee; it must not regress in the conversion."""
    stores, auth, scans = build_demo_world()
    voids = find_voids(stores, auth, scans, as_of=AS_OF)
    hero = build_hero(voids, AS_OF)

    def _text(c):
        if c is None:
            return ""
        if isinstance(c, str):
            return c
        if isinstance(c, (list, tuple)):
            return "".join(_text(x) for x in c)
        return _text(getattr(c, "children", None))

    text = _text(hero)
    assert "in lost retail scan sales" in text
    assert "$8,520 in lost retail scan sales" in text

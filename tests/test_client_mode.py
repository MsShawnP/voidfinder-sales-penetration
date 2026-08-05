"""Client-mode + shared POS-intake tests for Void Finder (checklist §6).

Skipped unless the shared ``lailara_engagement`` lib is installed
(``pip install -e ../engagement-template/lib``): client mode is a local,
runtime-only path and never deploys, so it is not CI-gated. Fixtures are
generated on the fly — no client identifiers, no committed data.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("lailara_engagement")

import client_mode  # noqa: E402  (after importorskip)
from tests.test_demo_golden import build_demo_world  # noqa: E402


# ── helpers ─────────────────────────────────────────────────────────────────

def _write_trio(dirpath: Path, *, scans_name="scans.csv"):
    """Write a valid demo-shaped scans/auth/stores trio; return their paths."""
    stores, auth, scans = build_demo_world()
    auth = auth.copy()
    auth["authorized_date"] = pd.to_datetime(auth["authorized_date"]).dt.strftime("%Y-%m-%d")
    auth["deauthorized_date"] = (
        pd.to_datetime(auth["deauthorized_date"]).dt.strftime("%Y-%m-%d").fillna(""))
    scans = scans.copy()
    scans["week_ending"] = pd.to_datetime(scans["week_ending"]).dt.strftime("%Y-%m-%d")
    sp = dirpath / scans_name
    ap = dirpath / "auth.csv"
    stp = dirpath / "stores.csv"
    scans.to_csv(sp, index=False)
    auth.to_csv(ap, index=False)
    stores.to_csv(stp, index=False)
    return sp, ap, stp


def _write_config(dirpath: Path, *, columns=None, demo=True, name="Cinderhaven Provisions (demo)"):
    import yaml
    cfg = {
        "client": {"name": name},
        "engagement": {"id": "TEST-001"},
        "as_of_date": "2025-12-27",
        "prepared_by": "Lailara LLC",
        "demo": demo,
        "columns": columns or {},
    }
    p = dirpath / ("engagement.demo.yml" if demo else "engagement.yml")
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def _args(scans=None, auth=None, stores=None, products=None):
    return SimpleNamespace(scans=scans, auth=auth, stores=stores, products=products)


# ── happy path (the clean-file-renders-clean case) ──────────────────────────

def test_clean_trio_reproduces_engine_totals(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"
    res = client_mode.run(str(cfg), str(out), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "ok"
    # matches the engine golden ($8,520; run-rate 210*52).
    assert res["total_void_dollars"] == 8520.00
    assert res["n_voids"] == 12
    assert res["run_rate"] == 10920.00
    assert res["n_warnings"] == 0
    assert Path(res["report"]).is_file()
    assert Path(res["exceptions_csv"]).is_file()


def test_deliverable_prints_basis_window_and_draft(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"
    res = client_mode.run(str(cfg), str(out), _args(str(sp), str(ap), str(stp)))
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "$8,520 in lost retail scan sales" in html
    assert "Basis: retail-scan dollars" in html
    assert "Window: scan weeks" in html
    assert "DRAFT" in html                      # draft watermark until --final
    assert "Cinderhaven Provisions (demo)" in html
    assert "Config hash:" in html               # provenance footer


def test_final_flag_removes_draft(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"
    res = client_mode.run(str(cfg), str(out), _args(str(sp), str(ap), str(stp)), final=True)
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "DRAFT" not in html


# ── the readiness path (missing required column) ────────────────────────────

def test_missing_units_column_blocks_with_named_finding(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    pd.read_csv(sp).drop(columns=["units_sold"]).to_csv(sp, index=False)
    cfg = _write_config(tmp_path)
    out = tmp_path / "out"
    res = client_mode.run(str(cfg), str(out), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "blocked"
    assert res["blocked_files"] == ["scans"]
    report = Path(res["readiness_reports"]["scans"]).read_text(encoding="utf-8")
    assert "units_sold" in report
    assert "INPUT-SPEC §Scans" in report


# ── §6 adversarial intake ────────────────────────────────────────────────────

def test_bom_semicolon_scans_still_reads(tmp_path):
    # UTF-8 BOM, semicolon delimiter, whitespace headers, leading blank row.
    sp, ap, stp = _write_trio(tmp_path)
    df = pd.read_csv(sp)
    body = "\n" + df.to_csv(index=False, sep=";")
    body = body.replace("store_id;", " store_id ;", 1)
    sp.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "ok"
    assert res["total_void_dollars"] == 8520.00


def test_excel_mangled_store_id_recovered_as_text(tmp_path):
    from openpyxl import Workbook
    sp, ap, stp = _write_trio(tmp_path)
    # Rebuild the store file as XLSX with a numeric store id Excel widened to float.
    stores = pd.read_csv(stp, dtype=str)
    xp = tmp_path / "stores.xlsx"
    wb = Workbook(); ws = wb.active
    ws.append(list(stores.columns))
    for _, r in stores.iterrows():
        ws.append([r[c] for c in stores.columns])
    # append one store with a float-typed id and reference it nowhere critical
    wb.save(xp)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(xp)))
    assert res["status"] == "ok"


def test_client_headers_mapped_via_engagement_yml(tmp_path):
    stores, auth, scans = build_demo_world()
    auth = auth.copy()
    auth["authorized_date"] = pd.to_datetime(auth["authorized_date"]).dt.strftime("%Y-%m-%d")
    auth["deauthorized_date"] = (
        pd.to_datetime(auth["deauthorized_date"]).dt.strftime("%Y-%m-%d").fillna(""))
    scans = scans.copy()
    scans["week_ending"] = pd.to_datetime(scans["week_ending"]).dt.strftime("%Y-%m-%d")
    # Rename scan headers to a client's vocabulary.
    scans = scans.rename(columns={
        "store_id": "Store #", "sku": "Item Code", "week_ending": "Wk End",
        "units_sold": "Scan Units", "dollars_sold": "Scan $"})
    sp = tmp_path / "scans.csv"; scans.to_csv(sp, index=False)
    ap = tmp_path / "auth.csv"; auth.to_csv(ap, index=False)
    stp = tmp_path / "stores.csv"; stores.to_csv(stp, index=False)
    cfg = _write_config(tmp_path, columns={
        "store_id": "Store #", "sku": "Item Code", "week_ending": "Wk End",
        "units_sold": "Scan Units", "dollars_sold": "Scan $"})
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "ok"
    assert res["total_void_dollars"] == 8520.00


def test_deauthorized_column_absent_is_tolerated(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    pd.read_csv(ap).drop(columns=["deauthorized_date"]).to_csv(ap, index=False)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    assert res["status"] == "ok"
    assert res["total_void_dollars"] == 8520.00


def test_products_absent_disclosed_as_limitation(tmp_path):
    sp, ap, stp = _write_trio(tmp_path)
    cfg = _write_config(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "No products file" in html


def test_as_of_before_scan_window_errors(tmp_path):
    import yaml
    sp, ap, stp = _write_trio(tmp_path)
    cfg = tmp_path / "engagement.demo.yml"
    cfg.write_text(yaml.safe_dump({
        "client": {"name": "Cinderhaven Provisions (demo)"},
        "engagement": {"id": "TEST-001"},
        "as_of_date": "2020-01-01",   # before every scan week
        "demo": True, "columns": {},
    }), encoding="utf-8")
    with pytest.raises(SystemExit):
        client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(sp), str(ap), str(stp)))

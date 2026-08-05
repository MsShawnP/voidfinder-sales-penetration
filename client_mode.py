"""Client-mode CLI for Void Finder.

Runs the void engine (`app/calculations.py`) on a client's own POS data instead
of the Cinderhaven demo database, via the shared ``lailara_engagement`` scaffold
and its POS-intake layer (`lailara_engagement.pos`):

  * three required inputs — weekly **scans**, the **authorization** log, and the
    **store** dimension (plus an optional **products** master) — each read with
    the tolerant CSV/XLSX reader (identifiers as text, dates faithfully parsed);
  * a preflight per file that maps client headers to the canonical POS contract
    via ``engagement.yml`` and blocks with a branded **Data Readiness Report**
    naming any missing required column (no silent coercion);
  * the void exception work list computed by the same tested engine the demo
    uses, with every dollar figure printed next to its **basis** (retail-scan
    dollars, median comparable-store velocity) and **window** (the scan span,
    as of the config date);
  * a branded, provenance-footed, draft-watermarked ``Void Exception Work List``
    plus the ranked exceptions as CSV — written to ``client-output/`` only,
    never committed, never deployed.

Demo mode (the deployed app) is untouched: this file is additive and imports the
engine read-only.

Usage:
    python client_mode.py --config engagement.yml [--out client-output] [--final]
    # inputs come from engagement.yml `inputs:`, or override on the CLI:
    python client_mode.py --config engagement.yml \
        --scans client-data/scans.csv --auth client-data/auth.csv \
        --stores client-data/stores.csv [--products client-data/products.csv]
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import pandas as pd

from app import calculations
from lailara_engagement import (
    build_provenance,
    load_config,
    pos,
    read_table,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.provenance import Provenance

TOOL = "voidfinder"
TOOL_VERSION = "1.0"


def _basis_label(scan_basis: str) -> str:
    """The basis every void dollar is computed on — derived from config, not prose."""
    return (f"{pos.scan_basis_label(scan_basis)} dollars · "
            "median comparable-store weekly velocity × void weeks")


def _resolve_inputs(config, args) -> dict[str, str | None]:
    """CLI flags override engagement.yml `inputs:`; returns absolute-ish paths."""
    cfg_inputs = config.raw.get("inputs") or {}
    return {
        "scans": args.scans or cfg_inputs.get("scans"),
        "authorizations": args.auth or cfg_inputs.get("authorizations") or cfg_inputs.get("auth"),
        "stores": args.stores or cfg_inputs.get("stores"),
        "products": args.products or cfg_inputs.get("products"),
    }


def _fmt_dollars(v) -> str:
    return "—" if v is None else f"${v:,.0f}"


def _window_label(scans: pd.DataFrame, as_of: pd.Timestamp) -> str:
    first = scans["week_ending"].min()
    last = scans["week_ending"].max()
    return (f"scan weeks {first.strftime('%b %d, %Y')} – {last.strftime('%b %d, %Y')} "
            f"· as of {as_of.strftime('%b %d, %Y')}")


def _deliverable_html(config, voids, rollups, run_rate, window_label,
                      basis_label, basis_word, limitations, provenance: Provenance,
                      *, draft: bool) -> str:
    esc = html.escape
    draft_class = " ll-draft" if draft else ""
    total = round(float(voids["void_dollars"].sum()), 2)
    n_voids = len(voids)
    n_stores = int(voids["store_id"].nunique())

    def _rollup_table(title, df, key_label):
        rows = "".join(
            f"<tr><td>{esc(str(r[df.columns[0]]) if not isinstance(r.get('label'), str) else r['label'])}</td>"
            f"<td class=num>{int(r['void_count']):,}</td>"
            f"<td class=num>{int(r['store_count']):,}</td>"
            f"<td class=num>{_fmt_dollars(r['void_dollars'])}</td></tr>"
            for _, r in df.iterrows()
        )
        return f"""
<section class=ll-section>
  <h2 class=ll-h2>{esc(title)}</h2>
  <table class=ll-table><thead><tr><th>{esc(key_label)}</th><th>Voids</th>
  <th>Stores</th><th>Void $</th></tr></thead><tbody>{rows}</tbody></table>
</section>"""

    # Top exceptions (ranked by priority = void$ × fixability).
    top = voids.head(25)
    name_col = "product_name" if "product_name" in voids.columns else "sku"
    ex_rows = "".join(
        f"<tr><td>{esc(str(r['store_id']))}</td><td>{esc(str(r.get('chain_name','')))}</td>"
        f"<td>{esc(str(r[name_col]))}</td><td>{esc(str(r['void_type']).replace('_',' '))}</td>"
        f"<td class=num>{int(r['void_weeks'])}</td>"
        f"<td class=num>{_fmt_dollars(r['void_dollars'])}</td>"
        f"<td class=num>{_fmt_dollars(r['priority'])}</td></tr>"
        for _, r in top.iterrows()
    )
    lim_html = "".join(f"<li>{esc(x)}</li>" for x in limitations)

    retailer_tbl = _rollup_table("Void dollars by retailer", rollups["retailer"], "Retailer")
    region_tbl = _rollup_table("Void dollars by region", rollups["region"], "Region")
    type_tbl = _rollup_table("Void dollars by type", rollups["void_type"], "Void type")

    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Void Exception Work List — {esc(config.client_name)}</title>
<style>{_css(draft)}</style></head>
<body class="{draft_class.strip()}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · Void Finder</div>
  <h1 class=ll-title>Void Exception Work List</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>As of</span> {esc(config.as_of_date.isoformat())}</div>
    <div><span class=ll-k>Prepared by</span> {esc(config.prepared_by)}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{_fmt_dollars(total)} in lost {esc(basis_word)} sales</div>
  <div>{n_voids:,} item-store voids across {n_stores:,} stores
       · {_fmt_dollars(run_rate)}/yr run-rate if nothing changes</div>
  <div class=ll-basis>Basis: {esc(basis_label)}<br>Window: {esc(window_label)}</div>
</section>
{type_tbl}
{retailer_tbl}
{region_tbl}
<section class=ll-section>
  <h2 class=ll-h2>Top exceptions (ranked by priority = void $ × fixability)</h2>
  <table class=ll-table><thead><tr><th>Store</th><th>Banner</th><th>Item</th>
  <th>Type</th><th>Weeks</th><th>Void $</th><th>Priority</th></tr></thead>
  <tbody>{ex_rows}</tbody></table>
  <p class=ll-note>Full ranked list exported to the accompanying CSV.</p>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Data limitations</h2>
  <ul class=ll-limitations>{lim_html}</ul>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}
*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:34px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_RED_SURFACE};color:{P.LL_RED_DARK}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:22px}}
.ll-basis{{font-size:12px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-note{{font-size:13px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-table{{width:100%;border-collapse:collapse;font-size:14px}}
.ll-table th{{text-align:left;background:{P.LL_CHICAGO};color:#fff;padding:8px 12px}}
.ll-table td{{padding:8px 12px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-limitations{{margin:0;padding-left:20px}}.ll-limitations li{{margin-bottom:6px}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);
padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def _labelled_rollup(voids: pd.DataFrame, by: str) -> pd.DataFrame:
    """calculations.rollup + a single display 'label' column per grouping."""
    agg = calculations.rollup(voids, by)
    if by == "retailer":
        agg["label"] = agg["chain_name"].astype(str)
    elif by == "region":
        agg["label"] = agg["region"].astype(str)
    elif by == "void_type":
        agg["label"] = agg["void_type"].astype(str).str.replace("_", " ")
    else:
        agg["label"] = agg[agg.columns[0]].astype(str)
    return agg


def run(config_path: str, out_dir: str, args, *, final: bool = False) -> dict:
    config = load_config(config_path)
    inputs = _resolve_inputs(config, args)

    # Required POS declarations (raise a clear ConfigError if absent) — every
    # dollar's basis and the week grid are declared, not re-derived.
    week_conv_name, _week_weekday = pos.resolve_week_convention(config)
    scan_basis = pos.resolve_scan_basis(config)
    basis_label = _basis_label(scan_basis)
    basis_word = pos.scan_basis_label(scan_basis)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # --- Intake + preflight each required file --------------------------------
    required = {
        "scans": pos.scan_spec(tool=TOOL, version=TOOL_VERSION, week_convention=week_conv_name),
        "authorizations": pos.authorization_spec(tool=TOOL, version=TOOL_VERSION),
        "stores": pos.store_spec(tool=TOOL, version=TOOL_VERSION),
    }
    reads: dict[str, object] = {}
    reports: dict[str, object] = {}
    frames: dict[str, pd.DataFrame] = {}
    missing_files = [k for k, v in inputs.items() if k in required and not v]
    if missing_files:
        raise SystemExit(
            f"missing required input(s): {', '.join(missing_files)}. Provide them "
            f"via --{'/--'.join(missing_files)} or engagement.yml `inputs:`."
        )

    for key, spec in required.items():
        read = read_table(inputs[key])
        report, frame = pos.intake(read, spec, config)
        reads[key] = read
        reports[key] = report
        frames[key] = frame

    # Surface the declared week convention + scan basis on the scans report.
    reports["scans"].disclosures.extend(pos.declared_disclosures(week_conv_name, scan_basis))

    blocked = {k: r for k, r in reports.items() if not r.passed}
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION,
        inputs=[reads[k] for k in required],
        config=config,
        validation_status=validation_status_label(
            "failed" if blocked else "clean",
            sum(r.n_warnings for r in reports.values()),
        ),
        extra={"Week convention": week_conv_name, "Scan basis": f"{basis_word} dollars"},
    )

    if blocked:
        written = {}
        for key, report in blocked.items():
            paths = write_report(
                report, config, str(out), provenance=provenance, draft=not final,
                basename=f"data-readiness-{key}",
                title=f"Void Finder Data Readiness Report — {key}",
            )
            written[key] = paths["html"]
        return {"status": "blocked", "blocked_files": list(blocked),
                "readiness_reports": written}

    # --- Assemble engine frames ----------------------------------------------
    scans = frames["scans"]
    auth = frames["authorizations"]
    stores = frames["stores"]
    # find_voids reads auth["deauthorized_date"]; guarantee the column exists.
    if "deauthorized_date" not in auth.columns:
        auth["deauthorized_date"] = pd.NaT

    as_of = pd.Timestamp(config.as_of_date)
    weeks_at_or_before = (scans["week_ending"] <= as_of).sum()
    if weeks_at_or_before == 0:
        raise SystemExit(
            f"as_of_date {config.as_of_date} precedes every scan week "
            f"({scans['week_ending'].min().date()} – {scans['week_ending'].max().date()}); "
            "set an as_of_date within the scan window."
        )

    voids = calculations.find_voids(stores, auth, scans, as_of=as_of)

    # Optional product names for display.
    limitations: list[str] = []
    if inputs.get("products"):
        pread = read_table(inputs["products"])
        # products has only sku required; reuse a light spec.
        from lailara_engagement import ColumnSpec, PreflightSpec, run_preflight
        pspec = PreflightSpec(tool=TOOL, version=TOOL_VERSION, columns=[
            ColumnSpec(name="sku", dtype="identifier", required=True, spec_ref="INPUT-SPEC §Products"),
            ColumnSpec(name="product_name", dtype="string", required=False, allow_blank=True),
            ColumnSpec(name="product_line", dtype="string", required=False, allow_blank=True),
        ])
        preport = run_preflight(pread, pspec, config)
        if preport.passed:
            pframe = pos.to_frame(pread, preport, pspec)
            if not voids.empty and "product_name" in pframe.columns:
                voids = voids.merge(pframe[["sku", "product_name"]], on="sku", how="left")
        else:
            limitations.append("Products file failed preflight — items labeled by SKU code.")
    else:
        limitations.append("No products file — items labeled by SKU code.")

    run_rate = calculations.annualized_run_rate(voids)
    window_label = _window_label(scans, as_of)

    # Warnings from any file become data-limitation lines.
    for key, report in reports.items():
        for f in report.findings:
            if f.severity == "warning":
                limitations.append(f"[{key}] {f.message}")
    if voids.empty:
        limitations.append("No qualifying voids at the chosen parameters "
                           "(N consecutive zero-scan weeks, above the slow-mover floor).")

    rollups = {b: _labelled_rollup(voids, b) for b in ("retailer", "region", "void_type")}

    # --- Write deliverables (client-output only) ------------------------------
    csv_path = out / "void-exceptions.csv"
    voids.to_csv(csv_path, index=False)
    html_path = out / "void-exception-work-list.html"
    html_path.write_text(
        _deliverable_html(config, voids, rollups, run_rate, window_label,
                          basis_label, basis_word, limitations, provenance, draft=not final),
        encoding="utf-8",
    )

    return {
        "status": "ok",
        "n_voids": len(voids),
        "total_void_dollars": round(float(voids["void_dollars"].sum()), 2) if not voids.empty else 0.0,
        "run_rate": round(run_rate, 2),
        "report": str(html_path),
        "exceptions_csv": str(csv_path),
        "n_warnings": sum(r.n_warnings for r in reports.values()),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="voidfinder client mode",
        description="Run the void engine on a client's POS data in engagement mode.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--scans")
    ap.add_argument("--auth")
    ap.add_argument("--stores")
    ap.add_argument("--products")
    ap.add_argument("--out", default="client-output")
    ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.out, args, final=args.final)
    if result["status"] == "blocked":
        print("BLOCKED — data not ready. Readiness report(s):")
        for key, path in result["readiness_reports"].items():
            print(f"  {key}: {path}")
        return 3
    print(f"{result['n_voids']:,} voids · {_fmt_dollars(result['total_void_dollars'])} "
          f"in lost retail scan sales · {_fmt_dollars(result['run_rate'])}/yr run-rate"
          + (f" · {result['n_warnings']} warning(s)" if result["n_warnings"] else ""))
    print(f"report -> {result['report']}\ncsv    -> {result['exceptions_csv']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

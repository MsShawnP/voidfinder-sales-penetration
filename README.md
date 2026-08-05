# Void Finder — Dollarized Distribution Voids, Ranked for Action

**Live:** https://voidfinder.lailarallc.com

Void Finder answers one question: where are we authorized but not selling, and what is each gap costing us? Tool #5 of the Cinderhaven sales-penetration series.

## What it does

- Scans the Cinderhaven authorization matrix against weekly POS scan data and flags every store where an authorized item is not scanning
- Classifies each void: **never-scanned** (the shelf set never happened) vs **went-dark** (distribution quietly decaying)
- Dollarizes every void from median comparable-store velocity, so gaps rank by money rather than by count
- Produces a ranked, broker-ready exception work list with a formatted Excel export

Three views:

- **Rollup** — total void dollars by item, banner, region, and void type; the exec-slide number and the one pattern worth fixing first
- **Trend** — void count over time: is the problem growing, stable, or fixed?
- **Exceptions** — the store-level, ranked, dollarized work list

## Cinderhaven context

Built on the Cinderhaven synthetic dataset — a ~$25M (wholesale) specialty food brand, 50 SKUs across 5 product lines and 6 contracted retailers. Data is synthetic; methodology and deliverables are real.

## Why it matters

Authorization is revenue that was already won in the buyer meeting. Every authorized-but-not-scanning store is money the sales team earned and the shelf never collected — and it fails silently, because total sales reports don't distinguish a store that never set the item from one that quietly dropped it. Void Finder turns that invisible leak into a dollar figure per store and a prioritized list a broker can execute on their next store visit.

## Quick start

Requires Python 3.11+ and a `DATABASE_URL` pointing at the Cinderhaven SSOT Postgres instance.

```
# .env in the repo root
DATABASE_URL=postgres://user:password@host:5432/cinderhaven

pip install -e ".[dev]"
python wsgi.py        # http://localhost:8050
pytest                # run the test suite
```

Operational endpoints: `/health` (liveness — never touches the database) and `/ready` (readiness — reports database connectivity and data availability).

## Tech stack

- **Application:** Dash 4.2, Plotly 6.8, Python 3.11
- **Data:** pandas, numpy, psycopg2 (pooled connections to Cinderhaven Postgres)
- **UI:** dash-ag-grid (exception work list), Lailara brand frame
- **Export:** openpyxl (styled Excel workbook)
- **Deploy:** Gunicorn, Docker, Fly.io (iad region, auto-stop machines)

## Project structure

```
app/
  views/          rollup, trend, exceptions
  calculations.py void detection, classification, dollarization
  export.py       Excel work-list export
  db.py           Postgres pool, query timeout, graceful degradation
wsgi.py           entry point + health/readiness endpoints
analysis/         one-off impact analyses
tests/            pytest suite
```

## Client engagement use

Void Finder runs on a client's own POS data via an in-place **client mode** —
same engine, same math, client data at runtime only (never committed, never
deployed). It reuses the shared `lailara_engagement` scaffold and its POS-intake
layer.

```
pip install -e ../engagement-template/lib      # the shared scaffold
python client_mode.py --config engagement.yml  # inputs from engagement.yml `inputs:`
```

Three required inputs (weekly **scans**, the **authorization** log, the **store**
dimension; **products** optional) are validated by a preflight that maps the
client's headers to the canonical POS contract via `engagement.yml`. A missing
required column produces a branded **Data Readiness Report** naming exactly
what's missing instead of a result. A clean run writes a draft-watermarked,
provenance-footed **Void Exception Work List** (HTML) plus the ranked exceptions
(CSV) to `client-output/`. Add `--final` to drop the draft watermark.

See [`INPUT-SPEC.md`](INPUT-SPEC.md) for the full column contract and the
`engagement.yml` mapping. Demo mode (the deployed site) is unchanged: client mode
is additive and imports the engine read-only.

## License

MIT

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.

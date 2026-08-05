# Void Finder — Client Data Input Specification

What a client must provide for a Void Finder engagement, derived from the engine
(`app/calculations.py`, `app/db.py`), not from prose. Void Finder finds stores
where an item is **authorized but not scanning**, dollarizes each gap from the
median velocity of comparable scanning stores, and ranks the result. That needs
three tables: weekly **scans**, the **authorization** (distribution) log, and the
**store** dimension. A fourth, **products**, is optional (item names for display).

Column **names** below are the canonical schema. Your headers can differ — map
them in `engagement.yml` under `columns:` (see "Column mapping"). Identifiers
(store id, item id) are read as **text**, so leading zeros are preserved; provide
them as text to be safe. All three required files are validated by a preflight
before any analysis runs; a missing required column produces a **Data Readiness
Report** naming exactly what's missing, not a result.

The canonical column contract is shared across the sales-penetration tool family
(`lailara_engagement.pos`); the same names work for Door Math, Spin Rate, and
Decompose.

---

## §Scans — weekly POS scan movement (required file)

One row per (store, item, week). This is the movement/velocity feed.

| Column | Type | Required | Used for |
|---|---|---|---|
| `store_id` | identifier (text) | **required** | joins to authorizations + stores; the void is per store |
| `sku` | identifier (text) | **required** | the item; joins to authorizations + products |
| `week_ending` | date | **required** | the weekly grid; void duration and the trailing velocity window |
| `units_sold` | number ≥ 0 | **required** | comparable-store weekly velocity; the slow-mover floor |
| `dollars_sold` | number ≥ 0 | **required** | dollarizes each void (median comparable weekly dollars × void weeks) |
| `retailer_id` | identifier (text) | optional | banner; normally taken from the store dimension instead |

Notes: a week with no scan for a (store, item) is represented by the **absence**
of a row, not a zero row (zero rows are tolerated but not required). Dates may be
`YYYY-MM-DD`, `MM/DD/YYYY`, `DD-Mon-YYYY`, or Excel dates; mixed formats within a
column are disclosed, never silently reconciled.

## §Authorizations — the distribution log (required file)

One row per (item, store) authorization. Drives the denominator: a void can only
exist where the item is authorized.

| Column | Type | Required | Used for |
|---|---|---|---|
| `sku` | identifier (text) | **required** | the authorized item |
| `store_id` | identifier (text) | **required** | the authorized store |
| `authorized_date` | date | **required** | when authorization began; never-scanned void duration is measured from here |
| `deauthorized_date` | date | optional | when authorization ended; **blank = still authorized**. Absent column ⇒ all authorizations treated as active |

## §Stores — the store dimension (required file)

One row per store. Supplies the segmentation the comparable-store cohorts use.

| Column | Type | Required | Used for |
|---|---|---|---|
| `store_id` | identifier (text) | **required, unique** | the store key |
| `retailer_id` | identifier (text) | **required** | retailer rollup; never-scanned cluster detection |
| `chain_name` | string | **required** | banner label on the deliverable |
| `region` | string | **required** | comparable-cohort segmentation (tier+region → tier → region → all) |
| `state` | identifier (text) | required (blanks tolerated) | the state rollup / map |
| `volume_tier` | string | **required** | comparable-cohort segmentation (e.g. high / medium / low) |

## §Products — item master (optional file)

| Column | Type | Required | Used for |
|---|---|---|---|
| `sku` | identifier (text) | **required if file provided** | join key |
| `product_name` | string | optional | display name (else the SKU code is shown) |
| `product_line` | string | optional | grouping |

Absent ⇒ items are labeled by SKU code; disclosed as a data limitation.

---

## Column mapping (`engagement.yml`)

Map your headers to the canonical names — never edit code. Point the run at your
three files under `inputs:`:

```yaml
client:
  name: Your Brand
engagement:
  id: YB-2026-08
as_of_date: 2026-06-27        # the reporting anchor; never today's date

basis:
  week_convention: week_ending_saturday   # REQUIRED: iso_week_ending_sunday | week_ending_saturday | retail_454
  scan_basis: retail_scan                 # REQUIRED: retail_scan | wholesale

inputs:
  scans: client-data/scans.csv
  authorizations: client-data/auth.csv
  stores: client-data/stores.csv
  products: client-data/products.csv   # optional

# canonical_name: "Your header"  — only the ones that differ
columns:
  store_id: "Store #"
  sku: "Item Code"
  week_ending: "Week Ending"
  units_sold: "Scan Units"
  dollars_sold: "Scan $"
  authorized_date: "Auth Date"
  volume_tier: "Volume Band"
```

### Required declarations (`basis:`)

- **`week_convention`** — which weekday `week_ending` falls on. Every value is
  **validated** against it; a stray off-weekday date is a named finding, not a
  silent pass (this is what stops a re-derived week grid from drifting). The
  convention is disclosed on the readiness report and in the provenance footer.
- **`scan_basis`** — `retail_scan` or `wholesale`. Carried into the provenance
  footer and printed next to every dollar, so the basis is structural, never
  assumed. Void Finder dollarizes scan movement, so `retail_scan` is the norm.

The scans grain `(store_id, sku, week_ending)` must be **unique** (a duplicate
row would double revenue) and `deauthorized_date` must not precede
`authorized_date` — both are validated.

Unmatched headers are auto-mapped only on an exact case/whitespace-insensitive
match, and every auto-map is disclosed on the report. Anything still unresolved
that is **required** blocks the run with a named finding.

# Void Finder — Fable / Claude Code build brief

Paste this to Claude Code. Attach `voidfinder-build-brainstorm.md` alongside it.

```
Build Void Finder — tool #5 of the Cinderhaven sales-penetration series. The full
brainstorm is in the attached voidfinder-build-brainstorm.md — read it first; this
brief is the actionable summary.

WHAT IT IS
"Where are we authorized but not selling, and what is each gap costing us?" A void =
a store authorized to carry an item where it isn't scanning. Output is a ranked,
dollarized work list ("send your broker to these 84 stores"). This is the most
client-shaped tool in the series.

HARD DEPENDENCY — REUSE, DON'T REBUILD
Read the doormath repo first. Void Finder reuses Door Math's existing data model:
store universe (640 doors: banner, region, volume tier), authorization matrix
(item x door), and POS scan data (item x store x week). Import/share it — do not
generate a second, drifting copy. Confirm the packaging approach early (shared
cinderhaven-store-universe package preferred; standalone repo reading the same locked
canonical data if that's cleaner).

CORE LOGIC
- Void definition: authorized + zero scans for N consecutive weeks. N is a PARAMETER,
  not a constant. Exclude slow movers (1 unit/month is not a void).
- Classify: never-scanned (likely never set) vs went-dark (was scanning, stopped).
- Dollarize: expected sales per void store = MEDIAN velocity of comparable scanning
  stores (same volume tier + region) x void weeks. Median, not mean — reuse the
  comparable-store logic from the short-ship-cost project. State the assumption in-app.
- Prioritize: rank by dollar opportunity x fixability.

SEED THE DEMO
Add both void types to the Cinderhaven store universe: a regional CLUSTER of
never-scanned stores (botched mod reset — the "aha", voids aren't random) plus
scattered went-dark stores.

OUTPUTS
1. Void exception report: item x store, void type, duration, dollarized opportunity.
2. Summary rollup: total void dollars by item / banner / region (the exec-slide number).
3. Trend: void count over time.
4. Broker-ready export (CSV/Excel, store numbers + addresses) — end user is a field
   rep, not an analyst. Use the multi-tab verified-figures export pattern from the
   trade-spend diagnostic.

STACK — MIRROR SPIN RATE (clone the shell, don't reinvent)
Dash 3.x, Plotly 6.0, Python 3.11, pandas, psycopg2 -> cinderhaven-db (SSOT Postgres),
dash-ag-grid for tables, Gunicorn + Docker + Fly.io (shared-cpu-1x, iad).

NON-NEGOTIABLE LESSONS FROM THE #1/#2 SESSIONS
- Do NOT hard-gate /health on the DB. If the DB is down, serve the branded shell +
  "data temporarily unavailable"; keep a SEPARATE readiness signal. (This is the exact
  bug that took Spin Rate to an external 503.)
- Wire DATABASE_URL into the synced credential set (canonical creds in
  cinderhaven-data-platform/.env, gitignored) so this app never repeats the desync.
- Ship a branded pre-hydration loading state (no blank white first paint).
- Test to Spin Rate's bar; unit-test the dollarization and void-classification logic
  hard — a wrong opportunity number kills credibility.

PULL FROM SOURCE (don't guess)
- Door Math's actual data-model schema (table/column names) — from the doormath repo.
- The short-ship-cost comparable-store dollarization function — reuse it.

DELIVERABLES
- Working repo, tests green, HANDOFF.md written.
- Deployed to a subdomain (default voidfinder.lailarallc.com unless Shawn picks
  ghostshelf/darkdoors — match repo name to subdomain).
- A Work-page card in the same format as Door Math / Spin Rate, added after them.
- Report back with the live URL and confirm the exception report renders real
  dollarized voids from Cinderhaven data.

CONFIRM WITH SHAWN before deploy: (1) name/subdomain, (2) packaging choice if it means
refactoring doormath.
```

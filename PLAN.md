# Void Finder — Current Work Plan

The current arc of work. Updated when the arc changes, not every
session. For session-by-session state, see HANDOFF.md.

---

## Goal

Ship Void Finder v1: a Dash app at voidfinder.lailarallc.com that
finds authorized-but-not-scanning stores in Cinderhaven data,
classifies each void (never-scanned vs went-dark), dollarizes it from
median comparable-store velocity (same volume tier + region), and
exports a ranked, broker-ready work list — tests green, deployed,
Work-page card added.

## Why this arc, why now

Tool #5 of the Cinderhaven sales-penetration series — the most
client-shaped tool in the series. Doormath (#1) and Spin Rate (#2)
are live; this completes the authorized-vs-selling story.

## Business question this arc answers

Where are we authorized but not selling, and what is each gap
costing us?

## Scoping decisions (2026-07-02, confirmed by Shawn — see DECISIONS.md)

1. **Packaging:** install `cinderhaven-store-universe` directly from
   doormath's repo subdirectory. No doormath refactor.
2. **Dollarization:** build fresh (short-ship-cost has no reusable
   comparable-store logic). Median velocity of comparable scanning
   stores, same volume tier + region. Heavy unit tests.
3. **Void seeding:** into cinderhaven-db ONLY, following Spin Rate's
   seeding pattern in cinderhaven-data-platform. Do NOT touch
   doormath's generator or locked canonical figures.
   - Rider A: document doormath (in-memory) vs cinderhaven-db
     row-level divergence in HANDOFF.md.
   - Rider B: compute how much doormath's locked ACV/TDP figures
     WOULD shift under unified seeding — ANALYSIS ONLY, change
     nothing in doormath.

## Tasks

Vertical slices, in order:

- [x] 1. Recon: Spin Rate shell anatomy (layout, /health pattern,
      loading state, DB module, Docker/fly config) + cinderhaven-db
      schema (what tables exist, how Spin Rate seeds)
- [x] 2. Data foundation: install cinderhaven-store-universe from
      doormath subdirectory; seed script in cinderhaven-data-platform
      that writes universe + auth matrix + scans WITH seeded voids
      (regional never-scanned cluster = botched mod reset; scattered
      went-dark stores) to cinderhaven-db
- [x] 3. Core logic + tests: void detection (N consecutive weeks,
      parameterized), slow-mover exclusion, classification
      (never-scanned vs went-dark), median comparable-store
      dollarization, fixability ranking — unit-tested hard BEFORE
      any UI
- [x] 4. App shell: clone Spin Rate pattern — branded pre-hydration
      loading state, /health NOT gated on DB, separate readiness,
      Lailara design system + deployed-UI gate
- [x] 5. View: void exception report (item x store, type, duration,
      dollars) with dash-ag-grid
- [x] 6. View: summary rollup (total void $ by item/banner/region)
- [x] 7. View: void-count trend over time
- [x] 8. Broker export: multi-tab verified-figures Excel/CSV pattern
      from trade-spend diagnostic (store numbers + addresses)
- [x] 9. Rider B analysis: option-(b) canonical-figure impact report
      (analysis/RIDER-B-option-b-impact.md)
- [x] 10. Deploy: Docker + Fly.io (shared-cpu-1x, iad), DATABASE_URL
      from synced credential set — live at voidfinder.lailarallc.com
      since 2026-07-04
- [ ] 11. Work-page card on lailara-website (same format as Door
      Math / Spin Rate, placed after them) — WRITTEN AND LOCAL, not
      pushed. Pushing auto-publishes via GH Actions, so it waits on
      Shawn's OK. The only open item in this arc.
- [x] 12. HANDOFF.md: divergence documentation (Rider A) + wrap

### Un-pinned defects — tests are waiting, fixes are not written

Added 2026-07-28 by the FIX-LIST cross-repo test sweep. Each has a
strict-xfail test asserting the corrected behaviour, so the suite fails
loudly the moment the fix lands and the marker has to come off. Do not
remove a marker without doing the fix.

- [x] **Workbook total is not period-clipped.** Fixed 2026-07-28 along
      with the second half of the same defect: the exception grid's
      Opportunity/Priority columns and the state choropleth were also
      un-clipped while the rollup clipped, so the two pages disagreed.
      One basis now: `calculations.apply_period` clips dollars and
      priority together, and the hero, the "Lost so far" KPI, the grid,
      the map, the rollup charts, and both workbook tabs all read
      through it. The workbook parameter line states the period.
- [x] **Margin-equivalent sentence is dimensionally invalid.** Fixed
      2026-07-28 by cutting it (Shawn's call). `_fmt_margin_equiv` is
      gone. Cinderhaven has no canonical contribution-margin figure —
      only 87¢ net-collected per wholesale dollar and an 11% EBITDA
      check — so no defensible multiple existed to compute. The why
      panel now states the period total and stops; the qualitative
      argument (authorization and slotting already paid) carries the
      point without an invented ratio.

## Out of scope for this arc

- Refactoring doormath in any way (incl. extracting the package to
  its own repo)
- Modifying locked canonical figures or the shared generator
- Applying option-(b) unification (analysis only)
- Real (non-Cinderhaven) client data connectors

## Definition of done for this arc

- [x] All dollarization + classification unit tests green
- [x] Exception report renders real dollarized voids from
      cinderhaven-db, including the regional never-scanned cluster
- [x] Live at the confirmed subdomain; /health returns 200 with DB
      down; branded loading state on first paint
- [x] Broker export downloads with store numbers + addresses
- [ ] Work-page card live after Door Math / Spin Rate — see task 11
- [x] Rider A + B documented; HANDOFF.md current

---

## Arc history

When an arc completes, archive its goal, completion date, and outcome
here. Then start a new arc above. Provides continuity without bloating
the active plan.

---

## Improvement history

Track when this project was reviewed and improved via /improve.
Each entry records what was found, what was fixed, and when to
check again.

<!-- Entries are added by /improve — don't delete this section -->

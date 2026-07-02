# Void Finder — Handoff Log

Session-by-session state. Updated by /log mid-session and /wrap at
session end.

For durable choices, see DECISIONS.md.
For the current work arc, see PLAN.md.
For things that didn't work, see FAILURES.md.

---

## 2026-07-02 (later) — Core build complete; seeding blocked on Docker

**Started from:** /clarify complete, three scoping decisions confirmed
(see DECISIONS.md), "proceed with the build."

**Did:**
- Recon of Spin Rate shell, cinderhaven-db schema/seeding, trade-spend
  export pattern (3 subagent reports).
- Core logic (`app/calculations.py`): parameterized-N void detection,
  never-scanned vs went-dark classification, median tier+region
  comparable dollarization with widening basis, slow-mover exclusion,
  fixability + cluster ranking, weekly trend. 27 unit tests pin exact
  hand-computed numbers.
- App shell cloned from Spin Rate (pool/db.py, branded pre-hydration
  overlay, Lailara frame/CSS/fonts). DELIBERATE DIVERGENCE: /health is
  liveness-only (always 200); DB state lives at /ready; fly.toml
  points at /health. This is the fix for the Spin Rate external-503
  lesson — do not "simplify" them back together.
- Three views (exception grid + KPIs + cluster callout, rollup charts,
  26-week trend), broker workbook export (2 tabs, openpyxl,
  summary/detail reconciliation tested). 35 tests green total.
- Dockerfile + fly.toml (app name voidfinder-sales-penetration, iad).
- Seed script written: cinderhaven-data-platform/scripts/
  seed_void_patterns.py + seed_all.py step 6.5 (UNCOMMITTED in the
  platform repo until it runs green against a live DB). Design:
  never-scanned cluster = INSERT-only new authorizations (Kroger ×
  Southeast × 3 star AS SKUs, auth 2025-06-30) so zero revenue
  deletion; went-dark = 30 pairs, scans deleted after 8–20-week
  cutoffs, guarded to <1% of any retailer's trailing-52w revenue
  (lock tolerance is 2%).
- Rider B done (analysis/RIDER-B-option-b-impact.md): unification
  would stay inside every canonical lock; all movement comes from
  went-dark deletions; recommendation = no urgency, protocol-gated.
- cinderhaven-store-universe installed read-only from doormath's
  packages/ subdirectory (Decision 1). Doormath untouched.

**Rider A — doormath ↔ cinderhaven-db divergence (permanent record):**
Door Math generates its data in-memory from cinderhaven-store-universe
(no DB); Spin Rate and Void Finder read cinderhaven-db Postgres, which
is seeded by cinderhaven-data-platform's own generators. These were
ALREADY two parallel data sources before Void Finder; the contract
between them is CINDERHAVEN_CANONICAL.md figures, not row-level
identity. Void seeding (option a) widens the row-level gap on purpose:
- cinderhaven-db gains ~28+ Kroger-Southeast authorizations
  (CHP-AS-001/002/006, dated 2025-06-30) that Door Math's auth matrix
  does not have, and loses scans for 30 went-dark pairs that Door Math
  still shows as scanning.
- Consequence: Door Math's authorized-but-not-scanning exception list
  (conceptually Void Finder's input) will NOT contain Void Finder's
  seeded voids, and their door/scan counts differ at row level.
- Canonical figures stay inside tolerance (the seed guard enforces
  <1% per-retailer revenue deletion; verify with
  scripts/check_canonical.py after seeding).
- If a future session needs the two tools to tell one row-level story,
  that is option (b) — see analysis/RIDER-B-option-b-impact.md; it
  requires Shawn's approval under doormath's data-change protocol.

**State:** Repo green (35 tests). NOT yet seeded/deployed.
BLOCKED on two things:
1. Docker Desktop is wedged in a restart-to-update loop (backend exits
   ~15s after launch; staged delta update 230596→232116 never applies;
   the elevated updater run got a canceled UAC). Fix: run
   `C:\Users\mssha\AppData\Local\Temp\DockerDesktopUpdates\Docker
   Desktop Updater-230596 (232116).exe` elevated, then start Docker
   Desktop. Note: a stale flyctl proxy to PROD holds localhost:5432 —
   develop against local compose on 5433 via the override file in the
   session scratchpad, or kill the proxy first.
2. Deploy gate: confirm subdomain with Shawn (default
   voidfinder.lailarallc.com; name "voidfinder" already confirmed).

**Next:** (1) unblock Docker → compose up → run
seed_void_patterns.py → check_canonical.py → dbt build if marts are
needed → commit platform repo; (2) run app locally against seeded DB,
verify exception report renders the cluster; (3) sync seed to prod
cinderhaven-db (CSV dump pattern from spinrate FAILURES.md); (4)
deploy to Fly after Shawn's subdomain confirm; (5) Work-page card
after Door Math / Spin Rate on lailara-website; (6) DATABASE_URL into
the synced credential set.

---

## 2026-07-02 — Project initialized

**Started from:** New project setup via /new-project. Build brief
already in folder (voidfinder-fable-brief.md).

**Did:** Created repo, set up CLAUDE.md/DECISIONS.md/HANDOFF.md/
PLAN.md/FAILURES.md, git init, GitHub remote
(voidfinder-sales-penetration, private, matching series siblings).

**State:** Foundation in place. PLAN.md intentionally empty — brief
is the scope source. Two loose ends:
1. Folder rename PENDING: local folder is still `voidfinder` but the
   repo is `voidfinder-sales-penetration`. Windows locked the folder
   while this session was open. After closing the session, rename:
   `Rename-Item C:\Users\mssha\projects\active\voidfinder voidfinder-sales-penetration`
2. The brief references a fuller voidfinder-build-brainstorm.md that
   was NOT found on disk anywhere — Shawn should drop it into the
   project root before the build session.

**Next:** Run /clarify to scope the first arc, then /office-hours
(Heavy tier). Before deploy, confirm with Shawn: (1) name/subdomain
(voidfinder confirmed at setup), (2) packaging choice if sharing the
Door Math data model means refactoring doormath.

---

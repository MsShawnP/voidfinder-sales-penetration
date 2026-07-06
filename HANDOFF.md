# Void Finder — Handoff Log

Session-by-session state. Updated by /log mid-session and /wrap at
session end.

For durable choices, see DECISIONS.md.
For the current work arc, see PLAN.md.
For things that didn't work, see FAILURES.md.

---

## 2026-07-04 14:09

**What changed:** DNS + cert live at voidfinder.lailarallc.com;
executive content pack shipped, then final copy applied verbatim,
then Scope C: "Measured through" (as-of) selector + annualized
run-rate metric ($762,385/yr, 0.77% of $99.2M at default as-of).

**Why:** Shawn's copy doc + Scope C brief. The old "Total Void
Opportunity / annual" tooltip mislabeled a cumulative figure — split
into "Lost So Far" + "Annualized Run-Rate" (median weekly comparable
$ × 52, labeled forward projection).

**State:** Live and verified: as-of recomputes everything (Sep 27
check: $171,449 / 87 voids / 11 map states); hero shows both numbers;
5 stat cards; state choropleth; glossary/why panels; filter tooltips.
52 tests green. Pushed through a97ad1c. Work-page card still local
in lailara-website (push = auto-publish via GH Actions — awaiting
Shawn's OK). CF DNS:Edit token still active (deletion offer open).

**Next:** Shawn reviews the live site → say the word and I push
lailara-website to publish the card. Then /wrap; remaining PLAN
items: none blocking (arc complete except card publish + Rider A
already documented).

---

## 2026-07-03 12:49

**What changed:** Seed ran green against a new native Windows Postgres
(no Docker); canonical check passed; all three views verified rendering
real voids, cluster callout correct ($164,884 Kroger·Southeast).

**Why:** Docker Desktop proved unrepairable (recurring broken-socket
crashes even after the 4.80.0 update; WSL mirrored networking also
refuses host→WSL connections). Replaced it with PG 16.9 zip binaries at
C:\Users\mssha\tools\pg16, port 5433 (5432 stays reserved for the
flyctl prod proxy).

**State:** Local pipeline proven end-to-end: seed_all.py (2.28M rows,
void guard max 0.07% vs 1% limit), check_canonical.py PASS, app serves
/health 200 + /ready ready, exception report shows $366,175 / 114
voids / 60 stores, rollup + trend render, export callback clean. Both
repos committed. Minor: AG Grid paginationPageSize warning +
sizeColumnsToFit noise on hidden tabs. Docker remains broken (unused).

**Next:** Sync seed to prod cinderhaven-db (CSV-dump pattern, needs
go-ahead), confirm subdomain (default voidfinder.lailarallc.com), then
Fly deploy + Work-page card.

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

## 2026-07-06 18:22

**What changed:** Realistic void seeding (background voids at all six
retailers), confirmed the hero recompute is not a code bug, and synced
the reseeded raw.scan_data to prod cinderhaven-db.

**Why:** ~96% of void dollars sat at Kroger (over-broad cluster
defensive delete + a 30-pair scatter too small for other banners); the
"static hero" report was a stale browser tab from an earlier 3-output
callback change, not a wiring bug.

**State:** Live and verified on deployed site. Seed fix committed in
cinderhaven-data-platform (02587a5): narrowed defensive delete +
retailer-stratified scatter → all 6 retailers/5 regions nonzero,
cluster 53%, canonical PASS. Prod raw.scan_data synced (1,323,569 rows,
atomic); public_marts intentionally NOT rebuilt so spinrate stays
byte-identical (verified). Hero recomputes on deployed site (default
$293,208/133/116 vs strict 13w/12/1.0 → $152,767/116/101); regression
test committed (e9f4222). 93 tests green.

**Next:** If prod dbt marts are ever rebuilt, spinrate shifts by the
small within-tolerance void delta — decide whether to rebuild or leave.
Otherwise: /wrap the session.

---

## 2026-07-06 18:46

**What changed:** Rebuilt the prod dbt marts (`dbt build` against
cinderhaven-db) so raw + marts are now consistent — following through on
the last session's flagged decision to rebuild rather than protect
spinrate's exact bytes.

**Why:** Last session synced reseeded raw.scan_data to prod but left
public_marts stale. Shawn chose consistency: void delta is verified
inside the 2% canonical lock, so rebuild.

**State:** dbt build PASS=457/WARN=0/ERROR=0/SKIP=0 (32 tables, 55 views,
370 tests). verify_canonical.py = OK within tolerance, all 18 figures
reconcile (its only failure was a Windows cp1252 crash on the Δ glyph —
re-ran with PYTHONUTF8=1; display bug, not data). Before/after proof only
the scan chain moved: fct_scan_data 1,325,794/$99,208,341.46 →
1,323,569/$99,058,738.85, now == raw.scan_data; every non-scan anchor
byte-identical (retailer pmts $52,128,777.36/$45,467,554.01, deductions
14,947/$1,118,681.92, chargebacks 2,873, 50 SKUs/640 stores/6 retailers).
Scan delta −$149,602.61 (−0.15%). Live reconciliation: spinrate (marts,
no-TTL cache, warm min=1) was serving stale $99.21M — restarted (same
image, no redeploy), healthy 1/1, now serves $99.06M; ask-cinderhaven
(min=0) was stopped, self-heals on cold start; voidfinder reads
raw.scan_data so unaffected — default $293,208/133/116 stands. All three
live sites HTTP 200. No other active tool reads public_marts.

**Next:** /wrap the session — arc work is done; only remaining PLAN item
is the lailara-website Work-page card publish (awaiting Shawn's OK).

---

## 2026-07-06 18:53 — /wrap

**Started from:** Prod raw.scan_data reseeded last session but marts left
stale; open decision to rebuild or leave.

**Did:** Started flyctl proxy, confirmed prod identity, captured
before-state, ran `dbt build` on prod (457 PASS / 0 ERROR), ran
verify_canonical (OK within tolerance), captured after-state proving only
the scan chain moved, restarted spinrate to clear its stale warm cache,
committed the log (6bb5ff5). Stopped the proxy.

**State:** Prod raw + marts consistent. spinrate healthy 1/1 serving
$99.06M; ask-cinderhaven self-heals; voidfinder unaffected
($293,208/133/116). All three live sites 200. Repo clean. Local PG (5433)
untouched. Two lessons logged to FAILURES; consistency rule logged to
DECISIONS.

**Next:** Publish the lailara-website Work-page card (auto-publishes via
GH Actions on push) once Shawn gives the OK. That closes the arc.

---

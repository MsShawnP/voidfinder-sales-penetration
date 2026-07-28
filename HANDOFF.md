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
[Update 2026-07-13: the annual-sales basis for the run-rate share
is now trailing-52-week revenue of $32.8M (`ANNUAL_SALES_BASIS` in
app/layout.py), superseding the $99.2M basis above; the 0.77%
figure no longer applies and the share is computed at runtime.]

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

## 2026-07-06 20:48

**What changed:** Scattered never-scanned voids across the five non-Kroger
banners so each shows a nonzero never-scanned bar while Kroger stays
dominant — then ran the full local→prod pipeline.

**Why:** Never-scanned was $0 everywhere except the Kroger-SE cluster.
Isolated new-item setup failures happen at every banner; the cluster
should dominate, not monopolize.

**State:** seed_never_scanned_scatter added to platform
scripts/seed_void_patterns.py (committed b287881): one healthy uncurated
item per banner (DG/SB lines), 1-3 stores, recent auth, no scans;
INSERT-only so no revenue moves. Full seed_all local re-seed (re-running
void patterns alone double-applies went-dark — not idempotent);
scan_data reproduced prod exactly (1,323,569/$99,058,738.85), dist_log
9,992 (+12 scatter). The scatter lives in raw.distribution_log (NOT
scan_data — voidfinder reads dist_log directly), so synced ONLY the 12
new rows to prod via a gated diff-sync (aborts unless diff == the 12
scatter rows); scan_data left byte-identical. dbt build prod
PASS=457/0 ERROR; fct_distribution 9,992=raw, fct_scan_data unchanged.
verify_canonical prod OK. Restarted BOTH voidfinder (reads dist_log,
warm min=1) and spinrate (reads fct_distribution). Verified vs prod:
never-scanned nonzero at all 6 — Kroger $165,526 (93%), Walmart $4,946,
Costco $3,270, Sprouts $1,820, Regional $1,460, Whole Foods $590. New
default void set 145/$323,884/128 (never-scanned 49/$177,612, +12).
Sites 200. Proxy stopped, local 5433 intact.

**Next:** /wrap. Only remaining PLAN item is the lailara-website
Work-page card publish (awaiting Shawn's OK).

---

## 2026-07-06 21:11 — /wrap

**Started from:** Prod raw+marts consistent (earlier wrap); new ask to
scatter never-scanned voids beyond the Kroger cluster.

**Did:** Added seed_never_scanned_scatter (platform b287881); full
seed_all local re-seed; gated 12-row distribution_log diff-sync to prod;
dbt build prod (457/0); verify_canonical OK; restarted voidfinder +
spinrate; verified all 6 banners nonzero never-scanned. Both repos pushed
(voidfinder 96eb1e4, platform b287881). Logged one failure + two
decisions.

**State:** Prod: never-scanned nonzero at all 6 banners (Kroger 93%
dominant, $165,526; scatter $590-$4,946). Default void set 145/$323,884/
128. raw+marts consistent, canonical OK, sites 200. Repos clean/pushed.
Proxy stopped, local 5433 intact.

**Next:** Publish the lailara-website Work-page card (auto-publishes via
GH Actions on push) once Shawn gives the OK — closes the arc.

---

## 2026-07-28 — Tier C review fixes, shipped and verified live

**What changed:** Worked the Tier C review list — 12 of 13 items — then
deployed. Live at voidfinder.lailarallc.com, version 29 (previous
deploy was 2026-07-14).

**Why:** Two Criticals were in production: the broker workbook printed
an un-clipped whole-life total against a period-clipped screen, and the
why-panel asserted a dimensionally invalid 20–33× margin multiple.

**Did:**
- `9cddf7a` — one period basis. `calculations.apply_period` clips
  void_dollars and recomputes priority; the hero, the "Lost so far"
  KPI, the exception grid, the state map, the cluster callout, the
  rollup charts, and both workbook tabs now read through it. The
  workbook resolves the period in its callback (where the week grid
  lives) and passes period_weeks/period_label down, so
  generate_workbook stays pure and unit-testable.
- `8daf6d7` — cut the margin-equivalent sentence (Shawn's call).
  `_fmt_margin_equiv` divided revenue by a net-margin ratio. There is
  no canonical contribution-margin figure to rebuild it from —
  CINDERHAVEN_CANONICAL.md has only 87¢ net-collected per wholesale
  dollar and an 11% EBITDA check — so inventing a rate was rejected.
- `b1983e1` — three captions that overstated the code: the trend's
  "always matches the Exception Report count" (false under any display
  filter, since void_trend never sees them), the hero subhead mixing a
  clipped dollar with unclipped counts, and a choropleth footnote
  describing a bar chart.
- `a4b860d` — .dockerignore, `NUM_FMT_DOLLAR` → `"$#,##0"`, PLAN.md
  ticked, stale worktree pruned.
- `8e51824` — void-type series moved to paired-palette slots 1–2
  (Chicago-20/70); Visualization section of DECISIONS.md filled in,
  including the documented choropleth no-labels deviation.
- `7718155` — synthetic-data disclosure moved from the frame footer to
  an eyebrow above the hero, rendered from layout.py so the vendored
  lailara-frame survives re-vendoring.

**State:** 107 tests green, no xfails. Pushed (d7dd026..7718155) and
deployed. Verified on the live site: /health 200, /ready ready,
by-type + by-retailer + by-region rollups and the Exception Report KPI
all read $305,294; the why-line's only dollar figure is $305K; palette
on #1f2e7a/#8e9ad0; eyebrow present, footer clean. Checked at 1440 and
375 locally against the seeded DB — no horizontal overflow, no console
errors. Local PG was started on 5433 for verification and stopped
again.

**Workbook verified off the live site, not inferred.** `_build_summary`
is a separate code path off the same frame as the on-screen KPI, which
is exactly how the two diverged, so the page rendering correctly is not
evidence about the export. Pulled the real .xlsx from the deployed
export callback (20,941 bytes): Summary total $305,294 = the page KPI,
parameter line reads "period the last 26 weeks", detail reconciles at
$305,294.17 across 145 rows, by-type split 177,612.31 / 127,681.86
matches the live rollup chart exactly, cells formatted $#,##0.
(Note for scripted checks: the edge 403s python-urllib's default
User-Agent — send a browser UA.)

**Observed, not a defect:** 43 of 145 rows carry a "Weeks dark" larger
than the reporting period, because apply_period clips dollars but not
the void's true age — a broker needs to know a store has been dark 37
weeks even when only 26 are counted. Disclosed in the grid header
tooltip, the methodology note, and the workbook footnote. The cost is
that dividing the dollar column by the weeks column understates weekly
velocity. If that ever bites, the fix is an "In-period weeks" column
beside "Weeks dark" — display only, no math change.

**Figures note:** the review's $238,546 / $834K were synthetic
reproductions run through the shipped calculations.py, not real seeded
figures — read them as the 3.5× ratio, which held. The real seeded
default is $305,294 / 145 voids / 128 stores.

**Next:** The lailara-website Work-page card is still the only open
PLAN item, awaiting Shawn's OK (push auto-publishes via GH Actions).
The dollarization sensitivity band is backlogged in PLAN.md — six
sibling repos have live Criticals and come first.

---

## 2026-07-20 19:45 — /wrap (cross-cutting session)

**Started from:** cinderhaven-db credential desync — spinrate DOWN (503),
postgres role password didn't match any .env file.

**Did:** Found correct password (SU_PASSWORD from cinderhaven-data-platform
.env); propagated to 4 Fly app secrets (spinrate, voidfinder, EDI,
ask-cinderhaven) and 11 local .env files across active/published/archived
projects. Deployed voidfinder with hero text already committed (d9bc59f).
Ran dbt fct_exceptions rebuild on EDI (679K rows). All sites verified
live and rendering data.

**State:** All DB-backed sites healthy (200). Credentials synced across
all repos. Code changes (hero text, data fixes) were already committed in
prior sessions. .env files gitignored, no code changes to commit.

**Next:** Audit batch complete. No blocking work remaining. Work-page card
publish still awaiting Shawn's OK.

---

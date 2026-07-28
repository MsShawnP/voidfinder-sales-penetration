# Void Finder — Decisions Log

Permanent record of choices that should survive session turnover.
If a decision is reversed, strike it through and add the replacement
below — don't delete.

---

## Format

Each entry:
- **Date** — when decided
- **Decision** — one sentence, imperative voice
- **Why** — the reasoning, including what was tried and rejected
- **Scope** — what this applies to (file, chunk, deliverable, or "global")
- **Do not** — explicit anti-instructions, if any

---

## Architecture & Pipeline

### 2026-07-02 — Name the tool "voidfinder"; repo voidfinder-sales-penetration
- **Why:** Shawn picked voidfinder over ghostshelf/darkdoors at setup.
  Repo name follows the series convention (doormath-sales-penetration,
  spinrate-sales-penetration); subdomain voidfinder.lailarallc.com.
- **Scope:** global
- **Do not:** Deploy to any other subdomain without asking.

### ~~2026-07-02 — Private GitHub repo~~ (superseded 2026-07-18)
- **Why:** Matches both series siblings (doormath and spinrate are
  private). Use /publish to take it public later if desired.
- **Scope:** global

### 2026-07-18 — Public GitHub repo
- **Why:** The original rationale was matching private siblings, but doormath and spinrate are both public now. Flipped public alongside the profile README that lists every public tool. Pre-flip audit: no .env committed, .gitignore covers secrets and keys, data is synthetic Cinderhaven, LICENSE and .env.example brought to sibling parity.
- **Scope:** global

---

## Data & Schema

### 2026-07-02 — Install cinderhaven-store-universe from doormath's repo subdirectory
- **Why:** The shared package already exists at
  doormath-sales-penetration/packages/cinderhaven-store-universe/
  (643 lines, pip-installable, tested). Installing it in place gives
  one source of truth with zero doormath changes. Extracting to a
  standalone repo was rejected: touches a shipped tool for no
  functional gain. Confirmed by Shawn 2026-07-02.
- **Scope:** global
- **Do not:** Refactor doormath. Do not copy the package's source
  into this repo.

### 2026-07-02 — Build the comparable-store dollarization fresh
- **Why:** The brief said reuse short-ship-cost's logic, but
  inspection showed that repo has no comparable-store median-velocity
  code (it does shipment-level cost math). Spin Rate's
  calculate_expansion_upside() uses door-count percentiles, not
  tier+region medians — wrong shape. Build here: median velocity of
  comparable scanning stores (same volume tier + region) × void
  weeks. Median, not mean. Heavy unit tests.
- **Scope:** src/ core logic
- **Do not:** Silently switch to mean or to percentile benchmarks.

### 2026-07-02 — Seed demo voids into cinderhaven-db ONLY
- **Why:** The brief's "add voids to the store universe" collides
  with doormath's data-change protocol: the shared generator feeds
  all 5 tools and its ACV/TDP canonical figures are locked. Injecting
  a never-scanned cluster would shift them. So: seed voids in the
  Postgres seed path (cinderhaven-data-platform, Spin Rate's
  pattern); doormath's in-memory data stays untouched. Confirmed by
  Shawn 2026-07-02, with two riders:
  (A) document the doormath↔DB row-level divergence in HANDOFF.md —
  Door Math's authorized-but-not-scanning list feeds Void Finder
  conceptually, and under this option their row-level numbers
  diverge; (B) compute how much doormath's locked figures WOULD
  shift under unified seeding — analysis only, apply nothing.
- **Scope:** seeding pipeline, cinderhaven-db
- **Do not:** Touch doormath's generator, its locked canonical
  figures, or CINDERHAVEN_CANONICAL.md.

### 2026-07-06 — Keep prod raw and dbt marts consistent; rebuild marts after any scan reseed
- **Why:** After reseeding raw.scan_data, the prior session left
  public_marts stale to protect spinrate's exact bytes. Shawn chose
  consistency: the void delta is verified inside the 2% canonical lock, so
  a raw≠marts state is worse than a small within-tolerance shift. Rebuilt
  via `dbt build` (457 PASS/0 ERROR); verify_canonical stayed within
  tolerance; only the scan chain moved ($99,208,341.46 → $99,058,738.85,
  −0.15%), every non-scan anchor byte-identical.
- **Scope:** prod cinderhaven-db, public_marts
- **Do not:** Leave marts unbuilt after a raw reseed thinking it protects a
  downstream tool — it just hides an inconsistency. After a mart rebuild,
  RESTART any warm marts-reading app (spinrate: min_machines_running=1 +
  no-TTL in-process cache) or it serves stale figures indefinitely. Tools
  that read raw directly (voidfinder) or auto-stop when idle
  (ask-cinderhaven, min=0) don't need a restart.

### 2026-07-06 — Never-scanned voids live in raw.distribution_log; sync that table and restart voidfinder
- **Why:** A never-scanned void is an authorization with no scans, so it
  lives in raw.distribution_log — NOT raw.scan_data. voidfinder reads
  distribution_log directly (app/db.py get_auth). Adding/changing
  never-scanned voids means editing distribution_log and syncing THAT
  table to prod; scan_data stays byte-identical (which also keeps
  spinrate's scan figures untouched). Synced via a gated diff (abort
  unless the diff is exactly the expected new rows).
- **Scope:** void seeding, prod sync, cinderhaven-db
- **Do not:** Sync scan_data expecting never-scanned changes to appear —
  they won't. After any raw.distribution_log change, RESTART voidfinder
  (warm min_machines_running=1, caches auth in-process) and dbt build +
  restart spinrate (reads fct_distribution). See the mart-consistency
  decision above.

### 2026-07-06 — Always re-seed via full seed_all, never seed_void_patterns alone
- **Why:** went-dark seeding samples currently-scanning pairs and deletes
  them; it is not idempotent, so re-running seed_void_patterns on an
  already-seeded DB compounds deletions and drifts scan_data off the
  canonical figures. seed_all drops and regenerates raw from scratch and
  applies void patterns exactly once, reproducing prod deterministically.
- **Scope:** local re-seeding, cinderhaven-data-platform
- **Do not:** Re-run seed_void_patterns (or apply_went_dark) against a DB
  that already has void patterns applied. Full seed_all only.

---

## Visualization

Lailara design system governs. Entries here record where this project
sits inside it, and the one place it deviates.

### 2026-07-28 — Never-scanned / went-dark take paired-palette slots 1–2

- **Decision:** The two void types are Chicago-20 (never scanned) and
  Chicago-70 (went dark), in both `charts.split_bars_by_type` and the
  by-type rollup bar.
- **Why:** The design system assigns categorical series from the paired
  palette in order and never skips a slot; a two-series chart gets slots
  1 and 2. The previous pairing was Tokyo-40 and HK-35 — neither is a
  paired-palette stop, and the teal/rose combination read as
  positive-versus-negative when both void types are losses. Dark = the
  higher-value fix also matches how the rest of the tool ranks them.
- **Scope:** app/charts.py, app/views/rollup.py
- **Do not:** Reintroduce Tokyo/HK for these two series, or assign a
  categorical series a colour that is not a numbered slot. Pinned by
  `tests/test_charts.py` —
  `test_two_series_split_takes_paired_palette_slots_one_and_two`.

### 2026-07-28 — The state choropleth carries no direct data labels

- **Decision:** Documented deviation from "label every data point." The
  void map states its numbers through a colourbar with explicit
  true-value ticks and a per-state hover readout, not printed labels.
- **Why:** Direct labels on a US choropleth collide on the small
  Northeastern states, and voids appear there. Illegible overlapping
  labels are worse than a legend a field rep can read. The exact
  per-state dollar figure is one hover away, and the ranked grid below
  carries every store-level number in full.
- **Scope:** app/charts.py `state_choropleth`, the Exception Report view
- **Do not:** Treat this as licence to drop labels from the bar charts —
  every bar in this tool is labeled with its true value. Revisit if a
  Scattergeo label overlay can be made collision-free.

---

## Output Formats

[Decisions about deliverable formats, structure, organization.]

---

## Writing & Voice

[Voice, style, terminology decisions specific to this project.]

---

## Reversed / Superseded

When a decision is overturned:
1. Strike through the original entry above (don't delete)
2. Add a new entry below with the replacement decision
3. Note the link in both directions

This preserves the history of why something is the way it is.

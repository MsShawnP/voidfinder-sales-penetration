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

### 2026-07-02 — Private GitHub repo
- **Why:** Matches both series siblings (doormath and spinrate are
  private). Use /publish to take it public later if desired.
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

---

## Visualization

[Chart conventions, palette decisions, interactivity choices —
Lailara design system governs.]

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

# Void Finder — Failure Log

What was attempted that didn't work, why it didn't work, and what was
tried next.

Lower bar than DECISIONS.md — capture failures even when they didn't
produce a durable rule. The whole point: future-you (or future-Claude)
shouldn't re-attempt dead ends because the lesson got lost.

---

## Format

### YYYY-MM-DD — [One-line failure description]

**Attempted:** [What was tried]

**Why it didn't work:** [Concrete reason, not "it broke." If the
failure mode was technical, name the specific issue. If the failure
mode was scope or approach, name that.]

**What we tried instead:** [The next attempt, which may also have
failed and may have its own entry below]

**Status:** Resolved / open / abandoned

**Tags:** [keywords for future text-search]

---

## Inherited lessons (from tools #1/#2 — pre-logged so they don't repeat)

### Spin Rate — /health hard-gated on the DB caused an external 503

**Why it didn't work:** Health endpoint required a live DB connection;
when the DB blipped, Fly marked the app unhealthy and users got a 503
instead of a branded "data temporarily unavailable" shell.

**What to do instead:** /health always returns 200 if the app process
is up; DB readiness is a separate signal.

**Status:** Resolved (rule carried into CLAUDE.md)

**Tags:** health-check, fly.io, 503, readiness

### Spin Rate — DATABASE_URL drifted from the canonical credential set

**Why it didn't work:** App had its own copy of credentials that
desynced from cinderhaven-data-platform/.env.

**What to do instead:** Wire DATABASE_URL into the synced credential
set (canonical creds in cinderhaven-data-platform/.env, gitignored).

**Status:** Resolved (rule carried into CLAUDE.md)

**Tags:** credentials, env, desync, postgres

---

## Entries

[New entries get added here, most recent at the top]

### 2026-07-06 — Re-running seed_void_patterns alone double-applied went-dark deletions

**Attempted:** To add the never-scanned scatter, re-ran
`seed_void_patterns.py` against the already-seeded local DB, expecting the
existing cluster/went-dark steps to no-op and only the new scatter to
apply.

**Why it didn't work:** `pick_went_dark_pairs` samples from pairs that are
CURRENTLY scanning (week_ending >= recent cutoff). After the first seed,
the previously-darkened pairs are gone, so the second run samples a NEW
set of still-scanning pairs and deletes them too. went-dark is not
idempotent — re-running compounds the deletions (saw ~94 additional pairs
darkened, Regional hit 1.47% of trailing-52w). Local scan_data no longer
matched prod.

**What we tried instead:** Full `seed_all` re-seed (drops + regenerates
raw from scratch, applies void patterns once). scan_data reproduced prod
exactly (1,323,569 / $99,058,738.85). This is the only correct way to
re-seed.

**Status:** Resolved (rule captured in DECISIONS.md — always re-seed via
seed_all)

**Tags:** seed, idempotency, went-dark, scan_data, seed_all, determinism

### 2026-07-06 — spinrate's live site did NOT reflect the rebuilt marts on its own

**Attempted:** Rebuilt prod marts and expected spinrate's live scan
figures to shift by the void delta automatically, since spinrate
live-queries public_marts.

**Why it didn't work:** spinrate caches query results in an in-process
dict with no TTL (`app/db.py` `_cache`, evicted only at 128 entries or on
restart), and its Fly app has `min_machines_running = 1` so the machine
stays warm across the DB change. The warm process kept serving the
pre-rebuild $99.21M scan total. A correct DB is not sufficient for a
correct live site when the reader caches and stays warm.

**What we tried instead:** `flyctl apps restart spinrate-sales-penetration`
(same image, no redeploy) → cache cleared, healthy 1/1, now serves
$99.06M. Note: ask-cinderhaven (`min_machines_running = 0`) self-heals on
cold start; voidfinder reads raw.scan_data so it's immune.

**Status:** Resolved (restart is the fix; captured as a rule in DECISIONS.md)

**Tags:** cache, no-ttl, fly.io, min_machines_running, stale, spinrate, marts

### 2026-07-06 — verify_canonical.py crashes on Windows with UnicodeEncodeError

**Attempted:** Ran `scripts/verify_canonical.py` against prod to check the
canonical figures after the mart rebuild.

**Why it didn't work:** The script prints a `Δ` (U+0394) column header;
Windows' default cp1252 console encoding can't encode it, so it dies with
`UnicodeEncodeError` — AFTER all DB queries have already run. It's a
display bug, not a data problem, but it makes the script exit 1 and print
no table.

**What we tried instead:** Re-ran with `PYTHONUTF8=1 PYTHONIOENCODING=utf-8`
→ full table printed, "OK within 2% tolerance", exit 0. Permanent fix
would be to reconfigure stdout to UTF-8 inside the script (or drop the
`Δ` glyph) so it doesn't depend on the shell.

**Status:** Resolved via env var (script still has the latent bug)

**Tags:** windows, cp1252, unicode, encoding, verify_canonical, dbt

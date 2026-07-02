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

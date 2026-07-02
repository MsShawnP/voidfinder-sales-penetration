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

[Decisions about data sources, schemas, transformations. The big open
one: packaging of the shared Door Math data model — shared
cinderhaven-store-universe package vs standalone repo reading locked
canonical data. Confirm with Shawn before deciding.]

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

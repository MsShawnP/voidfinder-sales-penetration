# Rider B — What unifying the void seeds into the shared generator would do to Door Math

**Status: analysis only. Nothing was changed in doormath.** Produced
2026-07-02 by `analysis/rider_b_impact.py` against the installed
`cinderhaven-store-universe` package (doormath's own generator,
read-only).

## Headline

Unification is **technically cheap — every locked canonical figure
stays inside tolerance** — but it is not invisible, and it triggers
doormath's data-change protocol regardless.

## Numbers

Simulated on Door Math's in-memory data, last-13-week window
(2025-W40..W52):

| Effect | Baseline → unified | Against the lock |
|---|---|---|
| Portfolio penetration rate | 84.71% → 84.50% (−0.21pp) | Inside the 0.5pp rate lock |
| Retailer TDP (sum of per-SKU ACV%) | −1.6 to −6.0 points per retailer | −0.16% to −0.22% relative — inside the 2% band |
| Largest single-SKU ACV% shift | −1.9pp (CHP-SC-010 at Costco) | Per-SKU ACV is not a locked figure |
| Cluster authorizations added | +28 pairs (Kroger × Southeast) | Zero ACV/TDP effect — they never scan |

Two distinct mechanisms:

1. **The never-scanned cluster is nearly free.** It only adds
   authorizations. Door Math's ACV/TDP count scanning stores, so the
   cluster moves nothing but the penetration denominator (−0.21pp).
2. **All visible movement comes from the 30 went-dark pairs.** Deleting
   their recent scans pulls those stores out of "carrying" in the
   final quarter, nudging per-SKU ACV% down by up to ~1.9pp on the
   affected SKUs.

## What the numbers don't capture

- **Door Math's demo narrative.** Its exception and trend views would
  start showing Void Finder's seeded voids. That is arguably a
  feature (the two tools would tell one consistent story — Door
  Math's authorized-but-not-scanning list would literally contain
  Void Finder's cluster), but it changes screenshots and any figures
  quoted in Door Math's README/Work-page card.
- **The data-change protocol.** Doormath's DECISIONS.md requires
  explicit approval before touching the shared generator, regardless
  of impact size.
- **Approximation caveat.** The went-dark pair selection here uses the
  package's own exclusion list (slow-leak SKUs), not the platform
  seed's exact curated list, and the package's 2024–2025 window
  differs from the DB's 2023–2026 window. Treat per-SKU deltas as
  magnitude estimates, not exact predictions.

## Recommendation

No urgency. Option (a) — DB-only seeding — is live and consistent
within cinderhaven-db, where Spin Rate and Void Finder both read.
If cross-tool storytelling with Door Math ever matters (e.g., a demo
walking from Door Math's gap list into Void Finder's dollarization),
unification is a small, protocol-gated change: add the cluster
auths + went-dark patterns to the package generator, regenerate, and
re-verify Door Math's quoted figures. Budget roughly an hour, most
of it re-verification.

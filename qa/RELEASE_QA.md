# Public release QA

Current release verdict: **PASS**.

## Current release safeguards

- The versioned public-source lock verifies the official raw snapshots, extracted observations, consumed curve and H.8 calibration before release calculations write outputs.
- `cashflows()` accepts only immutable curves created from the verified canonical source and rechecks provenance and in-memory integrity at the calculation boundary.
- The H.8 residual is described as a residual-based stylized equity proxy, not regulatory capital.
- Word visual-QA evidence is regenerated automatically when missing or stale before artifact validation.

## Current-state verification

- Source lock: PASS; Treasury 2026-10-22 and H.8 2026-10-07 raw-to-processed lineage verified.
- Direct curve boundary: unbound and +10 bps in-memory curves are rejected; the canonical bound curve is accepted.
- Metrics: 17 / 17 canonical release metrics pass current-state reconciliation in `qa/current_metric_reconciliation.csv`.
- SQL: 2 independent recomputations and 3 partial recomputations; all five reconcile below USD 0.01.
- Tests: 60 passed, 0 failures, 0 errors, 0 skipped.
- Controls: 52 automated controls plus 2 recorded visual reviews pass in the current release.
- Word: 9 / 9 pages render without blank pages; core values and source hashes reconcile.
- Excel: 12 sheets, 15 native tables and 4 native charts; formula caches are present, with no formula errors or external links.

## Core metrics

- 938 synthetic contract/group records; total assets USD 100,000,000.00.
- Base NII USD 2,567,565.11; worst Delta NII USD -32,213.09 under +200 bps.
- Base EVE USD 12,927,232.70; worst Delta EVE USD -3,166,812.52 under +200 bps.
- Delta EVE / residual-based stylized equity proxy: -33.616%.
- Combined ending liquidity buffer USD 1,017,055.78; no breach in the tested 90 days, so survival is right-censored at at least 90 days.

## Known limitations

The H.8 residual-based equity proxy is not regulatory capital or a BCBS supervisory outlier test denominator. Liquidity is not formal LCR/NSFR. Treasury par yields feed a simplified discount-curve proxy, not an observed zero curve. The study is synthetic, omits the documented behavioral and market channels, and has not been used in production.

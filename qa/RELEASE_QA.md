# Public release QA

Release verdict: **PASS**.

## Original audit repairs

- M01 source binding: **FIXED**. Every formal calculation and artifact entry point uses the same fail-closed, versioned public-source lock.
- M02 equity proxy naming: **FIXED**. The H.8 residual is named only as a residual-based stylized equity proxy; it is not regulatory capital.
- M03 release object: **FIXED**. A public-safe local Git release candidate is prepared without the private audit workspace, runtime or caches.

## Verification

- Mandatory source lock: PASS; Treasury 2026-10-22 and H.8 2026-10-07 raw-to-processed lineage verified.
- Adversarial binding: +10 bps and six additional mutations rejected before EVE or artifact writes.
- Core regression: 17 / 17 audited metric comparisons unchanged.
- SQL: 2 independent recomputations, 3 partial recomputations, 0 output reaggregations; all five reconcile below USD 0.01.
- Tests: 55 passed, 0 failures, 0 errors, 0 skipped.
- Controls: 52 automated controls plus two recorded visual reviews passed.
- Word: 9 / 9 pages rendered and reviewed; no clipping, blank pages, unfinished text or legacy positive Tier 1 label.
- Excel: 12 sheets, 15 native tables, 4 native charts; 88 saved formulas have caches; no formula errors or external links. LibreOffice cache-stripped recalculation passed.
- Distribution: MIT license, public-source attribution, deterministic Office metadata and public-safe tracked set present.
- Preserved audit: 1226 files byte-identical; audit directory excluded from release tracking.

## Core metrics

- 938 synthetic contract/group records; total assets USD 100,000,000.00.
- Base NII USD 2,567,565.11; worst Delta NII USD -32,213.09 under +200 bps.
- Base EVE USD 12,927,232.70; worst Delta EVE USD -3,166,812.52 under +200 bps.
- Delta EVE / residual-based stylized equity proxy: -33.616%.
- Combined ending liquidity buffer USD 1,017,055.78; no breach in the tested 90 days, so survival is right-censored at at least 90 days.

## Known limitations

The H.8 residual-based equity proxy is not regulatory capital or a BCBS supervisory outlier test denominator. Liquidity is not formal LCR/NSFR. Treasury par yields feed a simplified discount-curve proxy, not an observed zero curve. The study is synthetic, omits the documented behavioral and market channels, and has not been used in production.

# Final source boundary repair report

## Scope and result

This repair closes the remaining source-boundary P1 without changing model assumptions, NII, EVE, liquidity, SQL, Word, or Excel logic. The sensitive `cashflows()` boundary now delegates authorization to trusted module-owned code. It accepts only the exact production `Curve` type, revalidates the current locked source, reconstructs the expected scenario curve, and compares every current normalized numeric field before position validation or financial calculation.

The independently reproduced subclass pattern is no longer usable. A subclass that overrides `require_source_binding()`, scenario provenance, or valuation behavior is rejected by exact-type identity before any such method or property is invoked.

## Current verification

| Check | Result |
| --- | --- |
| Direct unbound `Curve` | PASS: rejected |
| Direct +10 bp `Curve` | PASS: rejected |
| Post-verification mutation | PASS: rejected |
| Copied or forged provenance on altered content | PASS: rejected |
| Malicious subclass override | PASS: rejected without virtual validation |
| Malicious subclass with +10 bp content | PASS: rejected |
| Valid canonical concrete `Curve` | PASS: accepted |
| Formal pipeline +10 bp attack | PASS: rejected before EVE and outputs preserved |
| Source-boundary test module | PASS: 23 / 23 |
| Full pytest suite | PASS: 64 / 64 |
| Automated acceptance controls | PASS: 52 / 52 |
| Artifact checks | PASS: 21 / 21 |
| Current metric reconciliation | PASS: 17 / 17 |
| SQL classification | PASS: two independent and three partial recomputations |
| Word | PASS: nine pages rendered and reviewed |
| Excel | PASS: 12 sheets, 15 tables, four charts, 88 formulas, no formula errors |
| Prohibited positive Tier 1/CET1 labels | PASS: zero |

## Financial non-regression

The tracked financial result population has no diff against the base commit: positions, saved output tables, key metrics, SQL classifications, and core controls are unchanged. The current recomputation reports 938 records, USD 100,000,000 assets, Base NII USD 2,567,565.11, Base EVE USD 12,927,232.70, worst Delta EVE USD -3,166,812.52, and Combined terminal liquidity USD 1,017,055.78.

## Reproduction

The repair commit was checked out in a disposable fresh clone and executed with the documented Python 3.12 workflow. Setup, pipeline, figures, artifacts, documentation, Word build/render, tests, workbook build/verification, artifact validation, and final controls passed. The malicious subclass probe was also executed independently in that clone and failed closed with `SourceValidationError`.

See `subclass_bypass_fix.md`, `attack_matrix.md`, `fresh_clone_validation.md`, and `files_changed.csv` in this directory.

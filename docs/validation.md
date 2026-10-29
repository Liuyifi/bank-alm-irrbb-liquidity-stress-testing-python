# Validation summary

## Release conclusion

The public package preserves the reviewed analytics and artifacts from technical baseline `911b74a7c0d457028533046c15593c94b0846f01`. Packaging changed presentation, public tracking and documentation only; it did not change model code, SQL, tests, configuration, canonical financial inputs or canonical financial outputs.

| Validation layer | Result |
| --- | ---: |
| Pytest suite | 64 / 64 PASS |
| Automated acceptance controls | 52 / 52 PASS |
| Recorded visual reviews | 2 / 2 PASS |
| Core engine/data controls | 30 / 30 PASS |
| Current-metric reconciliation | 17 / 17 PASS |
| SQL reconciliation controls | 5 / 5 PASS |
| Maximum Python/SQL difference | USD 0.0000008158 |
| SQL tolerance | USD 0.01 |

## Source boundary

The release is bound to the hashes and dates in `config/public_source_lock.json`. The validation gate checks the official raw snapshots, extracted observations, consumed Treasury curve, H.8 calibration, schemas, units, ordering, missing values and numeric ranges. Mutation and exceptional-input tests confirm that altered or improperly bound source data fail closed before analysis outputs are written.

The frozen observations are:

- US Treasury par yield curve: observation 2026-10-22.
- Federal Reserve H.8: release 2026-10-16, observation 2026-10-07, all US commercial banks, not seasonally adjusted.

## Analytical controls

Thirty core controls cover the balance identity, unique position and cash-flow keys, principal conservation, date/rate bounds, shock direction, scenario completeness, discount-factor behavior, liquidity reconciliation and public-source integrity.

DuckDB executes all four files in `sql/`. Balance-sheet and repricing controls independently recompute results from position-level inputs. NII, EVE and liquidity controls are classified as partial recomputations because they reuse Python-projected cash flows or scenario discount inputs. No SQL control is presented as an independent valuation engine. The exact classification and input grain are published in `outputs/metrics/sql_reconciliation_classification.csv`.

## Artifact controls

The Word report opens as valid Office Open XML, renders to exactly nine nonblank pages and contains the same core metrics and six public-source hashes as the model outputs. The public PDF was copied from that verified rendering and visually checked page by page.

The Excel pack contains 12 populated sheets, 15 native tables, four native charts and 88 cached formulas. It has no external links or formula errors. A recalculation probe confirmed dependency behavior and restored the source value before the reviewed workbook was saved.

Both Office files were checked for comments, tracked changes, hidden sheets, external links, local absolute paths, personal identifiers and credential-like text. No public-safety issue was found.

## Evidence map

- `qa/QA_REPORT.md`: human-readable acceptance report and check register.
- `qa/checks.json`: 52 automated controls, two visual reviews and pytest result.
- `qa/core_checks.json`: 30 engine and data controls.
- `qa/current_metric_reconciliation.csv`: 17 current-vs-recomputed metrics.
- `qa/public_source_checks.json`: official-source validation record.
- `qa/visual_review.json`: Word and Excel visual-review record.
- `qa/workbook_build.json`: workbook build and recalculation evidence.
- `outputs/metrics/sql_reconciliation_classification.csv`: SQL control classification.

## Interpretation boundary

Passing validation establishes consistency with the documented synthetic assumptions. It does not establish empirical validity for deposit behavior, runoff, product mix, haircut eligibility or regulatory capital/liquidity compliance. See `docs/methodology.md` for the complete limitations.

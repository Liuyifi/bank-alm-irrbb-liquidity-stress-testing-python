# Project status

- Checkpoint: QA_COMPLETE / RELEASE_REPAIRED
- Started: 2026-10-23 (Asia/Shanghai)
- Scope: Independent stylized USD banking-book ALM, IRRBB and internal liquidity survival analysis. No reuse of other portfolio projects. No push or PR.
- Inputs: Fixed-seed synthetic contracts with mandatory locked official Treasury and Federal Reserve H.8 snapshots; no fallback or release bypass.
- Outputs: Reproducible Python/DuckDB engine, automated controls, English Word report (rendered page-by-page), Excel management pack, README and evidence-based resume bullets.
- Plan: (1) lock assumptions/source; (2) implement and run engine; (3) reconcile/test; (4) create and render artifacts; (5) final acceptance.
- Acceptance: Balanced ledger, valid contracts, cash-flow conservation, scenario completeness, Python/SQL agreement, reconciled liquidity buffers, readable Word/Excel, no unresolved required checks.
- Completed: Analytics, formal artifacts, source-binding repair, SQL classification repair, regression testing, rendering and release QA.
- Pending: None for the requested local release candidate.
- Release repair workspace is the repository root. Public release files use relative paths only.

## PLAN_LOCKED
- Official Treasury snapshot: observation 2026-10-22, feed entry updated 2026-10-23. Official annual XML acquired by src.public_data.
- Official H.8: release 2026-10-16, observation 2026-10-07. Downloadable FRB XML archive preferred and cross-checked to official current HTML (all commercial banks, NSA).
- Added requirement incorporated: observed H.8 aggregate category shares calibrate USD 100 million synthetic book; contracts and behavioral fields remain model assumptions.
- Broad H.8 cash, securities, loans, deposits, borrowings, residual and other net categories are retained. Residual is a normalization proxy, not regulatory Tier 1.
- No public-source fallback used. Snapshots and SHA256 lineage saved.
- Implemented monthly run-off cash-flow engine, par bootstrap, seven internal rate scenarios, daily liquidity ledger and four DuckDB SQL controls.
- Current phase: locked release candidate; refresh requires a separately reviewed source vintage and updated source lock.

## MAIN_EDIT_COMPLETE and RENDER_COMPLETE
- Engine: completed; 938 synthetic contract/group records calibrated to official H.8, USD 100m total assets.
- 30 dataset controls pass, including 12 public-source controls; the complete suite passes 55 tests.
- Five Python/DuckDB comparisons reconcile with max difference USD 0.0000008159.
- Seven rate scenarios, three liquidity scenarios and deposit beta/maturity sensitivities saved.
- Word report generated and rendered to nine page PNGs. All nine reviewed via contact sheets; no blank page, overflow or clipped tables. A template title border was removed after inspection and report rerendered.
- Excel management pack exported with 12 sheets, native filter tables, four charts and recalculation proof. All sheet previews reviewed; NII axis precision and chart labels corrected.
- README, full methodology, field dictionary and English/Chinese resume bullets created.
- Final corrected-view review, artifact acceptance, source attack tests and complete test run are finished.

## QA_COMPLETE
- TASK_STATUS: COMPLETED
- Initial build completed 2026-10-23; release repair and revalidation completed 2026-10-28, Asia/Shanghai.
- Public data: Official Treasury 2026-10-22 and Fed H.8 release 2026-10-16 / observation 2026-10-07; no fallback. Original snapshots, field mappings and SHA256 retained.
- Data: 938 synthetic contract/group records, USD 100m assets, calibrated to H.8 with 0.01 percentage-point tolerance.
- Verification: 55 pytest cases pass, zero skips/failures/errors; all 52 automated acceptance controls and two visual reviews pass (54/54 check register). The original 31 tests and 48 automated controls remain covered.
- Python/SQL: five controls pass, maximum difference USD 0.0000008159; two are independent recomputations and three are partial recomputations.
- Word: English report delivered; exactly nine pages rendered to PNG, all reviewed; targeted final views checked corrected title and appendix.
- Excel: 12 sheets, 15 filter tables, four native charts; formula recalculation probe passed, saved XLSX reimported, key metrics and formula caches verified.
- Completed files: README, methodology, source/field dictionaries, source QA, final QA and English/Chinese resume bullets.
- Next step: None required for the requested delivery. Reuse verified outputs. Optional future model extensions are described in the report and are not incomplete acceptance work.
- Boundaries: Synthetic positions, internal scenarios, H.8 residual-based stylized equity proxy, internal liquidity proxy. The equity proxy is not regulatory capital or a BCBS outlier-test denominator. No prepayment/options/hedges or other-liability cash demands; no LCR/NSFR or production claim.
- Git: Local `main` repository with one initial release-candidate commit; no remote, push, tag, PR or modification to another portfolio project.

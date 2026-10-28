# QA report

Final acceptance: **PASS**. 54 / 54 controls pass, comprising 52 automated acceptance controls and two recorded visual reviews. The full pytest suite passes 55 cases with 0 failures, 0 errors and 0 skips. It includes the original engine and saved-artifact coverage plus fail-closed source-binding and focused exceptional-input tests.

## Official public sources

Treasury observation 2026-10-22; H.8 release 2026-10-16 and observation 2026-10-07, all US commercial banks, not seasonally adjusted. The versioned source lock binds the raw official snapshots, extracted observations, consumed curve and H.8 calibration. The gate checks hashes, dates, schemas, units, maturities, ordering, duplicates, missing values, ranges and raw-to-processed lineage before output writes. Seven mutation cases, including the audited +10 bps attack, are rejected. No fallback or release override exists. Details: config/public_source_lock.json, public_source_checks.json and data/processed/public_data_lineage.json.

## Analytics and reconciliation

The USD 100m book balances to equity. Position IDs, principal, dates and rate/beta bounds pass. Contract-level principal conserves, fixed coupons preserve NII under shocks, floating resets retain current coupons until reset, and an isolated fixed asset loses PV under rising rates. Discount factors remain positive and decreasing. Tests also reprice synthetic par bonds and exercise exact bucket boundaries.

DuckDB executes all four saved SQL files. Five Python/SQL controls reconcile with maximum USD 0.0000008158, below USD 0.01. Balance-sheet totals and repricing buckets are independent recomputations. NII, EVE and liquidity are partial recomputations because they share Python-projected contractual cash flows or scenario discount inputs. The exact input grain and classification are published in outputs/metrics/sql_reconciliation_classification.csv. No SQL control is described as an independent valuation engine.

Daily liquidity reconciles opening cash, stress cash flows and one-time asset monetization. Sold government cash flows are excluded, remaining capacity is never spent twice, and inflows respect the internal cap. No scenario breaches within 90 days. All survival estimates are right-censored at 90 days; Combined ends with USD 1,017,055.78 available cash.

## Word verification

The final DOCX opens through python-docx and ZIP/XML verification and renders through the Documents skill's LibreOffice/PDF pipeline to exactly nine page PNGs. All nine pages were visually reviewed via contact sheets; targeted full-page views verified the title-rule correction and source-hash appendix. No blank pages, overflow, clipped tables, missing glyphs or blurred charts were observed. All core numbers and all six frozen-source SHA256 values match their source data. No TODO, TBC or unfinished placeholder text is present. QA PNGs/PDF are internal evidence, not substitute deliverables.

## Excel verification

The XLSX contains 12 populated sheets, 15 native tables and four native charts. The artifact-tool engine recalculated summary and scenario formulas. A temporary +0.1m NII edit changed its dependent delta by the same amount; the source value was restored before export. LibreOffice then opened a cache-stripped copy, forced formula recalculation and saved it without formula errors or structural count changes. All saved formulas have caches, no error cells or external links are present, and key saved summary numbers match Python. Every worksheet preview was reviewed, including the repaired Balance Sheet labels. The workbook is a frozen management pack with live arithmetic, not an input-driven implementation of the full Python engine.

## Scope and limitations

These tests establish implementation consistency under documented synthetic assumptions. They do not empirically validate NMD betas, maturities, runoff, sub-product mixes, haircut liquidity, the internal daily cap or the mapping of broad public categories. Delta EVE as a percentage of the stylized equity proxy is not a regulatory capital ratio or a BCBS supervisory outlier test. Liquidity results are not formal LCR/NSFR. Prepayment, options, hedges, spread/basis risk and other-liability cash demands remain unmodeled. Full boundaries are in docs/methodology.md and the report.

## Check register

| Check | Result | Evidence |
| --- | --- | --- |
| assets_equal_liabilities_plus_equity | PASS | Residual USD 0.0000000037 |
| position_id_unique | PASS |  |
| nonnegative_principal | PASS |  |
| reasonable_dates | PASS |  |
| rate_beta_bounds | PASS |  |
| cashflow_keys_unique | PASS |  |
| principal_not_overdrawn | PASS |  |
| base_principal_conservation | PASS | Max contract USD 0.000000001513; t0 carrying-value items are valuation entries |
| fixed_coupon_nii_unchanged | PASS |  |
| nii_shock_direction | PASS |  |
| fixed_asset_eve_shock_direction | PASS |  |
| discount_factors_positive_monotone | PASS |  |
| python_sql_reconciliation | PASS | Max USD 0.000000815839; tolerance USD 0.01 |
| ir_scenario_completeness | PASS |  |
| liquidity_scenario_completeness | PASS |  |
| liquidity_buffer_reconciliation | PASS | Max USD 0.000000011176 |
| inflow_cap_and_nonnegative_capacity | PASS |  |
| product_contribution_reconciliation | PASS |  |
| official_domains | PASS |  |
| dates_not_after_run | PASS |  |
| raw_files_nonempty | PASS |  |
| source_sha256 | PASS |  |
| h8_required_fields | PASS |  |
| h8_nsa_population_units | PASS |  |
| h8_xml_html_crosscheck | PASS | 0.049999999999272404 |
| calibration_ratios | PASS |  |
| treasury_maturities_strictly_increasing | PASS |  |
| no_public_data_fallback | PASS |  |
| synthetic_h8_calibration_tolerance | PASS | Maximum 0.000000008180 percentage points; tolerance 0.01 pp |
| h8_balance_identity | PASS |  |
| word_docx_openable | PASS |  |
| excel_xlsx_openable | PASS |  |
| excel_required_sheets | PASS |  |
| excel_native_tables_charts | PASS | 15 tables; 4 charts |
| excel_no_external_links | PASS | [] |
| excel_no_formula_errors | PASS | [] |
| excel_formula_caches_present | PASS | 88 formulas |
| word_no_unfinished_text | PASS |  |
| word_no_absolute_local_paths | PASS |  |
| word_no_legacy_equity_proxy_label | PASS |  |
| word_public_source_hashes | PASS |  |
| readme_paths_valid | PASS | [] |
| word_nine_pages | PASS | 9 |
| word_no_blank_pages | PASS |  |
| excel_core_metrics_vs_python | PASS | Max scaled difference 0.000000000000 |
| word_core_metrics_vs_python | PASS |  |
| word_page_pngs_present | PASS |  |
| word_title_rule_removed | PASS |  |
| word_embedded_charts_present | PASS |  |
| excel_recalculation_probe | PASS |  |
| excel_no_legacy_equity_proxy_label | PASS |  |
| word_visual_review_all_pages | PASS |  |
| excel_visual_review_all_sheets | PASS |  |
| pytest_full_suite | PASS | {'tests': 55, 'failures': 0, 'errors': 0, 'skipped': 0} |

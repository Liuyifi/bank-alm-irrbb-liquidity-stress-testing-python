# Banking Book Interest Rate and Liquidity Stress Testing

An independent Treasury Risk and ALM portfolio project with **938 synthetic contract/group records**, USD 100 million assets, official public calibration and a complete Python / DuckDB / Excel / Word workflow.

The default +200 bps internal shock changes 12-month NII by **USD -32,213** and EVE by **USD -3,166,813**. All three liquidity scenarios survive the tested 90 days. Combined ends with **USD 1,017,056** cash. Survival is **at least 90 days**, not an estimate beyond the window. Deposit beta sensitivity reverses the NII direction, so the small default earnings loss must be interpreted with its behavioral assumptions.

This is a synthetic banking-book study calibrated to industry aggregates. It does not represent any real bank, train a credit model, predict defaults or perform trading-book VaR backtesting. Shocks are internal illustrations. H.8 residual normalizes the equity proxy and is not regulatory capital. Liquidity measures are internal proxies, with no formal LCR/NSFR calculation. The model has not been used in production.

## Deliverables

- [Nine-page English Word management report](report/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.docx)
- [Excel management pack with 12 sheets](outputs/Bank_Treasury_Risk_Management_Pack.xlsx)
- [QA report](qa/QA_REPORT.md), [machine-readable checks](qa/checks.json) and [official public-source checks](qa/public_source_checks.json)
- [Exact key metrics](outputs/metrics/key_metrics.json), [H.8 calibration](outputs/tables/h8_balance_sheet_calibration.csv), [contract/group ledger](data/processed/positions.csv)
- [NMD model sensitivity](outputs/tables/nmd_model_sensitivity.csv) and [resume bullets](RESUME_BULLETS.md)
- [Source attribution and distribution notes](DATA_SOURCES.md) and [MIT license](LICENSE)

## Observed public inputs

Treasury: **2026-10-22** observation, selected feed entry updated **2026-10-23T04:00:43Z**. The publication-date metadata is the Atom entry update date; it is not a separate claim about the exact market-close publication time. Acquired from [US Treasury official annual XML](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=2026). Annual raw response, selected entry and dated CSV are frozen. These are par yields, not observed zero rates or SOFR.

Federal Reserve H.8: release **2026-10-16**, observation **2026-10-07**, **all commercial banks in the United States**, **not seasonally adjusted**. Downloaded from [Federal Reserve official XML archive](https://www.federalreserve.gov/releases/h8/data/FRB_h8_xml.zip) and cross-checked against the [official current release](https://www.federalreserve.gov/releases/h8/current/default.htm). XML USD millions are divided by 1000 for the stored USD billions extract. XML/HTML differences are within the table's 0.05 billion rounding. The current URL may change; frozen bytes and hashes identify this run.

Acquisition time: **2026-10-23T20:58:35.242778+08:00**. No public-source fallback was used. [Full public data lineage and field mapping](data/processed/public_data_lineage.json) records dates, source URLs, units, adjustment, response sizes and SHA256. Hashes below identify every frozen source file.

| Frozen source | SHA256 |
| --- | --- |
| [treasury_annual_source.xml](data/raw/treasury_annual_source.xml) | `8ca59afe0ed35054787ee256d5f384c3d3252f98eb5898caf0b105f665897bfe` |
| [treasury_selected_entry.xml](data/raw/treasury_selected_entry.xml) | `4a16963604c4bf96bb0e14e1f3944ac9063e8e7370796ca77ebd8e640a36c5c8` |
| [treasury_yield_curve_2026-10-22.csv](data/raw/treasury_yield_curve_2026-10-22.csv) | `0178bc9acf0ba819f571f29f5ce5a7b9f52b5c4e0a18dc4341b38fea4ff211bd` |
| [federal_reserve_h8_current_source.html](data/raw/federal_reserve_h8_current_source.html) | `59ecf8e72e3c2bb3414edf8a36fab7116adbb17e6999bd5d32ca70976d700949` |
| [federal_reserve_h8_2026-10-16.csv](data/raw/federal_reserve_h8_2026-10-16.csv) | `cb1f6d5d9dff0b8d469d254db2e502dd121f55b2782ba8ebf5ecefe73044d135` |
| [federal_reserve_h8_source.zip](data/raw/federal_reserve_h8_source.zip) | `2ce2d425cdc21fe7fe3623aec6fe0dc273438e6887cdea813a69e188344c222b` |

## Calibration and synthetic fields

Observed H.8 cash, securities, gross loans, deposits, borrowings, other liabilities, net due foreign offices and residual proportions calibrate USD 100m assets. [The calibration table](outputs/tables/h8_balance_sheet_calibration.csv) preserves asset and funding proportions to a predefined **0.01 percentage point** tolerance. Remaining asset categories, including the allowance adjustment, remain in a net other-assets proxy. Other liabilities and net due foreign remain in a separate non-rate-sensitive funding proxy. The H.8 residual is the stylized equity proxy. It is not regulatory capital, a regulatory capital ratio, or a BCBS supervisory outlier test denominator.

Within public totals, loan splits of 40:25:10 and deposit splits of 55:20 are model assumptions. Broad securities become synthetic fixed-rate government holdings; no trading book is reconstructed. Origination/maturity/reset dates, coupons, spreads, amortization, deposit betas, behavioral maturities, runoff and haircuts are synthetic assumptions. Fixed seed **20261023**, normalized lognormal weights and cent rounding create a manageable **938** records; counts are not inflated to imply real bank coverage. [Field dictionary](data/processed/field_dictionary.csv), [calibrated totals](data/processed/calibrated_product_totals.json), [configuration](src/config.py) and [methodology](docs/methodology.md) separate observation from simulation.

## Reproduce the locked run

Valuation date is locked to **2026-10-23**. Work from this project directory. Python 3.12 is the verified runtime; dependencies are in [requirements.txt](requirements.txt). A normal local environment can run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.public_data
python -m src.pipeline
python -m src.figures
python -m src.prepare_artifacts
python -m src.write_documentation
python -m src.build_report
python -m pytest -q
```

`src.source_validation` is the mandatory release gate. It validates the versioned [public-source lock](config/public_source_lock.json), both official raw snapshots, the exact observation extracts, the consumed curve, H.8 calibration lineage, dates, schemas, units, maturities, ordering, uniqueness, missing values and numeric ranges before analysis or artifact writes. The locked release has no refresh or bypass flag. A different vintage must be acquired and reviewed outside this release, then committed with a new lock.

Excel authoring was verified with Node **24.22.1** and `@oai/artifact-tool` **2.8.103** from the Codex workspace dependency bundle. Resolve the bundle with the workspace dependency loader, then run the complete workbook build and verification sequence below. The ignored `node_modules` symlink is local only and is not distributed.

```bash
export CODEX_NODE="<Node.js executable returned by the workspace dependency loader>"
export CODEX_NODE_MODULES="<Node.js packages returned by the workspace dependency loader>"
ln -s "$CODEX_NODE_MODULES" node_modules
ALM_PYTHON="$(command -v python)" "$CODEX_NODE" src/build_workbook.mjs
"$CODEX_NODE" src/verify_workbook.mjs
python -m src.artifact_validation
```

The workbook is a read-only management snapshot with live summary/delta formulas, 15 native tables and four native charts. Change the Python source/configuration and rerun the full pipeline and builders to refresh it. LibreOffice is used separately for forced native recalculation and saved-file formula checks.

The Word report uses `python-docx`. Its required visual QA uses the Documents skill's `render_docx.py` with LibreOffice and PDF rasterization; rendering is a separate external dependency. The retained page PNGs and PDF in `qa/render` are internal QA evidence. [Actual runtime versions](outputs/metrics/environment.json) record the analytics environment.

## Methods and controls

- Repricing gap: eight exact monthly-anniversary buckets; whole principal at first reset or fixed maturity. Non-rate-sensitive values contribute no RSA/RSL.
- NII: 12 monthly ACT/365 periods, existing-book runoff, fixed coupons, contractual maturity, equal-principal amortization, floating resets, deposit betas and behavioral runoff.
- EVE: full-life asset minus liability discounted cash flows, excluding equity, with reprojected floating coupons. Short simple-rate quotes and synthetic semiannual par bootstrap generate log-linearly interpolated discount factors. Cash and other non-rate-sensitive items use carrying values.
- Internal scenarios: Base, parallel +/-100/+/-200 bps, steepener `0.01*(1-2*exp(-t/4))`, and its negative flattener. Shock par nodes then bootstrap. No BCBS standardized implementation is claimed.
- Liquidity: 90-day daily ledger, stress retail runoff, maturing funding nonrenewal, commitment draws, haircuts, timed asset monetization, collected contractual inflows and an internal daily 75% inflow cap. Sold securities' cash flows are excluded. No breach is right-censored at the horizon.
- DuckDB executes [balance controls](sql/balance_sheet.sql), [independent bucket assignment](sql/repricing_gap.sql), [scenario cash-flow aggregation](sql/scenario_reconciliation.sql) and [liquidity reconstruction](sql/liquidity_aggregation.sql). The [machine-readable classification](outputs/metrics/sql_reconciliation_classification.csv) records two `INDEPENDENT_RECOMPUTATION` and three `PARTIAL_RECOMPUTATION` controls. No control is described as independent valuation. Maximum difference is **USD 0.0000008158**, versus USD 0.01 tolerance.
- **30 dataset controls** pass. The full pytest count, source-binding attacks and final artifact checks are recorded in [QA evidence](qa/QA_REPORT.md). The workbook formula probe changes a source NII cell, observes dependent recalculation and restores it before export. Saved cell caches and report core numbers are checked against the same payload.

## Directory and status

[src](src) contains generation, valuation, liquidity, control and presentation code. [sql](sql) contains executed reconciliation SQL; [data/raw](data/raw) contains official frozen inputs; [data/processed](data/processed) contains contracts, lineage, full cash flows in Parquet and a DuckDB database; [outputs/tables](outputs/tables), [figures](outputs/figures) and [metrics](outputs/metrics) hold reviewed results. [report](report), [tests](tests) and [qa](qa) contain deliverables and evidence. [STATUS.md](STATUS.md) records the latest recovery checkpoint.

Skills used: Data analysis/report framing, Documents and Spreadsheets. Local methodology is project-specific and does not import another portfolio repository. User-requested project-local paths take precedence over the workspace guide's generic shared-output convention. No push or PR was created.

## Known limitations

The model omits prepayment, default, options, hedges, basis/credit-spread/FX risk, exact instrument payment calendars, depositor insurance/concentration, intraday settlement, encumbrance, reserve requirements, margin calls and other-liability cash demands. Cash yield is fixed at zero. Other categories are insensitive carrying-value proxies. Treasury forwards proxy the lending index. Internal sub-product mixes, betas, maturities, caps and liquidity haircuts are not empirically estimated from H.8. Daily excess inflows are discarded under the cap. Full eligibility and fixed haircut liquidity are assumed for government proxies. See [full methodology and boundaries](docs/methodology.md) before interpreting results or extending the model.

The project is complete when [STATUS.md](STATUS.md) is QA_COMPLETE; acceptance evidence is in [qa/checks.json](qa/checks.json). Continue only missing stages after interruption and reuse verified outputs.

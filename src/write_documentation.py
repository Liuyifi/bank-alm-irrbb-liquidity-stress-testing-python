"""Generate traceable project README, field definitions and resume evidence."""
import csv
import json
from pathlib import Path
from .config import ROOT


def build():
    from .source_validation import validate_sources
    validate_sources()
    m=json.loads((ROOT/"outputs/metrics/key_metrics.json").read_text())
    line=json.loads((ROOT/"data/processed/public_data_lineage.json").read_text())
    definitions={
        'position_id':'Unique synthetic product/record key', 'product':'Internal stylized product classification',
        'asset_or_liability':'asset, liability or equity', 'principal':'Outstanding USD at valuation, cent-exact calibrated group allocation',
        'coupon_rate':'Annual decimal current coupon; current corporate forward proxy + spread or internal fixed bounds',
        'fixed_or_floating':'fixed, floating or non_rate', 'origination_date':'Simulated date before valuation; not observed contract history',
        'contractual_maturity':'Legal maturity; NMD demand maturity is next day',
        'next_repricing_date':'First scheduled reset; fixed positions use final maturity',
        'repricing_frequency':'1M, 3M or none','repricing_frequency_months':'Integer reset interval, zero if not applicable',
        'next_reset_month':'Months from valuation to first reset, zero for immediate NMD repricing',
        'amortization_type':'equal_principal, bullet, behavioral_equal_principal, cash, equity or carrying_value',
        'reference_rate':'Treasury-implied forward proxy for floaters; none otherwise',
        'spread':'Annual decimal fixed corporate spread, not a credit-spread stress',
        'behavioral_maturity_months':'NMD modeled principal runoff horizon, zero if not NMD',
        'behavioral_maturity':'Model effective maturity date; contractual maturity for other dated products',
        'remaining_maturity_months':'Remaining modeled calendar months; NMD behavioral horizon',
        'deposit_beta':'NMD coupon pass-through factor, annual rate change times beta',
        'runoff_assumption':'Baseline 90-day NMD runoff fraction before liquidity scenario multiplier',
        'liquidity_haircut':'Base haircut on eligible security Base EVE market value',
        'undrawn_commitment':'USD off-balance-sheet corporate commitment, 40% of current principal',
        'currency':'USD only','record_grain':'Contract or explicit position group',
        'bucket_order':'Derived first-reset bucket order 0 through 7',
        'bucket':'Derived label for next repricing/maturity bucket'}
    with open(ROOT/'data/processed/field_dictionary.csv','w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['field','classification','definition'])
        for k,v in definitions.items():w.writerow([k,'Synthetic allocation calibrated to public aggregate' if k=='principal' else ('Derived model field' if k in ('bucket','bucket_order') else 'Model assumption / synthetic field'),v])
    hashes='\n'.join(f"| [{Path(x['path']).name}]({x['path']}) | `{x['sha256']}` |" for x in line['files'])
    text=f'''# Banking Book Interest Rate and Liquidity Stress Testing

An independent Treasury Risk and ALM portfolio project with **{m['positions']} synthetic contract/group records**, USD 100 million assets, official public calibration and a complete Python / DuckDB / Excel / Word workflow.

The default +200 bps internal shock changes 12-month NII by **USD {m['worst_delta_nii']:,.0f}** and EVE by **USD {m['worst_delta_eve']:,.0f}**. All three liquidity scenarios survive the tested 90 days. Combined ends with **USD {m['liquidity_scenarios'][2]['remaining_liquidity_buffer']:,.0f}** cash. Survival is **at least 90 days**, not an estimate beyond the window. Deposit beta sensitivity reverses the NII direction, so the small default earnings loss must be interpreted with its behavioral assumptions.

This is a synthetic banking-book study calibrated to industry aggregates. It does not represent any real bank, train a credit model, predict defaults or perform trading-book VaR backtesting. Shocks are internal illustrations. H.8 residual normalizes the equity proxy and is not regulatory capital. Liquidity measures are internal proxies, with no formal LCR/NSFR calculation. The model has not been used in production.

## Deliverables

- [Nine-page English Word management report](report/Banking_Book_Interest_Rate_and_Liquidity_Stress_Testing_Report.docx)
- [Excel management pack with 12 sheets](outputs/Bank_Treasury_Risk_Management_Pack.xlsx)
- [QA report](qa/QA_REPORT.md), [machine-readable checks](qa/checks.json) and [official public-source checks](qa/public_source_checks.json)
- [Exact key metrics](outputs/metrics/key_metrics.json), [H.8 calibration](outputs/tables/h8_balance_sheet_calibration.csv), [contract/group ledger](data/processed/positions.csv)
- [NMD model sensitivity](outputs/tables/nmd_model_sensitivity.csv) and [resume bullets](RESUME_BULLETS.md)
- [Source attribution and distribution notes](DATA_SOURCES.md) and [MIT license](LICENSE)

## Observed public inputs

Treasury: **{line['treasury']['observation_date']}** observation, selected feed entry updated **{line['treasury']['feed_updated_timestamp']}**. The publication-date metadata is the Atom entry update date; it is not a separate claim about the exact market-close publication time. Acquired from [US Treasury official annual XML]({line['treasury']['source_url']}). Annual raw response, selected entry and dated CSV are frozen. These are par yields, not observed zero rates or SOFR.

Federal Reserve H.8: release **{line['h8']['release_date']}**, observation **{line['h8']['observation_date']}**, **all commercial banks in the United States**, **not seasonally adjusted**. Downloaded from [Federal Reserve official XML archive]({line['h8']['source_url']}) and cross-checked against the [official current release]({line['h8']['release_page']}). XML USD millions are divided by 1000 for the stored USD billions extract. XML/HTML differences are within the table's 0.05 billion rounding. The current URL may change; frozen bytes and hashes identify this run.

Acquisition time: **{line['download_time']}**. No public-source fallback was used. [Full public data lineage and field mapping](data/processed/public_data_lineage.json) records dates, source URLs, units, adjustment, response sizes and SHA256. Hashes below identify every frozen source file.

| Frozen source | SHA256 |
| --- | --- |
{hashes}

## Calibration and synthetic fields

Observed H.8 cash, securities, gross loans, deposits, borrowings, other liabilities, net due foreign offices and residual proportions calibrate USD 100m assets. [The calibration table](outputs/tables/h8_balance_sheet_calibration.csv) preserves asset and funding proportions to a predefined **0.01 percentage point** tolerance. Remaining asset categories, including the allowance adjustment, remain in a net other-assets proxy. Other liabilities and net due foreign remain in a separate non-rate-sensitive funding proxy. The H.8 residual is the stylized equity proxy. It is not regulatory capital, a regulatory capital ratio, or a BCBS supervisory outlier test denominator.

Within public totals, loan splits of 40:25:10 and deposit splits of 55:20 are model assumptions. Broad securities become synthetic fixed-rate government holdings; no trading book is reconstructed. Origination/maturity/reset dates, coupons, spreads, amortization, deposit betas, behavioral maturities, runoff and haircuts are synthetic assumptions. Fixed seed **20261023**, normalized lognormal weights and cent rounding create a manageable **{m['positions']}** records; counts are not inflated to imply real bank coverage. [Field dictionary](data/processed/field_dictionary.csv), [calibrated totals](data/processed/calibrated_product_totals.json), [configuration](src/config.py) and [methodology](docs/methodology.md) separate observation from simulation.

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
- DuckDB executes [balance controls](sql/balance_sheet.sql), [independent bucket assignment](sql/repricing_gap.sql), [scenario cash-flow aggregation](sql/scenario_reconciliation.sql) and [liquidity reconstruction](sql/liquidity_aggregation.sql). The [machine-readable classification](outputs/metrics/sql_reconciliation_classification.csv) records two `INDEPENDENT_RECOMPUTATION` and three `PARTIAL_RECOMPUTATION` controls. No control is described as independent valuation. Maximum difference is **USD {m['python_sql_max_difference']:.10f}**, versus USD 0.01 tolerance.
- **30 dataset controls** pass. The full pytest count, source-binding attacks and final artifact checks are recorded in [QA evidence](qa/QA_REPORT.md). The workbook formula probe changes a source NII cell, observes dependent recalculation and restores it before export. Saved cell caches and report core numbers are checked against the same payload.

## Directory and status

[src](src) contains generation, valuation, liquidity, control and presentation code. [sql](sql) contains executed reconciliation SQL; [data/raw](data/raw) contains official frozen inputs; [data/processed](data/processed) contains contracts, lineage, full cash flows in Parquet and a DuckDB database; [outputs/tables](outputs/tables), [figures](outputs/figures) and [metrics](outputs/metrics) hold reviewed results. [report](report), [tests](tests) and [qa](qa) contain deliverables and evidence. [STATUS.md](STATUS.md) records the latest recovery checkpoint.

Skills used: Data analysis/report framing, Documents and Spreadsheets. Local methodology is project-specific and does not import another portfolio repository. User-requested project-local paths take precedence over the workspace guide's generic shared-output convention. No push or PR was created.

## Known limitations

The model omits prepayment, default, options, hedges, basis/credit-spread/FX risk, exact instrument payment calendars, depositor insurance/concentration, intraday settlement, encumbrance, reserve requirements, margin calls and other-liability cash demands. Cash yield is fixed at zero. Other categories are insensitive carrying-value proxies. Treasury forwards proxy the lending index. Internal sub-product mixes, betas, maturities, caps and liquidity haircuts are not empirically estimated from H.8. Daily excess inflows are discarded under the cap. Full eligibility and fixed haircut liquidity are assumed for government proxies. See [full methodology and boundaries](docs/methodology.md) before interpreting results or extending the model.

The project is complete when [STATUS.md](STATUS.md) is QA_COMPLETE; acceptance evidence is in [qa/checks.json](qa/checks.json). Continue only missing stages after interruption and reuse verified outputs.
'''
    (ROOT/'README.md').write_text(text)
    (ROOT/'RESUME_BULLETS.md').write_text(f'''# Evidence based resume bullets

Project: Banking Book Interest Rate and Liquidity Stress Testing. Independent synthetic portfolio project; no real-bank or production claim.

## English

- Built a reproducible Python ALM engine for {m['positions']} synthetic contract/group records and USD 100m assets, calibrating category shares to official Federal Reserve H.8 and discount curves to official US Treasury par yields, with frozen source hashes and data lineage.
- Simulated seven internal IRRBB scenarios for repricing gaps, 12-month NII and full-life EVE; quantified a USD {abs(m['worst_delta_eve'])/1e6:.2f}m EVE decline under +200 bps and tested how deposit betas and behavioral maturities change risk interpretation.
- Implemented daily 90-day liquidity survival proxies for three stress scenarios, reconciled five Python/DuckDB controls to USD 0.01 tolerance, and delivered an English Word report and a 12-sheet Excel management pack with automated and visual QA.

## 中文

- 独立构建 Python 银行账簿 ALM 项目，以美联储 H.8 官方行业占比校准 1 亿美元假设资产负债表，生成 {m['positions']} 笔可复现 synthetic 合同或头寸组，并保存 Treasury 官方曲线、来源哈希及数据血缘。
- 完成七类内部利率情景下的重定价缺口、12 个月净利息收入及全期限经济价值分析，量化 +200 bps 下约 {abs(m['worst_delta_eve'])/1e4:.1f} 万美元 EVE 下降，并开展存款 beta 与行为期限敏感性分析。
- 实现三类 90 天流动性压力生存分析和五项 Python／DuckDB 结果对账，交付九页英文 Word 报告与 12 页签 Excel 管理包，保留自动化控制及实际渲染检查证据。

Evidence: [metrics](outputs/metrics/key_metrics.json), [QA](qa/QA_REPORT.md), [official lineage](data/processed/public_data_lineage.json). Amounts and scenarios are modeled, not realized financial performance. The H.8 residual-based equity proxy is not regulatory capital and the reported percentage is not a supervisory outlier test. Liquidity outputs are not formal LCR/NSFR.
''')
    print('README, field dictionary and resume bullets written.')


if __name__=='__main__':build()

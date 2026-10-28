# Evidence based resume bullets

Project: Banking Book Interest Rate and Liquidity Stress Testing. Independent synthetic portfolio project; no real-bank or production claim.

## English

- Built a reproducible Python ALM engine for 938 synthetic contract/group records and USD 100m assets, calibrating category shares to official Federal Reserve H.8 and discount curves to official US Treasury par yields, with frozen source hashes and data lineage.
- Simulated seven internal IRRBB scenarios for repricing gaps, 12-month NII and full-life EVE; quantified a USD 3.17m EVE decline under +200 bps and tested how deposit betas and behavioral maturities change risk interpretation.
- Implemented daily 90-day liquidity survival proxies for three stress scenarios, reconciled five Python/DuckDB controls to USD 0.01 tolerance, and delivered an English Word report and a 12-sheet Excel management pack with automated and visual QA.

## 中文

- 独立构建 Python 银行账簿 ALM 项目，以美联储 H.8 官方行业占比校准 1 亿美元假设资产负债表，生成 938 笔可复现 synthetic 合同或头寸组，并保存 Treasury 官方曲线、来源哈希及数据血缘。
- 完成七类内部利率情景下的重定价缺口、12 个月净利息收入及全期限经济价值分析，量化 +200 bps 下约 316.7 万美元 EVE 下降，并开展存款 beta 与行为期限敏感性分析。
- 实现三类 90 天流动性压力生存分析和五项 Python／DuckDB 结果对账，交付九页英文 Word 报告与 12 页签 Excel 管理包，保留自动化控制及实际渲染检查证据。

Evidence: [metrics](outputs/metrics/key_metrics.json), [QA](qa/QA_REPORT.md), [official lineage](data/processed/public_data_lineage.json). Amounts and scenarios are modeled, not realized financial performance. The H.8 residual-based equity proxy is not regulatory capital and the reported percentage is not a supervisory outlier test. Liquidity outputs are not formal LCR/NSFR.

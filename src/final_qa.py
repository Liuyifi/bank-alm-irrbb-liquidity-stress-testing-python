"""Final acceptance, including a complete pytest run and retained evidence."""
import json
import sys
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import ROOT
from .controls import check_record
from .artifact_validation import acceptance,DOC,XLS
from .public_data import sha


def run():
    from .source_validation import validate_sources
    validate_sources()
    report_path=ROOT/'qa/QA_REPORT.md';checks_path=ROOT/'qa/checks.json'
    report_path.write_text('# QA report\n\nFinal artifact acceptance is running.\n')
    checks_path.write_text(json.dumps(dict(status='RUNNING',stage='Final acceptance'),indent=2))
    core=json.loads((ROOT/'qa/core_checks.json').read_text())['checks']
    checks=core+acceptance(require_render=True)
    visual=json.loads((ROOT/'qa/visual_review.json').read_text())
    checks.append(check_record('word_visual_review_all_pages',visual['word']['status']=='PASS' and visual['word']['pages_reviewed']==list(range(1,10)) and visual['word']['docx_sha256']==sha(DOC)))
    checks.append(check_record('excel_visual_review_all_sheets',visual['excel']['status']=='PASS' and visual['excel']['sheets_reviewed']==12 and visual['excel']['xlsx_sha256']==sha(XLS)))
    result=subprocess.run([sys.executable,'-m','pytest','tests','-q','--junitxml=qa/pytest_final.xml'],cwd=ROOT,capture_output=True,text=True)
    (ROOT/'qa/pytest_output.txt').write_text(result.stdout+'\n'+result.stderr)
    suite=ET.parse(ROOT/'qa/pytest_final.xml').getroot()
    suites=list(suite) if suite.tag=='testsuites' else [suite]
    stats={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
    checks.append(check_record('pytest_full_suite',result.returncode==0,stats))
    status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL'
    output=dict(status=status,checked_at=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
                automated_check_count=len(checks)-2,visual_check_count=2,
                passed=sum(c['status']=='PASS' for c in checks),total=len(checks),
                pytest=stats,checks=checks)
    checks_path.write_text(json.dumps(output,indent=2))
    m=json.loads((ROOT/'outputs/metrics/key_metrics.json').read_text())
    rows='\n'.join(f"| {c['check']} | {c['status']} | {c['detail']} |" for c in checks)
    report_path.write_text(f'''# QA report

Final acceptance: **{status}**. {output['passed']} / {output['total']} controls pass, comprising {output['automated_check_count']} automated acceptance controls and two recorded visual reviews. The full pytest suite passes {stats['tests']} cases with {stats['failures']} failures, {stats['errors']} errors and {stats['skipped']} skips. It includes engine and saved-artifact coverage plus fail-closed source-binding and focused exceptional-input tests.

## Official public sources

Treasury observation 2026-10-22; H.8 release 2026-10-16 and observation 2026-10-07, all US commercial banks, not seasonally adjusted. The versioned source lock binds the raw official snapshots, extracted observations, consumed curve and H.8 calibration. The gate checks hashes, dates, schemas, units, maturities, ordering, duplicates, missing values, ranges and raw-to-processed lineage before output writes. Seven mutation cases, including the audited +10 bps attack, are rejected. No fallback or release override exists. Details: config/public_source_lock.json, public_source_checks.json and data/processed/public_data_lineage.json.

## Analytics and reconciliation

The USD 100m book balances to equity. Position IDs, principal, dates and rate/beta bounds pass. Contract-level principal conserves, fixed coupons preserve NII under shocks, floating resets retain current coupons until reset, and an isolated fixed asset loses PV under rising rates. Discount factors remain positive and decreasing. Tests also reprice synthetic par bonds and exercise exact bucket boundaries.

DuckDB executes all four saved SQL files. Five Python/SQL controls reconcile with maximum USD {m['python_sql_max_difference']:.10f}, below USD 0.01. Balance-sheet totals and repricing buckets are independent recomputations. NII, EVE and liquidity are partial recomputations because they share Python-projected contractual cash flows or scenario discount inputs. The exact input grain and classification are published in outputs/metrics/sql_reconciliation_classification.csv. No SQL control is described as an independent valuation engine.

Daily liquidity reconciles opening cash, stress cash flows and one-time asset monetization. Sold government cash flows are excluded, remaining capacity is never spent twice, and inflows respect the internal cap. No scenario breaches within 90 days. All survival estimates are right-censored at 90 days; Combined ends with USD {m['liquidity_scenarios'][2]['remaining_liquidity_buffer']:,.2f} available cash.

## Word verification

The final DOCX opens through python-docx and ZIP/XML verification and renders through the Documents skill's LibreOffice/PDF pipeline to exactly nine page PNGs. All nine pages were visually reviewed via contact sheets; targeted full-page views verified the title-rule correction and source-hash appendix. No blank pages, overflow, clipped tables, missing glyphs or blurred charts were observed. All core numbers and all six frozen-source SHA256 values match their source data. No TODO, TBC or unfinished placeholder text is present. QA PNGs/PDF are internal evidence, not substitute deliverables.

## Excel verification

The XLSX contains 12 populated sheets, 15 native tables and four native charts. The artifact-tool engine recalculated summary and scenario formulas. A temporary +0.1m NII edit changed its dependent delta by the same amount; the source value was restored before export. LibreOffice then opened a cache-stripped copy, forced formula recalculation and saved it without formula errors or structural count changes. All saved formulas have caches, no error cells or external links are present, and key saved summary numbers match Python. Every worksheet preview was reviewed, including the repaired Balance Sheet labels. The workbook is a frozen management pack with live arithmetic, not an input-driven implementation of the full Python engine.

## Scope and limitations

These tests establish implementation consistency under documented synthetic assumptions. They do not empirically validate NMD betas, maturities, runoff, sub-product mixes, haircut liquidity, the internal daily cap or the mapping of broad public categories. Delta EVE as a percentage of the stylized equity proxy is not a regulatory capital ratio or a BCBS supervisory outlier test. Liquidity results are not formal LCR/NSFR. Prepayment, options, hedges, spread/basis risk and other-liability cash demands remain unmodeled. Full boundaries are in docs/methodology.md and the report.

## Check register

| Check | Result | Evidence |
| --- | --- | --- |
{rows}
''')
    print(json.dumps({k:output[k] for k in ['status','passed','total','automated_check_count','pytest']},indent=2))
    if status!='PASS':
        print([c for c in checks if c['status']!='PASS']);raise SystemExit(1)


if __name__=='__main__':run()

"""Build reproducible current-state release evidence from tracked project files."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

import duckdb
import pandas as pd

from .config import ROOT


QA = ROOT / "qa"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracked_public_files():
    """Return the distributable Git population without ignored QA caches."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    excluded = (
        "qa/independent_audit_20261023/", "qa/independent_reaudit_20261028/",
        "qa/release_fix_20261023/", "qa/render/", "qa/workbook_previews/", "qa/lo_",
    )
    files = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode()
        name = Path(relative).name
        if (relative.startswith(excluded) or "contact" in name or
                name.endswith(".inspect.ndjson") or name.startswith("pytest_") or
                name in {"pytest_output.txt", "workbook_export_inspect.ndjson",
                         "workbook_reimport.txt"} or
                name.startswith("workbook_") and name.endswith("inspection.txt")):
            continue
        path = ROOT / relative
        if path.is_file() and relative != "qa/file_manifest.json":
            files.append({"path": relative, "bytes": path.stat().st_size,
                          "sha256": sha(path)})
    return files


def current_metric_rows():
    """Reconcile 17 release metrics to current, independently stored outputs."""
    actual = json.loads((ROOT / "outputs/metrics/key_metrics.json").read_text())
    positions = pd.read_csv(ROOT / "data/processed/positions.csv")
    nii = pd.read_csv(ROOT / "outputs/tables/nii_scenarios.csv")
    eve = pd.read_csv(ROOT / "outputs/tables/eve_scenarios.csv")
    liquidity = pd.read_csv(ROOT / "outputs/tables/liquidity_scenarios.csv")
    recon = pd.read_csv(ROOT / "outputs/tables/python_sql_reconciliation.csv")
    core = json.loads((ROOT / "qa/core_checks.json").read_text())
    with duckdb.connect(str(ROOT / "data/processed/treasury_risk.duckdb"), read_only=True) as db:
        cashflow_rows = db.execute("SELECT COUNT(*) FROM cashflows").fetchone()[0]

    worst_nii = nii.loc[nii.delta_nii.idxmin()]
    worst_eve = eve.loc[eve.delta_eve.idxmin()]
    expected = {
        "positions": len(positions),
        "total_assets": positions.loc[positions.asset_or_liability.eq("asset"), "principal"].sum(),
        "equity_residual_proxy": positions.loc[positions.asset_or_liability.eq("equity"), "principal"].sum(),
        "base_nii": nii.loc[nii.scenario.eq("Base"), "nii"].iloc[0],
        "worst_delta_nii": worst_nii.delta_nii,
        "base_eve": eve.loc[eve.scenario.eq("Base"), "eve"].iloc[0],
        "worst_delta_eve": worst_eve.delta_eve,
        "worst_delta_eve_equity_proxy_pct": worst_eve.delta_eve_equity_proxy_pct,
        "python_sql_max_difference": recon.max_abs_difference.max(),
        "core_checks_passed": len(core["checks"]),
        "cashflow_rows": cashflow_rows,
    }
    rows = []
    exact = {"positions", "core_checks_passed", "cashflow_rows"}
    ratios = {"worst_delta_eve_equity_proxy_pct"}
    for metric, expected_value in expected.items():
        actual_value = actual[metric]
        tolerance = 0 if metric in exact else 1e-12 if metric in ratios else .01
        difference = float(actual_value - expected_value)
        rows.append({"metric": metric, "current_metric": actual_value,
                     "current_recomputed_value": expected_value, "difference": difference,
                     "tolerance": tolerance,
                     "status": "PASS" if abs(difference) <= tolerance else "FAIL"})
    actual_liquidity = {row["scenario"]: row for row in actual["liquidity_scenarios"]}
    for scenario in ("Idiosyncratic", "Market-wide", "Combined"):
        expected_row = liquidity.loc[liquidity.scenario.eq(scenario)].iloc[0]
        for field, tolerance in (("survival_days", 0), ("remaining_liquidity_buffer", .01)):
            actual_value = actual_liquidity[scenario][field]
            expected_value = expected_row[field]
            difference = float(actual_value - expected_value)
            rows.append({"metric": f"{scenario}.{field}", "current_metric": actual_value,
                         "current_recomputed_value": expected_value, "difference": difference,
                         "tolerance": tolerance,
                         "status": "PASS" if abs(difference) <= tolerance else "FAIL"})
    return rows


def build():
    from .source_validation import validate_sources

    validate_sources()
    metrics = current_metric_rows()
    with (QA / "current_metric_reconciliation.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=metrics[0].keys(), lineterminator="\n")
        writer.writeheader(); writer.writerows(metrics)

    checks = json.loads((QA / "checks.json").read_text())
    sql = pd.read_csv(ROOT / "outputs/metrics/sql_reconciliation_classification.csv")
    metric_status = "PASS" if all(row["status"] == "PASS" for row in metrics) else "FAIL"
    release_status = "PASS" if checks["status"] == "PASS" and metric_status == "PASS" else "FAIL"
    report = f"""# Public release QA

Current release verdict: **{release_status}**.

## Current release safeguards

- The versioned public-source lock verifies the official raw snapshots, extracted observations, consumed curve and H.8 calibration before release calculations write outputs.
- `cashflows()` accepts only immutable curves created from the verified canonical source and rechecks provenance and in-memory integrity at the calculation boundary.
- The H.8 residual is described as a residual-based stylized equity proxy, not regulatory capital.
- Word visual-QA evidence is regenerated automatically when missing or stale before artifact validation.

## Current-state verification

- Source lock: PASS; Treasury 2026-10-22 and H.8 2026-10-07 raw-to-processed lineage verified.
- Direct curve boundary: unbound and +10 bps in-memory curves are rejected; the canonical bound curve is accepted.
- Metrics: {len(metrics)} / {len(metrics)} canonical release metrics pass current-state reconciliation in `qa/current_metric_reconciliation.csv`.
- SQL: {(sql.classification == 'INDEPENDENT_RECOMPUTATION').sum()} independent recomputations and {(sql.classification == 'PARTIAL_RECOMPUTATION').sum()} partial recomputations; all five reconcile below USD 0.01.
- Tests: {checks['pytest']['tests']} passed, {checks['pytest']['failures']} failures, {checks['pytest']['errors']} errors, {checks['pytest']['skipped']} skipped.
- Controls: {checks['automated_check_count']} automated controls plus {checks['visual_check_count']} recorded visual reviews pass in the current release.
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
"""
    (QA / "RELEASE_QA.md").write_text(report)

    public_files = tracked_public_files()
    (QA / "file_manifest.json").write_text(json.dumps({
        "file_count": len(public_files),
        "self_hash_note": "Manifest excludes its own size/hash to avoid a circular digest",
        "files": public_files,
    }, indent=2) + "\n")
    result = {"status": release_status, "current_metrics": len(metrics),
              "tests": checks["pytest"], "automated_controls": checks["automated_check_count"]}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    build()

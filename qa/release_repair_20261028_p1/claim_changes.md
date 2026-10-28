# Public claim changes

## Repair rule

Claims that require an unavailable prior-version baseline were removed from portfolio-facing content. Historical data was not reconstructed or fabricated. Current release evidence reports only values that can be recomputed from the checked-out repository.

## Updated surfaces

- `README.md`, `STATUS.md`, and `RESUME_BULLETS.md` now use current-state wording.
- `qa/RELEASE_QA.md` reports 17 current canonical metrics, 60 current tests, and 52 current automated controls.
- `qa/QA_REPORT.md`, `qa/checks.json`, and `qa/current_metric_reconciliation.csv` contain current-run evidence.
- `src/release_fix_evidence.py`, `src/final_qa.py`, and `src/write_documentation.py` no longer generate prior-baseline retention language.
- `qa/file_manifest.json` inventories current tracked public files only and excludes archival independent-audit and generated render-cache directories.

## Current-state substantiation

`python -m src.release_fix_evidence` returned:

```text
status=PASS
current_metrics=17
tests=60, failures=0, errors=0, skipped=0
automated_controls=52
```

The public-claim scan excluded the preserved independent-audit directory and found no remaining unavailable-baseline wording. The terminology scan found no positive regulatory capital label; the remaining Tier 1 reference is an explicit statement that the normalization proxy is not regulatory Tier 1.

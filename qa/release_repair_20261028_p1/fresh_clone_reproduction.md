# Fresh-clone reproduction

## Candidate and isolation

- Tested implementation commit: `3093f355960b612c67f4d5c336e4ef94720e817d`
- Successful disposable checkout: `/private/tmp/bank-alm-release-repair.llqryn/repo-py312`

The clone-created local `origin` was removed before running the project. The main repository had no remote and remained without one.

An initial disposable attempt resolved the host's bare `python3` to Python 3.9.6. That did not meet README's stated Python 3.12 prerequisite, and the sandbox correctly blocked an unapproved dependency download. No project command was run in that checkout. A second fresh clone used the Python 3.12 executable returned by the workspace dependency loader as `python3`; dependency installation was then explicitly approved.

## Exact successful commands

```bash
git clone --no-local --no-hardlinks /Users/yfl/GptWorkspace/projects/bank-alm-irrbb-liquidity-stress-testing-python /private/tmp/bank-alm-release-repair.llqryn/repo-py312
cd /private/tmp/bank-alm-release-repair.llqryn/repo-py312
git remote remove origin
git rev-parse HEAD
env PATH=/Users/yfl/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin:$PATH python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m src.public_data
python -m src.pipeline
python -m src.figures
python -m src.prepare_artifacts
python -m src.write_documentation
python -m src.build_report
python -m pytest -q
export CODEX_NODE="/Users/yfl/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
export CODEX_NODE_MODULES="/Users/yfl/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
ln -s "$CODEX_NODE_MODULES" node_modules
ALM_PYTHON="$(command -v python)" "$CODEX_NODE" src/build_workbook.mjs
"$CODEX_NODE" src/verify_workbook.mjs
command -v soffice
command -v pdftoppm
python -m src.render_report
python -m src.artifact_validation
```

## Results

```text
HEAD: 3093f355960b612c67f4d5c336e4ef94720e817d
Python: 3.12.14
Public sources: Treasury 2026-10-22; H.8 release 2026-10-16; fallback_used=false
Pipeline: positions=938; total_assets=100000000.0; core_checks_passed=30
Pipeline: base_nii=2567565.1057716478; worst_delta_nii=-32213.093824876007
Pipeline: base_eve=12927232.701620191; worst_delta_eve=-3166812.520569071
Pytest: 60 passed, 226 warnings in 7.94s
Workbook: SOURCE_BINDING_PASS; formula probe passed; 12 previews saved
Workbook verification: saved XLSX reimported; summary EVE matches Python
soffice: /Users/yfl/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice
pdftoppm: /Users/yfl/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm
Word render: WORD_RENDER_PASS; 9 pages
Artifact validation: PASS; checks=21; failed=[]
Fresh core checks: PASS; checks=30; failed=[]
Fresh key_metrics.json versus candidate: cmp exit 0
Fresh sql_reconciliation_classification.csv versus candidate: cmp exit 0
```

The only Word-render command needed was the command now documented before artifact validation: `python -m src.render_report`. There was no hidden manual render step. The generated `qa/render` directory remained ignored, so no render cache or bulk PDF/PNG output was committed.

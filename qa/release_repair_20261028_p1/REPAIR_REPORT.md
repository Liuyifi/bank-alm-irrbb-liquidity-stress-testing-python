# P1 release-readiness repair report

- Date: 2026-10-28
- Audited base: `3509fe757132cda4f641f04c786d1adbf6268919`
- Repair implementation commit: `3093f355960b612c67f4d5c336e4ef94720e817d`

## Scope and disposition

This was a narrow repair of the three P1 findings in the independent re-audit. The independent evidence under `qa/independent_reaudit_20261028/` was not edited, staged, or committed.

1. **Sensitive curve boundary: fixed.** `cashflows()` now accepts only an immutable curve carrying an opaque verified-source binding. It revalidates the canonical source and compares the complete in-memory curve state before calculation. Direct construction, a direct +10 bp curve, and a copied-then-mutated bound curve fail closed. A canonical bound curve and the guarded publication path continue to work.
2. **Public claims: fixed.** Public documentation and release evidence now make only current-state claims. The release evidence independently recomputes 17 current metrics from repository artifacts and does not rely on unavailable prior-version baselines.
3. **Fresh-clone Word rendering: fixed.** `python -m src.render_report` is documented before artifact validation with explicit LibreOffice and Poppler checks. Artifact validation also creates missing or stale render evidence automatically and returns an actionable dependency failure.

## Verification results

- Full pytest suite: **60 passed, 0 failed, 0 errors, 0 skipped**.
- Final controls: **54/54 passed**, comprising 52 automated controls and two recorded visual reviews.
- Artifact validation: **21/21 passed**.
- Current-state metric reconciliation: **17/17 passed**.
- Source-boundary suite: **19/19 passed**, including the formal source-tampering path and the direct-helper attacks.
- Fresh-clone core controls: **30/30 passed**.
- Fresh-clone Excel build: source binding passed, formula probe passed, 12 previews produced, and saved workbook reimport matched Python EVE.
- Fresh-clone Word render: **9 pages**, followed by artifact validation PASS.
- Fresh-clone key metrics and SQL classification files matched the repaired candidate byte-for-byte.
- The nine Word page images and 12 workbook sheet previews were visually reviewed without clipping, overlap, blank output, or broken charts/tables.

No financial assumptions or core financial outputs were changed. No remote was added to the main repository, and no push or release publication was performed.

Detailed evidence is in:

- `source_boundary_test.md`
- `claim_changes.md`
- `fresh_clone_reproduction.md`
- `files_changed.csv`

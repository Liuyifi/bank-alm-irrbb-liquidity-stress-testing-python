# Fresh clone validation

## Scope

A disposable local clone of the repair commit containing this report was created from the local repository. The original repository's remote configuration was not changed, no manual remote was added, and nothing was pushed. The clone used Python 3.12.14 and the workflow documented in `README.md`, followed by the independently required malicious-subclass probe.

## Documented workflow executed

1. `python3 -m venv .venv`
2. `source .venv/bin/activate`
3. `python -m pip install -r requirements.txt`
4. `python -m src.source_validation` (the mandatory release gate documented in `README.md`)
5. `python -m src.public_data`
6. `python -m src.pipeline`
7. `python -m src.figures`
8. `python -m src.prepare_artifacts`
9. `python -m src.write_documentation`
10. `python -m src.build_report`
11. `python -m pytest -q`
12. Workbook build and verification with the workspace dependency loader's Node.js and packages
13. `python -m src.render_report`
14. `python -m src.artifact_validation`
15. `python -m src.final_qa`

## Results

| Check | Result |
| --- | --- |
| Python | 3.12.14 |
| Source validation and pipeline | PASS |
| Word build and render | PASS: nine pages |
| Full pytest | PASS: 64 / 64 |
| Source-boundary module | PASS: 23 / 23 |
| Workbook build and saved-file verification | PASS |
| Artifact validation | PASS: 21 / 21 |
| Final acceptance | PASS: 54 / 54 controls, including 52 automated and two recorded visual reviews |
| Independent malicious subclass probe | PASS: rejected with `SourceValidationError` before financial computation |

The freshly regenerated nine Word page images and 12 workbook preview images were byte-for-byte identical to the already reviewed originals before the clone's artifact hashes were recorded. The independent probe combined an always-successful validation override with +10 bp content; the override was not invoked, and the exact concrete-type boundary rejected the object.

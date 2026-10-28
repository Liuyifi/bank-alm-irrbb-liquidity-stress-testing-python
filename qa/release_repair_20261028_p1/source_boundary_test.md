# Source-boundary repair and tests

## Authoritative contract

- `Curve.from_verified_source(scenario)` is the production constructor. It loads the canonical locked curve and attaches an opaque binding to the scenario.
- Curve arrays are stored as immutable tuples. Public array properties return copies, and normal attribute assignment is rejected.
- `cashflows()` is the authoritative sensitive boundary. Before any cash-flow rows or EVE inputs are produced, it requires the binding, re-runs source validation, reconstructs the expected scenario curve, and compares node times, shocked par rates, bootstrap times, and discount factors.
- `cashflows()` also checks scenario provenance and validates positions.
- `run_ir()` and the NMD sensitivity path use the verified constructor.

This rejects direct construction, filename-only metadata, a direct +10 bp curve, copied objects with altered rate state, and post-verification in-memory mutation. It preserves generic unbound curve construction for non-production bootstrap analysis, but an unbound instance cannot cross the sensitive boundary.

## Exact focused command and result

```bash
.venv/bin/python -m pytest -q tests/test_source_binding.py
```

```text
...................                                                      [100%]
19 passed in 5.73s
```

The suite covers:

- formal pipeline rejection before EVE for seven corrupt-source cases, including +10 bp;
- all publication entry points rejecting a corrupt source;
- direct unbound `Curve` rejection at `cashflows()`;
- direct in-memory +10 bp `Curve` rejection at `cashflows()`;
- canonical bound curve success;
- copied bound curve with private rate-state mutation rejection while the original remains valid.

The full suite also passed: `60 passed, 226 warnings in 7.37s`. The warnings are existing NumPy generic-timedelta deprecations and are not release failures.

# Source boundary attack matrix

| ID | Attack | Expected | Current result | Evidence |
| --- | --- | --- | --- | --- |
| A | Direct ordinary `Curve` without binding | Reject before computation | PASS | `test_direct_unbound_curve_rejected_at_cashflow_boundary` |
| B | Direct `Curve` built from +10 bp nodes | Reject before computation | PASS | `test_in_memory_ten_bp_curve_rejected_at_cashflow_boundary` |
| C | Valid bound curve changed after verification | Reject current-state mismatch | PASS | `test_post_verification_mutation_rejected_at_cashflow_boundary` |
| C2 | Shallow copy of a bound curve with changed discount factors | Reject current-state mismatch | PASS | `test_copied_bound_curve_cannot_hide_in_memory_mutation` |
| D | Subclass overrides `require_source_binding()` and provenance behavior | Reject without virtual dispatch | PASS | `test_malicious_subclass_override_is_rejected_without_virtual_validation`; override call count remains zero |
| E | Same malicious subclass with +10 bp rates | Reject before computation | PASS | `test_malicious_subclass_with_ten_bp_content_is_rejected` |
| F | Copy valid private binding metadata onto +10 bp concrete content | Reject current-state mismatch | PASS | `test_forged_copied_provenance_cannot_authorize_tampered_content` |
| G | Valid canonical exact `Curve` | Accept | PASS | `test_verified_canonical_curve_reaches_cashflow_boundary` |
| H | Formal frozen-source +10 bp file attack | Reject before `run_ir`/EVE and preserve outputs | PASS | `test_pipeline_rejects_before_eve_and_preserves_outputs[ten_bp]` |

The eight focused attack/acceptance selections pass together. The complete source-boundary module passes 23 / 23 tests.

# Subclass bypass fix

## Prior defect

The prior boundary used `isinstance(curve, Curve)` and then called `curve.require_source_binding()`. Because both decisions were polymorphic, a manually constructed `Curve` subclass could return success from its override and send altered rates into `cashflows()`.

## Authoritative design

`cashflows()` now calls the module-level `require_source_bound_curve(curve, scenario)` function. The function is production-owned and performs these checks before any sensitive computation:

1. `type(curve) is Curve`; every subclass is rejected.
2. The binding object must be the exact private binding type and carry the code-owned token.
3. The bound scenario, current curve scenario, and requested scenario must be exact built-in strings and must agree.
4. The locked source chain is revalidated at the boundary with `verified_curve()`.
5. A fresh exact `Curve` is reconstructed from the currently verified source and scenario.
6. `_node_t`, `_par`, `_times`, and `_dfs` must each be tuples containing only built-in floats and must equal the freshly reconstructed state.

The old overridable production `Curve.require_source_binding()` method was removed. A malicious subclass may still define a method with that name, but the authoritative boundary never calls it and rejects the subclass first.

## Weak-pattern review

- No production `isinstance(curve, Curve)` authorization remains.
- No production call to `curve.require_source_binding()` remains.
- No `curve.verified`, `curve.source_bound`, or mutable boolean authorizes calculation.
- No input-controlled `validate()` method is used.
- Stored binding metadata is insufficient: current numeric content is compared with a new curve reconstructed from the currently validated source.
- Validation occurs before position validation, forward-rate projection, discounting, cash-flow row creation, or EVE aggregation.
- Copying a valid binding onto +10 bp content fails the current-state comparison.
- Low-level mutation through `object.__setattr__` fails the same comparison.

## Why the attack cannot recur

Python subclasses cannot make `type(subclass_instance) is Curve` true. The exact-type decision is performed by trusted code before accessing any overridable property or method. For the accepted concrete type, the trusted verifier reads slot state directly, restricts the normalized state to built-in floats, and compares it with a fresh reconstruction from the current verified source. Input-controlled virtual behavior and copied provenance therefore cannot authorize altered curve content.

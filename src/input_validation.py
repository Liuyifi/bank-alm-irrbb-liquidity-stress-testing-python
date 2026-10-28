"""Reject malformed position inputs before cash-flow projection."""
import numpy as np


def validate_positions(p):
    required = {"position_id", "principal", "asset_or_liability", "coupon_rate",
                "fixed_or_floating", "repricing_frequency_months", "next_reset_month",
                "remaining_maturity_months", "behavioral_maturity_months"}
    if not required.issubset(p.columns):
        raise ValueError(f"Missing position fields: {sorted(required-set(p.columns))}")
    if p.empty or p.position_id.isna().any() or not p.position_id.is_unique:
        raise ValueError("Position IDs must be present and unique; portfolio cannot be empty")
    if not np.isfinite(p.principal).all() or not p.principal.gt(0).all():
        raise ValueError("Principal must be finite and positive")
    if not p.asset_or_liability.isin(["asset", "liability", "equity"]).all():
        raise ValueError("Invalid asset_or_liability")
    if not np.isfinite(p.coupon_rate).all() or not p.coupon_rate.between(0, .25).all():
        raise ValueError("Coupon rate must be finite and within [0, .25]")
    floating = p.fixed_or_floating.eq("floating")
    if not p.loc[floating, "repricing_frequency_months"].isin([1, 3]).all():
        raise ValueError("Floating repricing frequency must be 1 or 3 months")
    for col in ("remaining_maturity_months", "behavioral_maturity_months", "next_reset_month"):
        if not p[col].between(0, 360).all() or not (p[col] % 1 == 0).all():
            raise ValueError(f"Invalid {col}: expected integer months in [0, 360]")

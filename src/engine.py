"""Run-off NII and full-life EVE from one owning cash-flow schedule."""
import numpy as np
import pandas as pd
from .config import AS_OF, IR_SCENARIOS
from .market import Curve


def cashflows(positions, curve, scenario="Base", nmd_maturity_scale=1., beta_override=None):
    """ACT/365 monthly payments; equal principal or bullet; no principal replacement.

    Existing coupons remain locked until next reset. Corporate resets use the
    stressed curve-implied forward over the contractual reset tenor plus spread.
    NMD coupons follow initial coupon + beta*(one-month forward - initial index).
    NMD behavioral runoff replaces legal demand maturity only for IRRBB.
    """
    from .source_validation import SourceValidationError
    from .input_validation import validate_positions

    if not isinstance(curve, Curve):
        raise SourceValidationError("Cash-flow calculation requires a verified Curve")
    base_nodes = curve.require_source_binding()
    if scenario != curve.scenario:
        raise SourceValidationError("Cash-flow scenario does not match Curve provenance")
    validate_positions(positions)

    today = pd.Timestamp(AS_OF)
    dates = [today+pd.DateOffset(months=i) for i in range(362)]
    years = np.array([(d-today).days/365 for d in dates])
    # Initial index always from the unshocked curve, preventing shock cancellation.
    initial_index = Curve(base_nodes).forward(0, years[1])
    rows = []
    for p in positions.itertuples():
        if p.asset_or_liability == "equity":
            continue
        sign = 1 if p.asset_or_liability == "asset" else -1
        if p.amortization_type in ("cash", "carrying_value"):
            rows.append((scenario, p.position_id, p.product, p.asset_or_liability, 0,
                         dates[0].date().isoformat(), 0., p.principal, 0., p.principal,
                         0., p.principal, 1., sign*p.principal))
            continue
        nmd = p.amortization_type == "behavioral_equal_principal"
        n = max(1, round(p.behavioral_maturity_months*nmd_maturity_scale)) if nmd else p.remaining_maturity_months
        if n > 360:
            raise ValueError("Cash-flow maturity exceeds supported 30-year curve")
        opening = float(p.principal)
        rate = p.coupon_rate
        for m in range(1, n+1):
            start, end = years[m-1:m+1]
            if nmd:
                beta = p.deposit_beta if beta_override is None else beta_override
                rate = max(0., p.coupon_rate+beta*(curve.forward(start,end)-initial_index))
            elif p.fixed_or_floating == "floating":
                k = m-1
                if k >= p.next_reset_month and (k-p.next_reset_month) % p.repricing_frequency_months == 0:
                    reset_end = years[k+p.repricing_frequency_months]
                    rate = max(0., curve.forward(start,reset_end)+p.spread)
            interest = opening*rate*(end-start)
            repayment = (p.principal/n if p.amortization_type in ("equal_principal", "behavioral_equal_principal")
                         else (opening if m == n else 0.))
            if m == n:
                repayment = opening  # remove accumulated rounding drift at final payment
            closing = max(0., opening-repayment)
            df = float(curve.df(end))
            total = repayment+interest
            rows.append((scenario,p.position_id,p.product,p.asset_or_liability,m,
                         dates[m].date().isoformat(),end,repayment,interest,total,
                         closing,opening,df,sign*total*df))
            opening = closing
    return pd.DataFrame(rows, columns=["scenario","position_id","product","side","month",
                                      "payment_date","time_years","principal_cf","interest_cf","total_cf",
                                      "closing_principal","opening_principal","discount_factor","signed_pv"])


def run_ir(positions, nodes):
    from .source_validation import validate_sources
    verified = validate_sources()["curve"]
    pd.testing.assert_frame_equal(nodes, verified, check_dtype=False, atol=1e-14, rtol=0)
    all_flows = []
    nii_rows, eve_rows, contributions = [], [], []
    for scenario in IR_SCENARIOS:
        cf = cashflows(positions, Curve.from_verified_source(scenario), scenario)
        all_flows.append(cf)
        for product, part in cf.groupby("product", sort=False):
            sign = 1 if part.side.iloc[0] == "asset" else -1
            nii = sign*part.loc[part.month.between(1,12), "interest_cf"].sum()
            pv = part.signed_pv.sum()
            contributions.append(dict(scenario=scenario,product=product,nii=nii,signed_eve=pv))
        nii = sum(r["nii"] for r in contributions if r["scenario"] == scenario)
        a = cf.loc[cf.side.eq("asset"),"signed_pv"].sum()
        l = -cf.loc[cf.side.eq("liability"),"signed_pv"].sum()
        nii_rows.append(dict(scenario=scenario,nii=nii))
        eve_rows.append(dict(scenario=scenario,asset_pv=a,liability_pv=l,eve=a-l))
    nii = pd.DataFrame(nii_rows)
    nii["delta_nii"] = nii.nii-nii.nii.iloc[0]
    nii["delta_nii_pct"] = nii.delta_nii/nii.nii.iloc[0]
    eve = pd.DataFrame(eve_rows)
    eve["delta_eve"] = eve.eve-eve.eve.iloc[0]
    equity_residual_proxy = positions.loc[positions.asset_or_liability.eq("equity"),"principal"].sum()
    eve["delta_eve_equity_proxy_pct"] = eve.delta_eve/equity_residual_proxy
    products = pd.DataFrame(contributions)
    base = products.loc[products.scenario.eq("Base")].set_index("product")
    products["delta_nii"] = products.nii-products["product"].map(base.nii)
    products["delta_eve"] = products.signed_eve-products["product"].map(base.signed_eve)
    return pd.concat(all_flows,ignore_index=True), nii, eve, products

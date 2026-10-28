"""Daily internal liquidity proxy with explicit liquidity-stock accounting."""
import numpy as np
import pandas as pd
from .config import AS_OF, LIQUIDITY, LIQUIDITY_DAYS, INFLOW_CAP


def liquidity_stress(positions, base_cf):
    """No re-use of sold security flows, opening cash, or exhausted capacity.

    Remaining capacity is a stock. Available cash is an account. The liquidity
    gap is cash after real monetizations, even when negative. A negative gap is
    an unfunded need, with survival censored if no daily breach within 90 days.
    """
    today = pd.Timestamp(AS_OF)
    n = LIQUIDITY_DAYS
    retail = positions.loc[positions["product"].eq("Non-maturity retail deposits")]
    cash = positions.loc[positions["product"].eq("Cash and liquid assets"),"principal"].sum()
    gov = positions.loc[positions["product"].eq("Government securities")]
    pv_by_id = base_cf.groupby("position_id").signed_pv.sum()
    commitments = positions.undrawn_commitment.sum()
    all_rows, summaries = [], []
    for scenario, a in LIQUIDITY.items():
        d = pd.DataFrame({"day":np.arange(1,n+1)})
        d["scenario"] = scenario
        d["date"] = [(today+pd.Timedelta(days=int(i))).date().isoformat() for i in d.day]
        retail_runoff = (retail.principal*np.minimum(.95,retail.runoff_assumption*a["retail_multiplier"])).sum()
        weights = np.exp(-a["frontload"]*np.arange(n)); weights /= weights.sum()
        draw_weights = np.exp(-.09*np.arange(n)); draw_weights /= draw_weights.sum()
        d["retail_runoff"] = retail_runoff*weights
        d["commitment_drawdown"] = commitments*a["commitment_draw"]*draw_weights
        for col in ["term_nonrenewal","wholesale_loss","funding_interest","contractual_inflow"]:
            d[col] = 0.
        for p in positions.itertuples():
            part = base_cf.loc[base_cf.position_id.eq(p.position_id)]
            for cf in part.itertuples():
                day = (pd.Timestamp(cf.payment_date)-today).days
                if not 1 <= day <= n:
                    continue
                if p.product in ("Fixed-rate mortgages", "Floating-rate corporate loans", "Consumer loans"):
                    d.loc[day-1,"contractual_inflow"] += cf.total_cf*a["collection_rate"]
                elif p.product == "Term deposits":
                    d.loc[day-1,"term_nonrenewal"] += cf.principal_cf*a["term_nonrenewal"]
                    d.loc[day-1,"funding_interest"] += cf.interest_cf
                elif p.product == "Wholesale funding":
                    d.loc[day-1,"wholesale_loss"] += cf.principal_cf*a["wholesale_loss"]
                    d.loc[day-1,"funding_interest"] += cf.interest_cf
            # Rolled principal remains beyond the horizon; coupon expense continues.
            if p.product in ("Term deposits", "Wholesale funding"):
                loss = a["term_nonrenewal"] if p.product == "Term deposits" else a["wholesale_loss"]
                for m in range(p.remaining_maturity_months+1,4):
                    pay = today+pd.DateOffset(months=m)
                    prev = today+pd.DateOffset(months=m-1)
                    day = (pay-today).days
                    if day <= n:
                        d.loc[day-1,"funding_interest"] += p.principal*(1-loss)*p.coupon_rate*(pay-prev).days/365
        # Deposit interest uses the declining stress balance at original coupons.
        weighted_coupon = np.average(retail.coupon_rate,weights=retail.principal)
        d["retail_interest"] = (retail.principal.sum()-d.retail_runoff.cumsum()+d.retail_runoff)*weighted_coupon/365
        d["total_outflow"] = d[["retail_runoff","commitment_drawdown","term_nonrenewal",
                                  "wholesale_loss","funding_interest","retail_interest"]].sum(axis=1)
        d["recognized_inflow"] = np.minimum(d.contractual_inflow, INFLOW_CAP*d.total_outflow)
        d["excluded_inflow"] = d.contractual_inflow-d.recognized_inflow
        d["net_cash_flow"] = d.recognized_inflow-d.total_outflow
        capacity = sum(float(pv_by_id[p.position_id])*(1-min(.95,p.liquidity_haircut+a["extra_haircut"])) for p in gov.itertuples())
        d["asset_monetization"] = 0.
        d.loc[a["monetization_day"]-1,"asset_monetization"] = capacity
        d["cumulative_net_cash_flow"] = d.net_cash_flow.cumsum()
        d["cumulative_liquidity_gap"] = cash+d.cumulative_net_cash_flow+d.asset_monetization.cumsum()
        d["remaining_liquidity_buffer"] = d.cumulative_liquidity_gap.clip(lower=0)
        d["funding_need"] = (-d.cumulative_liquidity_gap).clip(lower=0)
        d["remaining_counterbalancing_capacity"] = capacity-d.asset_monetization.cumsum()
        d["total_resources_net_of_stress"] = d.cumulative_liquidity_gap+d.remaining_counterbalancing_capacity
        breached = d.loc[d.cumulative_liquidity_gap < -1e-8,"day"]
        breach = int(breached.iloc[0]) if len(breached) else None
        summaries.append(dict(scenario=scenario,opening_cash=cash,counterbalancing_capacity=capacity,
                              retail_runoff=retail_runoff,commitment_drawdown=commitments*a["commitment_draw"],
                              total_outflow=d.total_outflow.sum(),recognized_inflow=d.recognized_inflow.sum(),
                              excluded_inflow=d.excluded_inflow.sum(),monetization_day=a["monetization_day"],
                              first_breach_day=breach,survival_days=breach-1 if breach else n,
                              survival_censored=breach is None,peak_funding_need=d.funding_need.max(),
                              minimum_gap=d.cumulative_liquidity_gap.min(),terminal_gap=d.cumulative_liquidity_gap.iloc[-1],
                              remaining_liquidity_buffer=d.remaining_liquidity_buffer.iloc[-1]))
        all_rows.append(d)
    return pd.concat(all_rows,ignore_index=True),pd.DataFrame(summaries)

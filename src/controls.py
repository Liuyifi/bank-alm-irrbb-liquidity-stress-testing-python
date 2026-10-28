"""Executable dataset controls. A check failure stops artifact publication."""
import json
from urllib.parse import urlparse
import numpy as np
import pandas as pd
from .config import ROOT, AS_OF, IR_SCENARIOS, LIQUIDITY
from .market import Curve
from .public_data import sha


def check_record(name, passed, detail=""):
    return dict(check=name,status="PASS" if bool(passed) else "FAIL",detail=str(detail))


def public_checks(positions):
    lineage=json.loads((ROOT/"data/processed/public_data_lineage.json").read_text())
    t,h=lineage["treasury"],lineage["h8"]
    curve=pd.read_csv(ROOT/f"data/raw/treasury_yield_curve_{t['curve_date']}.csv")
    h8=pd.read_csv(ROOT/f"data/raw/federal_reserve_h8_{h['release_date']}.csv")
    cal=pd.read_csv(ROOT/"outputs/tables/h8_balance_sheet_calibration.csv")
    checks=[check_record("official_domains",urlparse(t["source_url"]).hostname=="home.treasury.gov" and
                         urlparse(h["source_url"]).hostname=="www.federalreserve.gov"),
            check_record("dates_not_after_run",all(x <= AS_OF for x in [t["observation_date"],t["publication_date"],h["release_date"],h["observation_date"]])),
            check_record("raw_files_nonempty",all((ROOT/f["path"]).stat().st_size > 0 for f in lineage["files"])),
            check_record("source_sha256",all(sha(ROOT/f["path"])==f["sha256"] for f in lineage["files"])),
            check_record("h8_required_fields",set(h8.field)=={"securities","loans","cash_assets","total_assets","deposits","borrowings","net_due_foreign","other_liabilities","total_liabilities","residual_equity_proxy"}),
            check_record("h8_nsa_population_units",h["seasonal_adjustment"]=="Not seasonally adjusted" and h8.value_usd_billions.gt(0).all()),
            check_record("h8_xml_html_crosscheck",h["xml_html_max_difference_usd_billions"]<=.051,h["xml_html_max_difference_usd_billions"]),
            check_record("calibration_ratios",all(abs(v-1)<1e-10 for v in cal.groupby("side").target_pct_total_assets.sum())),
            check_record("treasury_maturities_strictly_increasing",np.all(np.diff(curve.tenor_years)>0)),
            check_record("no_public_data_fallback",not lineage["fallback_used"])]
    a=positions.loc[positions.asset_or_liability.eq("asset"),"principal"].sum()
    diffs=[]
    for r in cal.itertuples():
        actual=positions.loc[positions["product"].isin(r.synthetic_products.split("; ")),"principal"].sum()/a
        diffs.append(abs(actual-r.target_pct_total_assets)*100)
    checks.append(check_record("synthetic_h8_calibration_tolerance",max(diffs)<=.01,
                               f"Maximum {max(diffs):.12f} percentage points; tolerance 0.01 pp"))
    x=h8.set_index("field").value_usd_billions
    checks.append(check_record("h8_balance_identity",abs(x.total_assets-x.total_liabilities-x.residual_equity_proxy)<.00001))
    result=dict(status="PASS" if all(c["status"]=="PASS" for c in checks) else "FAIL",checks=checks)
    (ROOT/"qa/public_source_checks.json").write_text(json.dumps(result,indent=2))
    return checks


def core_checks(p,cf,nii,eve,products,daily,liq,recon,nodes):
    a=p.loc[p.asset_or_liability.eq("asset"),"principal"].sum()
    l=p.loc[p.asset_or_liability.eq("liability"),"principal"].sum()
    e=p.loc[p.asset_or_liability.eq("equity"),"principal"].sum()
    checks=[check_record("assets_equal_liabilities_plus_equity",abs(a-l-e)<.01,f"Residual USD {a-l-e:.10f}"),
            check_record("position_id_unique",p.position_id.is_unique),
            check_record("nonnegative_principal",p.principal.ge(0).all()),
            check_record("reasonable_dates",((pd.to_datetime(p.origination_date)<AS_OF)&
                         (pd.to_datetime(p.contractual_maturity)>=AS_OF)&
                         (pd.to_datetime(p.next_repricing_date)>=AS_OF)&
                         (pd.to_datetime(p.next_repricing_date)<=pd.to_datetime(p.contractual_maturity))).all()),
            check_record("rate_beta_bounds",p.coupon_rate.between(0,.25).all() and p.deposit_beta.between(0,1).all() and p.runoff_assumption.between(0,1).all()),
            check_record("cashflow_keys_unique",not cf.duplicated(["scenario","position_id","month"]).any()),
            check_record("principal_not_overdrawn",cf.closing_principal.ge(-1e-7).all())]
    base=cf.loc[cf.scenario.eq("Base")]
    expected=p.loc[p.asset_or_liability.ne("equity")].set_index("position_id").principal
    actual=base.groupby("position_id").principal_cf.sum().reindex(expected.index)
    error=(actual-expected).abs().max()
    checks.append(check_record("base_principal_conservation",error<.00001,f"Max contract USD {error:.12f}; t0 carrying-value items are valuation entries"))
    fixed=cf.loc[cf["product"].isin(["Fixed-rate mortgages","Consumer loans","Government securities","Term deposits","Wholesale funding"])]
    fixed_nii=fixed.loc[fixed.month.between(1,12)].groupby(["scenario","product"]).interest_cf.sum().unstack(0)
    checks.append(check_record("fixed_coupon_nii_unchanged",(fixed_nii.max(axis=1)-fixed_nii.min(axis=1)).abs().max()<1e-7))
    corp=products.loc[products["product"].eq("Floating-rate corporate loans")].set_index("scenario")
    nmd=products.loc[products["product"].eq("Non-maturity retail deposits")].set_index("scenario")
    checks.append(check_record("nii_shock_direction",corp.loc["Parallel up 200 bps","delta_nii"]>0 and corp.loc["Parallel down 200 bps","delta_nii"]<0 and nmd.loc["Parallel up 200 bps","delta_nii"]<0))
    mortgage=products.loc[products["product"].eq("Fixed-rate mortgages")].set_index("scenario")
    checks.append(check_record("fixed_asset_eve_shock_direction",mortgage.loc["Parallel up 200 bps","delta_eve"]<0 and mortgage.loc["Parallel down 200 bps","delta_eve"]>0))
    checks.append(check_record("discount_factors_positive_monotone",all(np.all(np.diff(Curve(nodes,s).dfs)<=1e-10) and np.all(Curve(nodes,s).dfs>0) for s in IR_SCENARIOS)))
    checks.append(check_record("python_sql_reconciliation",recon.max_abs_difference.le(.01).all(),f"Max USD {recon.max_abs_difference.max():.12f}; tolerance USD 0.01"))
    checks.append(check_record("ir_scenario_completeness",list(nii.scenario)==IR_SCENARIOS and list(eve.scenario)==IR_SCENARIOS))
    checks.append(check_record("liquidity_scenario_completeness",set(liq.scenario)==set(LIQUIDITY) and daily.groupby("scenario").size().eq(90).all()))
    liq_error=0.
    for r in liq.itertuples():
        part=daily.loc[daily.scenario.eq(r.scenario)]
        delta=(r.opening_cash+part.net_cash_flow.cumsum()+part.asset_monetization.cumsum()-part.cumulative_liquidity_gap).abs().max()
        liq_error=max(liq_error,float(delta))
        liq_error=max(liq_error,abs(r.opening_cash+r.counterbalancing_capacity+r.recognized_inflow-r.total_outflow-r.terminal_gap))
    checks.append(check_record("liquidity_buffer_reconciliation",liq_error<.00001,f"Max USD {liq_error:.12f}"))
    checks.append(check_record("inflow_cap_and_nonnegative_capacity",daily.recognized_inflow.le(.75*daily.total_outflow+1e-8).all() and daily.remaining_counterbalancing_capacity.ge(-1e-8).all()))
    checks.append(check_record("product_contribution_reconciliation",all(abs(products.loc[products.scenario.eq(r.scenario),"delta_eve"].sum()-r.delta_eve)<.00001 for r in eve.itertuples())))
    checks += public_checks(p)
    result=dict(stage="engine",status="PASS" if all(c["status"]=="PASS" for c in checks) else "FAIL",checks=checks)
    (ROOT/"qa/core_checks.json").write_text(json.dumps(result,indent=2))
    if result["status"]!="PASS":
        raise AssertionError([c for c in checks if c["status"]!="PASS"])
    return result

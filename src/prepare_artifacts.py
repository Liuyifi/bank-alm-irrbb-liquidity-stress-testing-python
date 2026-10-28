"""One reviewed payload for the Word and Excel presentation layers."""
import json
import pandas as pd
import duckdb
from .config import ROOT,LIQUIDITY


def prepare():
    from .source_validation import validate_sources
    validate_sources()
    names=["balance_sheet","repricing_gap","nii_scenarios","eve_scenarios","product_contributions",
           "liquidity_scenarios","liquidity_daily","h8_balance_sheet_calibration","nmd_model_sensitivity"]
    payload={name:pd.read_csv(ROOT/f"outputs/tables/{name}.csv").astype(object).where(
        pd.notna(pd.read_csv(ROOT/f"outputs/tables/{name}.csv")),None).to_dict("records") for name in names}
    payload["metrics"]=json.loads((ROOT/"outputs/metrics/key_metrics.json").read_text())
    payload["lineage"]=json.loads((ROOT/"data/processed/public_data_lineage.json").read_text())
    payload["checks"]=json.loads((ROOT/"qa/core_checks.json").read_text())["checks"]
    payload["positions"]=pd.read_csv(ROOT/"data/processed/positions.csv").to_dict("records")
    with duckdb.connect() as db:
        payload['nmd_principal_wal_years']=db.execute("SELECT sum(principal_cf*time_years)/sum(principal_cf) FROM read_parquet(?) WHERE scenario='Base' AND product='Non-maturity retail deposits'",[str(ROOT/'data/processed/cashflows.parquet')]).fetchone()[0]
    payload["assumptions"]=[
        ["Valuation date","2026-10-23","Locked model date","Amounts USD; schedules ACT/365 monthly"],
        ["Portfolio scale",100000000,"Model assumption","Scale only; public category shares calibrate totals"],
        ["Random seed",20261023,"Model assumption","Lognormal contract weights with cent-exact totals"],
        ["Loan sub-product mix","40 : 25 : 10","Model assumption","Mortgages : corporate : consumer within observed H.8 loans"],
        ["Deposit sub-product mix","55 : 20","Model assumption","Non-maturity retail : term within observed H.8 deposits"],
        ["Securities mapping","Government proxy","Model assumption","H.8 broad securities mapped to synthetic fixed-rate government holdings; no trading VaR"],
        ["Other net assets","Carrying value","Model assumption","H.8 residual asset categories including allowance adjustment; not liquidated"],
        ["Other net liabilities","Carrying value","Model assumption","Other liabilities + net due foreign offices; excluded from stress outflows"],
        ["Cash yield",0,"Model assumption","Non-interest-bearing; cash at par at t0, counted once in liquidity"],
        ["NMD beta range","15% to 55%","Model assumption","Monthly coupon floor 0%; not estimated from H.8"],
        ["NMD behavior","24 to 60 months","Model assumption","Equal principal runoff for NII/EVE; independent stress runoff for liquidity"],
        ["Mortgages amortization","Equal principal","Model assumption","Remaining 36 to 240 months; no prepayment option"],
        ["Consumer amortization","Equal principal","Model assumption","Remaining 3 to 60 months; no default or prepayment"],
        ["Corporate repricing","1M or 3M","Model assumption","Treasury-implied forward proxy + 180 to 350 bps spread"],
        ["NII horizon","12 months","Model assumption","Existing book runoff; no replacement of matured assets or funding"],
        ["EVE discounting","Simplified discount-curve proxy","Model assumption","Treasury par yields feed a synthetic semiannual bootstrap; no coupon-instrument zero-curve calibration"],
        ["Parallel shocks","+/- 100 and 200 bps","Internal illustrative","Shock official par nodes then bootstrap; par floor 1 bp"],
        ["Steepener shock","0.01*(1-2*exp(-t/4))","Internal illustrative","Flattener is the negative; t in years"],
        ["Liquidity horizon","90 days","Internal illustrative","No default, reserve requirement, FX or extra margin call channels"],
        ["Recognized inflow cap",.75,"Internal illustrative","Daily inflow <= 75% of same-day outflow; excess discarded, no carry"],
        ["Undrawn commitments","40% corporate principal","Model assumption","New draws generate no inflows during the 90-day horizon"],
        ["Government eligibility",1.,"Model assumption","Fully unencumbered; base EVE market value monetized once"],
        ["Government base haircut",.02,"Model assumption","Scenario additional haircut is added to 2%"],
        ["Equity residual proxy","H.8 residual share","Normalization only","Stylized equity sensitivity; not regulatory capital or a BCBS outlier test"],
        ["Workbook refresh","Frozen engine outputs","Read-only management pack","Edit src/config.py then rerun engine, figures and artifact builders"],
    ]
    payload["liquidity_assumptions"]=[dict(scenario=k,**v) for k,v in LIQUIDITY.items()]
    curve=pd.read_csv(ROOT/"data/raw/treasury_curve.csv")
    (ROOT/"data/processed/curve_nodes.json").write_text(json.dumps(curve[["curve_date","tenor_years","par_rate"]].values.tolist()))
    h8=pd.read_csv(ROOT/f"data/raw/federal_reserve_h8_{payload['lineage']['h8']['release_date']}.csv")
    (ROOT/"data/processed/h8_nodes.json").write_text(json.dumps(h8[["field","value_usd_billions","observation_date","seasonal_adjustment"]].values.tolist()))
    (ROOT/"data/processed/artifact_payload.json").write_text(json.dumps(payload,indent=2,allow_nan=False))
    return payload


if __name__=="__main__": prepare()

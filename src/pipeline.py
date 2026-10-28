"""Offline reproducible analytics. Run public_data once to freeze official inputs."""
import json
import platform
import numpy as np
import pandas as pd
import duckdb
from .config import ROOT, AS_OF, SEED, LIQUIDITY, IR_SCENARIOS
from .public_data import acquire, calibrate
from .market import Curve
from .portfolio import generate,bucket_positions,repricing_gap
from .engine import run_ir,cashflows
from .liquidity import liquidity_stress
from .controls import core_checks


def run():
    from .source_validation import validate_sources
    verified = validate_sources()  # FIRST: fail before any analysis output write
    acquire()
    totals=calibrate()
    nodes=verified["curve"]
    p=bucket_positions(generate(Curve(nodes),calibrated_totals=totals))
    p.to_csv(ROOT/"data/processed/positions.csv",index=False)
    gap=repricing_gap(p)
    cf,nii,eve,products=run_ir(p,nodes)
    base_cf=cf.loc[cf.scenario.eq("Base")]
    daily,liq=liquidity_stress(p,base_cf)
    discount_inputs=[]
    for scenario in IR_SCENARIOS:
        curve=Curve(nodes,scenario)
        for month,time in cf.loc[cf.scenario.eq(scenario),["month","time_years"]].drop_duplicates().itertuples(index=False,name=None):
            discount_inputs.append(dict(scenario=scenario,month=month,time_years=time,discount_factor=float(curve.df(time))))
    discount_inputs=pd.DataFrame(discount_inputs)
    discount_inputs.to_csv(ROOT/"data/processed/scenario_discount_inputs.csv",index=False)
    assumptions=pd.DataFrame([dict(scenario=k,**v) for k,v in LIQUIDITY.items()])
    assumptions.to_csv(ROOT/"data/processed/liquidity_assumptions.csv",index=False)
    with duckdb.connect(str(ROOT/"data/processed/treasury_risk.duckdb")) as db:
        for name,frame in [("positions",p),("cashflows",cf),("scenario_discount_inputs",discount_inputs),("liquidity_assumptions",assumptions)]:
            db.register("input_frame",frame)
            db.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM input_frame")
        db.execute(f"COPY cashflows TO '{ROOT/'data/processed/cashflows.parquet'}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        queries={path.stem:db.execute(path.read_text()).df() for path in sorted((ROOT/"sql").glob("*.sql"))}
    b=queries["balance_sheet"]
    py_balance=p.groupby(["asset_or_liability","product"]).principal.sum().sort_index()
    sq_balance=b.set_index(["side","product"]).principal.sort_index()
    sq_gap=queries["repricing_gap"].set_index("bucket_order")
    sq_ir=queries["scenario_reconciliation"].set_index("scenario")
    sq_l=queries["liquidity_aggregation"].set_index(["scenario","day"]).sort_index()
    py_l=daily.set_index(["scenario","day"]).sort_index()
    liquidity_columns=[c for c in sq_l.columns if c in py_l.columns]
    errors={"balance_sheet":(py_balance-sq_balance).abs().max(),
            "repricing_rsa_rsl":(gap.set_index("bucket_order")[["rsa","rsl","periodic_gap","cumulative_gap"]]-sq_gap[["rsa","rsl","periodic_gap","cumulative_gap"]]).abs().max().max(),
            "scenario_nii":(nii.set_index("scenario").nii-sq_ir.nii).abs().max(),
            "scenario_eve":(eve.set_index("scenario").eve-sq_ir.eve).abs().max(),
            "liquidity_daily":(py_l[liquidity_columns]-sq_l[liquidity_columns]).abs().max().max()}
    recon=pd.DataFrame([dict(control=k,max_abs_difference=float(v),tolerance_usd=.01) for k,v in errors.items()])
    specs={
        "balance_sheet":("position principal", "portfolio.generate / position ledger", "sql/balance_sheet.sql", "INDEPENDENT_RECOMPUTATION"),
        "repricing_rsa_rsl":("position dates and principal", "portfolio.repricing_gap", "sql/repricing_gap.sql", "INDEPENDENT_RECOMPUTATION"),
        "scenario_nii":("projected contractual cash flow", "engine.cashflows / run_ir", "sql/scenario_reconciliation.sql", "PARTIAL_RECOMPUTATION"),
        "scenario_eve":("projected cash flow plus scenario discount inputs", "engine.cashflows / market.Curve", "sql/scenario_reconciliation.sql", "PARTIAL_RECOMPUTATION"),
        "liquidity_daily":("position, scenario assumption, shared Base cash flow and discount inputs", "liquidity.liquidity_stress", "sql/liquidity_aggregation.sql", "PARTIAL_RECOMPUTATION")}
    classification=pd.DataFrame([dict(check_name=k,input_grain=v[0],python_source=v[1],sql_source=v[2],
        classification=v[3],difference=float(errors[k]),tolerance=.01,status="PASS" if errors[k]<=.01 else "FAIL") for k,v in specs.items()])
    classification.to_csv(ROOT/"outputs/metrics/sql_reconciliation_classification.csv",index=False)
    if not classification.status.eq("PASS").all():
        raise AssertionError("Python/SQL reconciliation failed")
    for name,frame in {"balance_sheet":b,"repricing_gap":gap,"nii_scenarios":nii,"eve_scenarios":eve,
                       "product_contributions":products,"liquidity_daily":daily,"liquidity_scenarios":liq,
                       "python_sql_reconciliation":recon}.items():
        frame.to_csv(ROOT/f"outputs/tables/{name}.csv",index=False)
    for name,frame in queries.items():
        frame.to_csv(ROOT/f"outputs/tables/sql_{name}.csv",index=False)
    # Two meaningful model-risk dimensions, each revalued against its own base.
    sensitivity=[]
    for name,scale,beta in [("Default",1.,None),("NMD maturity 50%",.5,None),("NMD maturity 150%",1.5,None),
                            ("NMD beta 15%",1.,.15),("NMD beta 55%",1.,.55)]:
        values=[]
        for scenario in ["Base","Parallel up 200 bps","Parallel down 200 bps"]:
            flows=cashflows(p,Curve.from_verified_source(scenario),scenario,scale,beta)
            sign=np.where(flows.side.eq("asset"),1,-1)
            net_nii=(flows.loc[flows.month.between(1,12),"interest_cf"]*sign[flows.month.between(1,12)]).sum()
            values.append((scenario,net_nii,flows.signed_pv.sum()))
        for scenario,net_nii,pv in values:
            sensitivity.append(dict(variant=name,scenario=scenario,nii=net_nii,eve=pv,
                                    delta_nii=net_nii-values[0][1],delta_eve=pv-values[0][2]))
    pd.DataFrame(sensitivity).to_csv(ROOT/"outputs/tables/nmd_model_sensitivity.csv",index=False)
    checks=core_checks(p,cf,nii,eve,products,daily,liq,recon,nodes)
    worst_n=nii.loc[nii.delta_nii.idxmin()]; worst_e=eve.loc[eve.delta_eve.idxmin()]
    metrics=dict(as_of=AS_OF,seed=SEED,data_type="Synthetic contract/group records calibrated to observed official H.8 aggregate shares",
                 positions=len(p),total_assets=float(p.loc[p.asset_or_liability.eq("asset"),"principal"].sum()),
                 equity_residual_proxy=float(p.loc[p.asset_or_liability.eq("equity"),"principal"].sum()),
                 base_nii=float(nii.nii.iloc[0]),worst_delta_nii=float(worst_n.delta_nii),worst_nii_scenario=worst_n.scenario,
                 worst_delta_nii_pct=float(worst_n.delta_nii_pct),base_eve=float(eve.eve.iloc[0]),
                 worst_delta_eve=float(worst_e.delta_eve),worst_eve_scenario=worst_e.scenario,
                 worst_delta_eve_equity_proxy_pct=float(worst_e.delta_eve_equity_proxy_pct),
                 liquidity_scenarios=liq.astype(object).where(pd.notna(liq),None).to_dict("records"),
                 python_sql_max_difference=float(recon.max_abs_difference.max()),
                 core_checks_passed=len(checks["checks"]),cashflow_rows=len(cf))
    (ROOT/"outputs/metrics/key_metrics.json").write_text(json.dumps(metrics,indent=2,allow_nan=False))
    (ROOT/"outputs/metrics/environment.json").write_text(json.dumps(dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,duckdb=duckdb.__version__),indent=2))
    print(json.dumps({k:v for k,v in metrics.items() if k!="liquidity_scenarios"},indent=2))
    return metrics


if __name__=="__main__":
    run()

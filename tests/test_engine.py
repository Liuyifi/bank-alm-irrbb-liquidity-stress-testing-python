import json
import duckdb
import numpy as np
import pandas as pd
import pytest
from src.config import ROOT, AS_OF, IR_SCENARIOS, LIQUIDITY
from src.market import Curve,shock
from src.engine import cashflows
from src.portfolio import bucket_positions,generate
from src.public_data import acquire


@pytest.fixture(scope="module")
def nodes():
    return pd.read_csv(ROOT/"data/raw/treasury_curve.csv")


@pytest.fixture(scope="module")
def positions():
    return pd.read_csv(ROOT/"data/processed/positions.csv")


@pytest.fixture(scope="module")
def base_cf():
    with duckdb.connect(str(ROOT/"data/processed/treasury_risk.duckdb"),read_only=True) as db:
        return db.sql("SELECT * FROM cashflows WHERE scenario='Base'").df()


def test_source_integrity():
    assert acquire()["fallback_used"] is False
    assert json.loads((ROOT/"qa/public_source_checks.json").read_text())["status"]=="PASS"


def test_seed_reproducibility(nodes,positions):
    totals=json.loads((ROOT/"data/processed/calibrated_product_totals.json").read_text())
    again=bucket_positions(generate(Curve(nodes),calibrated_totals=totals))
    pd.testing.assert_frame_equal(again,positions,check_dtype=False,atol=1e-10,rtol=1e-12)


@pytest.mark.parametrize("scenario",IR_SCENARIOS)
def test_bootstrap_reprices_synthetic_par_bonds(nodes,scenario):
    c=Curve(nodes,scenario)
    for tenor in [.5,1.,2.,5.,10.,20.,30.]:
        par=np.interp(tenor,c.node_t,c.par)
        payments=np.arange(.5,tenor+.01,.5)
        value=par*.5*c.df(payments).sum()+c.df(tenor)
        assert abs(value-1)<1e-10


@pytest.mark.parametrize("scenario",IR_SCENARIOS)
def test_discount_curve_positive_decreasing(nodes,scenario):
    values=Curve(nodes,scenario).df(np.linspace(0,30,2001))
    assert values[0]==1
    assert np.all(values>0) and np.all(np.diff(values)<=1e-10)


def test_internal_twist_definition():
    assert shock([.1,30],"Steepener")[0]<0<shock([.1,30],"Steepener")[1]
    np.testing.assert_allclose(shock([.1,30],"Steepener"),-shock([.1,30],"Flattener"))
    with pytest.raises(ValueError): shock([1],"unapproved scenario")


def test_gap_bucket_boundaries(positions):
    p=positions.iloc[[0]*12].copy().reset_index(drop=True)
    today=pd.Timestamp(AS_OF)
    dates=[]; expected=[]
    for i,m in enumerate([1,3,6,12,24,60]):
        dates.extend([(today+pd.DateOffset(months=m)).date().isoformat(),
                      (today+pd.DateOffset(months=m)+pd.Timedelta(days=1)).date().isoformat()])
        expected.extend([i,i+1])
    p["next_repricing_date"]=dates
    assert list(bucket_positions(p).bucket_order)==expected


def test_principal_conserved_by_contract(positions,base_cf):
    target=positions.loc[positions.asset_or_liability.ne("equity")].set_index("position_id").principal
    got=base_cf.groupby("position_id").principal_cf.sum().reindex(target.index)
    np.testing.assert_allclose(got,target,atol=.00001,rtol=0)
    final=base_cf.sort_values("month").groupby("position_id").tail(1)
    # t0 entries record carrying values, not contractual repayments.
    assert final.loc[final.month.gt(0),"closing_principal"].abs().max()<1e-7


def test_float_reset_is_not_early(nodes,positions):
    p=positions.loc[positions["product"].eq("Floating-rate corporate loans")].iloc[[0]].copy()
    p["next_reset_month"]=3; p["repricing_frequency_months"]=3
    base=cashflows(p,Curve.from_verified_source(),"Base")
    up=cashflows(p,Curve.from_verified_source("Parallel up 200 bps"),"Parallel up 200 bps")
    np.testing.assert_allclose(base.interest_cf.iloc[:3],up.interest_cf.iloc[:3])
    assert up.interest_cf.iloc[3]>base.interest_cf.iloc[3]


def test_contractual_maturity_stops_interest(base_cf,positions):
    for p in positions.loc[positions["product"].eq("Term deposits")].itertuples():
        flows=base_cf.loc[base_cf.position_id.eq(p.position_id)]
        assert flows.month.max()==p.remaining_maturity_months
        assert flows.principal_cf.iloc[-1]==pytest.approx(p.principal)


def test_equity_excluded_from_eve_cashflows(base_cf,positions):
    eq=positions.loc[positions.asset_or_liability.eq("equity"),"position_id"]
    assert not base_cf.position_id.isin(eq).any()


def test_deposit_beta_changes_interest_cost(nodes,positions):
    p=positions.loc[positions["product"].eq("Non-maturity retail deposits")].iloc[:2]
    c=Curve.from_verified_source("Parallel up 200 bps")
    low=cashflows(p,c,"Parallel up 200 bps",beta_override=.15)
    high=cashflows(p,c,"Parallel up 200 bps",beta_override=.55)
    assert high.loc[high.month.le(12),"interest_cf"].sum()>low.loc[low.month.le(12),"interest_cf"].sum()


def test_daily_liquidity_stock_identity():
    df=pd.read_csv(ROOT/"outputs/tables/liquidity_daily.csv")
    summary=pd.read_csv(ROOT/"outputs/tables/liquidity_scenarios.csv")
    for s in summary.itertuples():
        part=df.loc[df.scenario.eq(s.scenario)]
        np.testing.assert_allclose(part.cumulative_liquidity_gap,
                                   s.opening_cash+part.net_cash_flow.cumsum()+part.asset_monetization.cumsum(),atol=1e-7)
        assert part.asset_monetization.gt(0).sum()==1
        assert part.asset_monetization.sum()==pytest.approx(s.counterbalancing_capacity)
        assert np.all(part.recognized_inflow <= .75*part.total_outflow+1e-8)
        assert part.loc[part.day.lt(s.monetization_day),"asset_monetization"].eq(0).all()
        breach=part.loc[part.cumulative_liquidity_gap.lt(0),"day"]
        if len(breach): assert s.survival_days==breach.iloc[0]-1
        else: assert s.survival_censored and s.survival_days==90


def test_sold_securities_not_reused_as_inflows(base_cf):
    daily=pd.read_csv(ROOT/"outputs/tables/liquidity_daily.csv")
    today=pd.Timestamp(AS_OF)
    eligible=base_cf.loc[base_cf["product"].isin(["Fixed-rate mortgages","Floating-rate corporate loans","Consumer loans"])].copy()
    days=(pd.to_datetime(eligible.payment_date)-today).dt.days
    eligible=eligible.loc[days.between(1,90)]
    for name,a in LIQUIDITY.items():
        assert daily.loc[daily.scenario.eq(name),"contractual_inflow"].sum()==pytest.approx(eligible.total_cf.sum()*a["collection_rate"])


def test_all_engine_controls_pass():
    result=json.loads((ROOT/"qa/core_checks.json").read_text())
    assert result["status"]=="PASS"
    assert all(c["status"]=="PASS" for c in result["checks"])

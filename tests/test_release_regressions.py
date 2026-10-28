"""Small independently expected financial checks and SQL dependency boundaries."""
import json
import duckdb
import numpy as np
import pandas as pd
import pytest
from src.config import ROOT
from src.engine import cashflows
from src.market import Curve
from src.liquidity import liquidity_stress


@pytest.fixture
def one():
    p=pd.read_csv(ROOT/'data/processed/positions.csv').iloc[[0]].copy()
    p['principal']=1200.;p['coupon_rate']=.12;p['amortization_type']='bullet'
    p['remaining_maturity_months']=2;p['fixed_or_floating']='fixed'
    return p


@pytest.fixture
def curve():
    return Curve.from_verified_source()


def test_hand_calculated_asset_liability_and_maturity(one,curve):
    # 23 Oct -> 23 Nov = 31 days; 23 Nov -> 23 Dec = 30 days.
    for side,sign in [('asset',1),('liability',-1)]:
        one['asset_or_liability']=side
        f=cashflows(one,curve)
        np.testing.assert_allclose(f.interest_cf,[1200*.12*31/365,1200*.12*30/365],rtol=0,atol=1e-12)
        assert f.principal_cf.tolist()==[0,1200]
        assert f.month.tolist()==[1,2]
        np.testing.assert_allclose(f.signed_pv,sign*f.total_cf*f.discount_factor)


def test_zero_deposit_coupon_floor(one,curve):
    one['fixed_or_floating']='floating';one['repricing_frequency_months']=1
    one['amortization_type']='behavioral_equal_principal';one['behavioral_maturity_months']=2
    one['coupon_rate']=0.;one['deposit_beta']=1.
    down=Curve.from_verified_source('Parallel down 200 bps')
    f=cashflows(one,down,'Parallel down 200 bps')
    assert f.interest_cf.eq(0).all()
    assert f.principal_cf.tolist()==[600,600]


@pytest.mark.parametrize('case',['duplicate','negative','frequency','missing','nan'])
def test_bad_position_rejected(one,curve,case):
    if case=='duplicate': one=pd.concat([one,one])
    elif case=='negative': one['principal']=-1
    elif case=='frequency': one['fixed_or_floating']='floating';one['repricing_frequency_months']=0
    elif case=='missing': one=one.drop(columns='principal')
    else: one['principal']=float('nan')
    with pytest.raises(ValueError): cashflows(one,curve)


def test_sql_does_not_depend_on_python_present_values_or_daily_outputs():
    with duckdb.connect(str(ROOT/'data/processed/treasury_risk.duckdb'),read_only=True) as source:
        p=source.sql('SELECT * FROM positions').df()
        c=source.sql('SELECT * FROM cashflows').df()
        d=source.sql('SELECT * FROM scenario_discount_inputs').df()
        a=source.sql('SELECT * FROM liquidity_assumptions').df()
    c['signed_pv']=0.;c['discount_factor']=0.
    with duckdb.connect() as db:
        for name,frame in [('positions',p),('cashflows',c),('scenario_discount_inputs',d),('liquidity_assumptions',a)]: db.register(name,frame)
        eve=db.execute((ROOT/'sql/scenario_reconciliation.sql').read_text()).df().set_index('scenario')
        liq=db.execute((ROOT/'sql/liquidity_aggregation.sql').read_text()).df()
    assert eve.loc['Base','eve']==pytest.approx(12927232.70,abs=.01)
    combined=liq.loc[liq.scenario.eq('Combined')]
    assert combined.iloc[-1].remaining_liquidity_buffer==pytest.approx(1017055.78,abs=.01)
    assert combined.asset_monetization.gt(0).sum()==1
    assert combined.recognized_inflow.le(.75*combined.total_outflow+1e-8).all()


def test_sql_classifications_are_explicit():
    f=pd.read_csv(ROOT/'outputs/metrics/sql_reconciliation_classification.csv')
    assert f.classification.value_counts().to_dict()=={'PARTIAL_RECOMPUTATION':3,'INDEPENDENT_RECOMPUTATION':2}
    assert f.difference.le(f.tolerance).all() and f.status.eq('PASS').all()

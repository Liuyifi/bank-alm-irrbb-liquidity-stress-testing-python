"""Deterministic contract/group generation with cent-exact product controls."""
import numpy as np
import pandas as pd
from .config import AS_OF, PRODUCTS, SEED, BUCKETS


def generate(curve, seed=SEED, calibrated_totals=None):
    rng = np.random.default_rng(seed)
    today = pd.Timestamp(AS_OF)
    rows = []
    for code, (product, (count, low, high, cmin, cmax, amort)) in enumerate(PRODUCTS.items(), 1):
        if calibrated_totals is None:
            raise ValueError("H.8-calibrated product totals are required")
        total = calibrated_totals[product]
        weights = rng.lognormal(0, .35, count)
        cents = np.round(weights/weights.sum()*total*100).astype(np.int64)
        cents[-1] += round(total*100)-int(cents.sum())
        for i, amount in enumerate(cents):
            asset = code <= 5 or product == "Other non-rate-sensitive assets"
            side = "asset" if asset else ("equity" if code == 9 else "liability")
            n = int(rng.integers(low, high+1)) if high else 0
            floating = code in (2, 6)
            freq = int(rng.choice([1, 3])) if code == 2 else (1 if code == 6 else 0)
            first_reset = int(rng.integers(1, freq+1)) if code == 2 else 0
            spread = float(rng.uniform(.018, .035)) if code == 2 else 0.
            coupon = curve.forward(0, freq/12)+spread if code == 2 else float(rng.uniform(cmin, cmax))
            maturity = today+pd.DateOffset(months=n) if n else today
            if code == 6:
                maturity = today+pd.Timedelta(days=1)  # Legal demand maturity, separate behavior.
            next_reset = (today+pd.DateOffset(months=first_reset) if floating else maturity)
            rows.append(dict(
                position_id=f"P{code:02d}-{i+1:04d}", product=product, asset_or_liability=side,
                principal=amount/100, coupon_rate=coupon,
                fixed_or_floating="floating" if floating else ("non_rate" if amort in ("cash","equity","carrying_value") else "fixed"),
                origination_date=(today-pd.DateOffset(months=int(rng.integers(1,61)))).date().isoformat(),
                contractual_maturity=maturity.date().isoformat(),
                next_repricing_date=next_reset.date().isoformat(),
                repricing_frequency=f"{freq}M" if floating else "none",
                repricing_frequency_months=freq, next_reset_month=first_reset,
                amortization_type=amort,
                reference_rate="USD Treasury implied forward proxy" if floating else "none",
                spread=spread, behavioral_maturity_months=n if code == 6 else 0,
                behavioral_maturity=(today+pd.DateOffset(months=n)).date().isoformat() if n else today.date().isoformat(),
                remaining_maturity_months=n,
                deposit_beta=float(rng.uniform(.15,.55)) if code == 6 else 0.,
                runoff_assumption=float(rng.uniform(.075,.125)) if code == 6 else 0.,
                liquidity_haircut=.02 if code == 4 else 0.,
                undrawn_commitment=amount/100*.4 if code == 2 else 0.,
                currency="USD", record_grain="contract" if code in (1,2,3,7) else "position group"))
    return pd.DataFrame(rows)


def bucket_positions(positions):
    """Stock allocated at next reset or final fixed maturity; cash/equity non-rate."""
    result = positions.copy()
    today = pd.Timestamp(AS_OF)
    cutoffs = [today+pd.DateOffset(months=m) for m in [1,3,6,12,24,60]]
    orders = []
    for p in result.itertuples():
        if p.fixed_or_floating == "non_rate":
            orders.append(7)
        else:
            date = pd.Timestamp(p.next_repricing_date)
            orders.append(next((i for i,c in enumerate(cutoffs) if date <= c), 6))
    result["bucket_order"] = orders
    result["bucket"] = [BUCKETS[i] for i in orders]
    return result


def repricing_gap(positions):
    records = []
    total_assets = positions.loc[positions.asset_or_liability.eq("asset"), "principal"].sum()
    for i, name in enumerate(BUCKETS):
        part = positions.loc[positions.bucket_order.eq(i)]
        a = part.loc[part.asset_or_liability.eq("asset"), "principal"].sum()
        l = part.loc[part.asset_or_liability.eq("liability"), "principal"].sum()
        eq = part.loc[part.asset_or_liability.eq("equity"), "principal"].sum()
        records.append(dict(bucket_order=i, bucket=name, asset_principal=a, liability_principal=l,
                            equity_principal=eq, rsa=a if i<7 else 0., rsl=l if i<7 else 0.))
    out = pd.DataFrame(records)
    out["periodic_gap"] = out.rsa-out.rsl
    out["cumulative_gap"] = out.periodic_gap.cumsum()
    out["gap_pct_total_assets"] = out.periodic_gap/total_assets
    return out

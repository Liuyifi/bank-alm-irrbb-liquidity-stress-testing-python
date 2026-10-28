# Methodology and model boundaries

The locked valuation date is 23 October 2026. All amounts are USD. This is a synthetic banking-book study calibrated to an official US industry aggregate, not a real-bank model or a trading-book VaR study.

## Public calibration

`src.public_data` downloads Treasury's official annual XML and the Federal Reserve's official H.8 XML archive, plus its current HTML release for a release-date and rounded-value cross-check. It selects the latest complete Treasury observation no later than the valuation date. H.8 uses the latest available release at acquisition, all commercial banks, weekly Wednesday observations, not seasonally adjusted, level series. The selected XML units are USD millions; stored H.8 extracts use USD billions. Original raw files and SHA256 are frozen. The default rerun verifies hashes and does not download or silently update the vintage.

H.8 cash, securities, gross loans, deposits, borrowings, other liabilities, net due foreign and residual balances anchor USD 100m total assets. Cash + securities + loans + net other assets equals total assets. Net other assets contain all remaining categories, including the subtraction of loan-loss allowances. Funding equals deposits + borrowings + other liabilities + net due foreign + residual. This preserves the public aggregate rather than discarding or reallocating its non-lending components.

The public securities total becomes synthetic government securities, and loan/deposit sub-product mixes are internal assumptions (40:25:10 mortgages/corporate/consumer and 55:20 NMD/term). These are simplifications, not observed H.8 subcategory matches. Other net asset/liability categories are held at book value, have no interest sensitivity or liquidity capacity, and do not reconstruct trading positions. The H.8 residual is only a stylized equity proxy. It is not regulatory capital, and Delta EVE divided by this proxy is not a regulatory capital ratio or supervisory outlier test.

## Positions and dates

Seed 20261023 draws lognormal weights with sigma 0.35, normalizes within each calibrated product total, then rounds to cents with the final record absorbing only a sub-dollar rounding residual. There are 938 contract/group records. Origination dates precede valuation, while principal is the outstanding balance at valuation, not original principal. Schedules are monthly anniversaries of valuation with ACT/365 accrual, including the final maturity date. No business-day calendar is applied.

Mortgages and consumer loans use equal principal, rather than annuity payments. Corporate loans, government securities, term deposits and wholesale funding use bullet principal. Cash and non-rate-sensitive other items are time-zero valuation entries for EVE, not future liquidity inflows. Equity is excluded from EVE cash flows and used only as a denominator. Contract principal is conserved through amortization and final bullet repayment; valuation-only entries conserve carrying values separately at time zero.

## Repricing gap

Assign entire principal to next reset for floaters and final contractual maturity for fixed-rate positions. The exact anniversary boundaries are 1, 3, 6, 12, 24 and 60 months. NMDs reprice monthly and occupy the first bucket, independently of their behavioral principal maturity. Cash, equity and other non-rate-sensitive categories contribute zero RSA/RSL. This stock gap does not allocate future amortization installments and is not an estimate of EVE duration.

## Discounting and projections

Treasury par quotes are annual decimals. Apply the scenario shock to original observed par nodes, floor the resulting par rate at 1 bp, then bootstrap. Below six months, use the short simple annual-rate approximation `D(t)=1/(1+y(t)t)`. From six months to 30 years, interpolate par rates linearly at semiannual synthetic coupon dates and solve `D(t)=(1-c/2*sum(D(previous coupon dates)))/(1+c/2)`. Discount factors use piecewise log-linear interpolation, with D(0)=1. No model cash flow extends beyond 30 years; the API clamps outside that supported curve range and schedules reject maturities over 360 months.

Projection rates are simple forwards `F(a,b)=(D(a)/D(b)-1)/(b-a)`. Corporate current coupons remain in force until the exact next reset month. At each reset the next contractual 1M/3M forward plus fixed spread determines the coupon, floored at zero. Before first reset, scenario coupons are identical. The Treasury-implied index is a modeling proxy and is not described as SOFR.

NMDs have contractual demand maturity but equal-principal behavioral runoff over 24–60 months. Monthly coupons are `max(0, original_coupon + beta*(scenario_1M_forward - initial_base_1M_index))`. The initial index is fixed from Base, not recomputed under the shock. This allows curve-implied Base repricing and avoids cancellation of the instantaneous shock. Beta affects coupon pass-through, while behavioral maturity affects principal timing. Principal weighted average life under the selected schedules is approximately 1.765 years; it is not an empirically estimated deposit duration.

## Internal illustrative scenarios

Base, parallel +/-100 bps and +/-200 bps, steepener and flattener are internal deterministic scenarios. With maturity `t` in years, the steepener par-node shock is `0.01*(1-2*exp(-t/4))`, with the flattener its negative. These scenarios are not a BCBS standardized scenario implementation. No regulatory approval or outlier threshold is claimed.

NII sums asset interest less liability interest over months 1–12. It follows existing-book runoff and includes maturity, amortization, reset mismatch and NMD behavior. There is no replacement business or reinvestment. EVE sums full-life signed discounted principal and interest, excluding equity, with scenario-dependent floating coupons. It includes contractual margins. Delta values subtract Base. Product contributions reconcile to aggregates. The NMD sensitivity table revalues every variant against that variant's own Base.

## Daily internal liquidity survival proxy

The horizon is 90 calendar days. Opening cash enters once. All synthetic government securities are assumed unencumbered and fully monetized once at Base EVE market value less a 2% base haircut plus the scenario addition. Monetization occurs on day 2, 5 or 7, so capacity is unavailable as cash before that date. All sold securities' future coupons and maturities are excluded from contractual inflows; no government payment occurs before these assumed sale dates. Other assets contribute no capacity.

NMD stress runoff uses each record's baseline 7.5–12.5% assumption multiplied by 2.0, 1.2 or 4.0, capped at 95% per record. It is allocated with normalized exponentially declining daily weights. This is a separate liquidity scenario, not a simultaneous replay of the NII/EVE behavioral runoff. Term nonrenewal and wholesale losses apply to principal at contractual maturity. The renewed portion remains beyond 90 days and continues paying its original interest. Retail interest uses daily declining aggregate balances and the initial principal-weighted average coupon. No replacement rate shock is imposed on liquidity interest costs.

Undrawn commitments equal 40% of corporate principal. Scenario draws are 25%, 40% and 65%, front-loaded at exponential rate 0.09 per day. New draws generate no contractual inflows within the window. Loan contractual inflows are scaled by collection assumptions of 95%, 85% or 80%. Recognized daily inflows are `min(collection-adjusted contractual inflow, 75% of same-day total outflows)`. Excess is discarded, not deferred; securities sale proceeds are not capped. This is an internal conservative timing rule, not a formal LCR definition.

`cash_gap(day) = opening_cash + cumulative(recognized_inflow-outflow) + cumulative(realized_sales)`.
`remaining_capacity = initial_haircut_capacity - cumulative(realized_sales)`.
`peak_funding_need = max(0, -min(cash_gap))`.
Survival is the last fully funded day before the first negative daily gap. No breach is reported as at least 90 days, right-censored at the test horizon, with no extrapolation. Ending buffer is max(terminal gap,0). A pre-sale cash deficit would be a breach even with positive remaining capacity.

## Controls and limits

Four SQL files implement five reconciliation controls at USD 0.01 tolerance. Balance-sheet totals and repricing buckets are `INDEPENDENT_RECOMPUTATION`. Scenario NII and EVE are `PARTIAL_RECOMPUTATION` because SQL shares Python-projected cash flows and scenario discount inputs. Daily liquidity is `PARTIAL_RECOMPUTATION`: SQL rebuilds all stress flows, caps, monetization and cumulative balances from positions, assumptions and shared Base contractual cash flows. The exact classifications and differences are machine-readable in `outputs/metrics/sql_reconciliation_classification.csv`. Dataset controls and pytest cover identities, bounds, keys, conservation, curve and shock behavior, scenario completeness, product bridges, liquidity reconciliation and official-source lineage. Artifact checks verify Word/Excel structure, saved formula caches, no formula errors, report metrics, source hashes, nine rendered pages and valid README links.

Excluded: prepayment, default, annuity mortgage payments, embedded options, basis/credit-spread risk, hedges, FX, intraday settlement, insurance/concentration calibration, encumbrance, central-bank eligibility, reserve requirements, margin calls and other-liability cash demands. No LCR, NSFR, regulatory Tier 1 or production-readiness claim is made. Fixed cash yield, carrying-value categories, internal caps and portfolio subcategory simplifications materially affect results.

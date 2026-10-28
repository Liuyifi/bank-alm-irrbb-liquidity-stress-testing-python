-- Stress mechanics rebuilt from positions, shared BASE contractual cash flows and
-- explicit scenario assumptions. No Python daily flows, sales or summary inputs.
-- PARTIAL_RECOMPUTATION: contractual cash flows and discount inputs are Python.
WITH grid AS (
 SELECT a.*, r.range::INTEGER AS day,
        exp(-frontload*(r.range-1)) AS rw, exp(-.09*(r.range-1)) AS dw
 FROM liquidity_assumptions a CROSS JOIN range(1,91) r
), weighted AS (
 SELECT *, rw/sum(rw) OVER(PARTITION BY scenario) AS retail_weight,
           dw/sum(dw) OVER(PARTITION BY scenario) AS draw_weight FROM grid
), stocks AS (
 SELECT a.scenario,
  (SELECT sum(principal) FROM positions WHERE product='Cash and liquid assets') AS opening_cash,
  (SELECT sum(undrawn_commitment) FROM positions) * a.commitment_draw AS commitments,
  sum(p.principal) AS retail_stock,
  sum(p.principal*least(.95,p.runoff_assumption*a.retail_multiplier)) AS retail_total,
  sum(p.principal*p.coupon_rate)/sum(p.principal) AS retail_coupon
 FROM liquidity_assumptions a CROSS JOIN positions p
 WHERE p.product='Non-maturity retail deposits' GROUP BY ALL
), base AS (
 SELECT c.*, date_diff('day', DATE '2026-10-23', CAST(payment_date AS DATE)) AS day
 FROM cashflows c WHERE scenario='Base'
), events AS (
 SELECT a.scenario, b.day,
  sum(CASE WHEN b.product IN ('Fixed-rate mortgages','Floating-rate corporate loans','Consumer loans')
      THEN b.total_cf*a.collection_rate ELSE 0 END) AS contractual_inflow,
  sum(CASE WHEN b.product='Term deposits' THEN b.principal_cf*a.term_nonrenewal ELSE 0 END) AS term_nonrenewal,
  sum(CASE WHEN b.product='Wholesale funding' THEN b.principal_cf*a.wholesale_loss ELSE 0 END) AS wholesale_loss,
  sum(CASE WHEN b.product IN ('Term deposits','Wholesale funding') THEN b.interest_cf ELSE 0 END) AS original_interest
 FROM liquidity_assumptions a CROSS JOIN base b WHERE day BETWEEN 1 AND 90 GROUP BY ALL
), rolled AS (
 SELECT a.scenario,
  date_diff('day', DATE '2026-10-23', DATE '2026-10-23'+CAST(m.range AS INTEGER)*INTERVAL 1 MONTH) AS day,
  sum(p.principal*(1-CASE WHEN p.product='Term deposits' THEN a.term_nonrenewal ELSE a.wholesale_loss END)
      *p.coupon_rate*date_diff('day',DATE '2026-10-23'+CAST(m.range-1 AS INTEGER)*INTERVAL 1 MONTH,
                                   DATE '2026-10-23'+CAST(m.range AS INTEGER)*INTERVAL 1 MONTH)/365.0) AS rolled_interest
 FROM positions p CROSS JOIN liquidity_assumptions a CROSS JOIN range(1,4) m
 WHERE p.product IN ('Term deposits','Wholesale funding') AND m.range>p.remaining_maturity_months
 GROUP BY ALL
), security_values AS (
 SELECT b.position_id,sum(b.total_cf*d.discount_factor) AS pv
 FROM base b JOIN scenario_discount_inputs d ON d.scenario='Base' AND b.month=d.month
 WHERE b.product='Government securities' GROUP BY b.position_id
), capacity AS (
 SELECT a.scenario,sum(v.pv*(1-least(.95,p.liquidity_haircut+a.extra_haircut))) AS sale_capacity
 FROM liquidity_assumptions a CROSS JOIN positions p JOIN security_values v USING(position_id) GROUP BY a.scenario
), raw_flows AS (
 SELECT w.scenario,w.day,s.opening_cash,s.retail_stock,s.retail_coupon,c.sale_capacity,
  s.retail_total*w.retail_weight AS retail_runoff,s.commitments*w.draw_weight AS commitment_drawdown,
  coalesce(e.term_nonrenewal,0) AS term_nonrenewal,coalesce(e.wholesale_loss,0) AS wholesale_loss,
  coalesce(e.original_interest,0)+coalesce(r.rolled_interest,0) AS funding_interest,
  coalesce(e.contractual_inflow,0) AS contractual_inflow,
  CASE WHEN w.day=w.monetization_day THEN c.sale_capacity ELSE 0 END AS asset_monetization
 FROM weighted w JOIN stocks s USING(scenario) JOIN capacity c USING(scenario)
 LEFT JOIN events e USING(scenario,day) LEFT JOIN rolled r USING(scenario,day)
), interest AS (
 SELECT *, (retail_stock-coalesce(sum(retail_runoff) OVER(PARTITION BY scenario ORDER BY day
                 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0))*retail_coupon/365.0 AS retail_interest
 FROM raw_flows
), outflows AS (
 SELECT *,retail_runoff+commitment_drawdown+term_nonrenewal+wholesale_loss+funding_interest+retail_interest AS total_outflow
 FROM interest
), recognized AS (
 SELECT *,least(contractual_inflow,.75*total_outflow) AS recognized_inflow FROM outflows
), daily AS (
 SELECT *,recognized_inflow-total_outflow AS net_cash_flow,
 contractual_inflow-recognized_inflow AS excluded_inflow FROM recognized
), cumulative AS (
 SELECT *,sum(net_cash_flow) OVER(PARTITION BY scenario ORDER BY day ROWS UNBOUNDED PRECEDING) AS cumulative_net_cash_flow,
 opening_cash+sum(net_cash_flow+asset_monetization) OVER(PARTITION BY scenario ORDER BY day ROWS UNBOUNDED PRECEDING) AS cumulative_liquidity_gap
 FROM daily
)
SELECT scenario,day,retail_runoff,commitment_drawdown,term_nonrenewal,wholesale_loss,
 funding_interest,retail_interest,contractual_inflow,total_outflow,recognized_inflow,
 excluded_inflow,net_cash_flow,asset_monetization,cumulative_net_cash_flow,cumulative_liquidity_gap,
 greatest(0,cumulative_liquidity_gap) AS remaining_liquidity_buffer
FROM cumulative ORDER BY scenario,day;

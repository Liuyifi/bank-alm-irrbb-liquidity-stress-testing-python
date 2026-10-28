-- PARTIAL_RECOMPUTATION: Python cash-flow projection and curve inputs remain
-- shared. SQL independently applies signs, discounts and horizon aggregation;
-- signed_pv, per-cash-flow Python discount_factor and summary CSVs are not used.
WITH valued AS (
 SELECT c.scenario,c.month,c.side,c.interest_cf,
        c.total_cf*d.discount_factor*CASE WHEN c.side='asset' THEN 1 ELSE -1 END AS pv
 FROM cashflows c JOIN scenario_discount_inputs d USING(scenario,month)
)
SELECT scenario,
 sum(CASE WHEN month BETWEEN 1 AND 12 THEN interest_cf*CASE WHEN side='asset' THEN 1 ELSE -1 END ELSE 0 END) AS nii,
 sum(pv) AS eve,
 sum(CASE WHEN side='asset' THEN pv ELSE 0 END) AS asset_pv,
 -sum(CASE WHEN side='liability' THEN pv ELSE 0 END) AS liability_pv
FROM valued GROUP BY scenario ORDER BY scenario;

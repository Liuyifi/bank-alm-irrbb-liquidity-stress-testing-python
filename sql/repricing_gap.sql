-- Independent SQL date bucketing. Whole stock at next repricing/final maturity.
WITH assigned AS (
 SELECT *, CASE
 WHEN fixed_or_floating = 'non_rate' THEN 7
 WHEN CAST(next_repricing_date AS DATE) <= DATE '2026-10-23' + INTERVAL 1 MONTH THEN 0
 WHEN CAST(next_repricing_date AS DATE) <= DATE '2026-10-23' + INTERVAL 3 MONTH THEN 1
 WHEN CAST(next_repricing_date AS DATE) <= DATE '2026-10-23' + INTERVAL 6 MONTH THEN 2
 WHEN CAST(next_repricing_date AS DATE) <= DATE '2026-10-23' + INTERVAL 12 MONTH THEN 3
 WHEN CAST(next_repricing_date AS DATE) <= DATE '2026-10-23' + INTERVAL 24 MONTH THEN 4
 WHEN CAST(next_repricing_date AS DATE) <= DATE '2026-10-23' + INTERVAL 60 MONTH THEN 5
 ELSE 6 END AS sql_bucket FROM positions
), buckets AS (SELECT range AS bucket_order FROM range(8))

, aggregated AS (
SELECT b.bucket_order,
 coalesce(sum(CASE WHEN p.asset_or_liability='asset' AND b.bucket_order<7 THEN principal ELSE 0 END),0) AS rsa,
 coalesce(sum(CASE WHEN p.asset_or_liability='liability' AND b.bucket_order<7 THEN principal ELSE 0 END),0) AS rsl
FROM buckets b LEFT JOIN assigned p ON b.bucket_order=p.sql_bucket
GROUP BY b.bucket_order)
SELECT *, rsa-rsl AS periodic_gap,
 sum(rsa-rsl) OVER(ORDER BY bucket_order ROWS UNBOUNDED PRECEDING) AS cumulative_gap
FROM aggregated ORDER BY bucket_order;

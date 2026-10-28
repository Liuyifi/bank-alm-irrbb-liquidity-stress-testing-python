SELECT asset_or_liability AS side, product,
       count(*) AS positions, sum(principal) AS principal,
       sum(principal * coupon_rate) / nullif(sum(principal),0) AS weighted_coupon
FROM positions GROUP BY ALL ORDER BY side, product;

-- Payment Transaction Amount Outlier & Z-Score Analysis
WITH stats AS (
  SELECT
    AVG(amount_usd) AS mean_amount,
    STDDEV(amount_usd) AS std_amount
  FROM `data-pipeline-immune-system.dpis_silver_dev.payments`
)
SELECT
  p.payment_id,
  p.amount_usd,
  (p.amount_usd - stats.mean_amount) / NULLIF(stats.std_amount, 0) AS z_score
FROM `data-pipeline-immune-system.dpis_silver_dev.payments` p
CROSS JOIN stats
WHERE ABS((p.amount_usd - stats.mean_amount) / NULLIF(stats.std_amount, 0)) > 4.0;

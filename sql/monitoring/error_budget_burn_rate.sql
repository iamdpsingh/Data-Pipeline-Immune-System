-- 30-Day Error Budget Consumption
WITH runs AS (
  SELECT
    COUNT(1) AS total_runs,
    COUNTIF(status = 'SUCCESS') AS successful_runs,
    COUNTIF(status = 'FAILED') AS failed_runs
  FROM `data-pipeline-immune-system.dpis_dev.pipeline_runs`
  WHERE started_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
)
SELECT
  total_runs,
  failed_runs,
  ROUND((1 - SAFE_DIVIDE(failed_runs, total_runs)) * 100, 3) AS achieved_availability,
  -- SLO Target 99.9%
  ROUND((SAFE_DIVIDE(failed_runs, total_runs * 0.001)) * 100, 2) AS error_budget_consumed_pct
FROM runs;

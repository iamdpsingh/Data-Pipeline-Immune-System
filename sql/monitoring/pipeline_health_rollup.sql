-- ==============================================================================
-- Data Pipeline Immune System — Daily Pipeline Health Metric Rollup
-- Dataset: dpis_{environment}
-- ==============================================================================

WITH daily_run_stats AS (
  SELECT
    pipeline_id,
    execution_date,
    COUNT(1) AS total_runs,
    COUNTIF(status = 'SUCCESS') AS successful_runs,
    ROUND(SAFE_DIVIDE(COUNTIF(status = 'SUCCESS'), COUNT(1)) * 100, 2) AS run_success_rate,
    ROUND(AVG(duration_seconds), 2) AS avg_duration_seconds
  FROM
    `{project}.{dataset}.pipeline_runs`
  WHERE
    execution_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY
    pipeline_id,
    execution_date
),

daily_quality_stats AS (
  SELECT
    pipeline_id,
    DATE(timestamp) AS check_date,
    COUNT(1) AS total_checks,
    COUNTIF(status = 'PASS') AS passed_checks,
    ROUND(SAFE_DIVIDE(COUNTIF(status = 'PASS'), COUNT(1)) * 100, 2) AS quality_pass_rate
  FROM
    `{project}.{dataset}.data_quality_results`
  WHERE
    DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  GROUP BY
    pipeline_id,
    check_date
)

SELECT
  GENERATE_UUID() AS metric_id,
  r.pipeline_id,
  r.execution_date AS metric_date,
  r.run_success_rate,
  r.avg_duration_seconds,
  COALESCE(q.quality_pass_rate, 100.0) AS quality_score,
  -- Health Score: Weighted blend (50% Run Success Rate + 50% Quality Score)
  ROUND((r.run_success_rate * 0.50) + (COALESCE(q.quality_pass_rate, 100.0) * 0.50), 2) AS health_score,
  CASE
    WHEN ((r.run_success_rate * 0.50) + (COALESCE(q.quality_pass_rate, 100.0) * 0.50)) >= 90.0 THEN 'HEALTHY'
    WHEN ((r.run_success_rate * 0.50) + (COALESCE(q.quality_pass_rate, 100.0) * 0.50)) >= 70.0 THEN 'WARNING'
    WHEN ((r.run_success_rate * 0.50) + (COALESCE(q.quality_pass_rate, 100.0) * 0.50)) >= 50.0 THEN 'DEGRADED'
    ELSE 'CRITICAL'
  END AS health_status,
  CURRENT_TIMESTAMP() AS calculated_at
FROM
  daily_run_stats r
LEFT JOIN
  daily_quality_stats q
ON
  r.pipeline_id = q.pipeline_id
  AND r.execution_date = q.check_date;

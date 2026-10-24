-- Predictive SLA Breach Warning
SELECT
  pipeline_id,
  run_id,
  started_at,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), started_at, MINUTE) AS runtime_minutes,
  CASE
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), started_at, MINUTE) > 45 THEN 'CRITICAL_RISK'
    WHEN TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), started_at, MINUTE) > 30 THEN 'WARNING'
    ELSE 'NOMINAL'
  END AS sla_risk_level
FROM `data-pipeline-immune-system.dpis_dev.pipeline_runs`
WHERE status = 'RUNNING';

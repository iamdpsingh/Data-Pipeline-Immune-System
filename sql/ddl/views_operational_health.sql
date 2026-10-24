-- Operational Health Summary View
CREATE OR REPLACE VIEW `data-pipeline-immune-system.dpis_dev.v_operational_health` AS
SELECT
  CURRENT_DATE() AS report_date,
  COUNT(DISTINCT pipeline_id) AS active_pipeline_count,
  COUNTIF(status = 'FAILED') AS active_failures,
  ROUND(SAFE_DIVIDE(COUNTIF(status = 'SUCCESS'), COUNT(1)) * 100, 2) AS success_rate_pct
FROM `data-pipeline-immune-system.dpis_dev.pipeline_runs`
WHERE started_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR);

-- Quarantine Reprocessing & Recovery Rate
SELECT
  pipeline_id,
  DATE(quarantined_at) AS quarantine_date,
  COUNT(1) AS total_quarantined_records,
  COUNTIF(status = 'RESOLVED') AS successfully_reprocessed,
  ROUND(SAFE_DIVIDE(COUNTIF(status = 'RESOLVED'), COUNT(1)) * 100, 2) AS recovery_rate_pct
FROM `data-pipeline-immune-system.dpis_dev.quarantine_records`
GROUP BY 1, 2
ORDER BY 2 DESC;

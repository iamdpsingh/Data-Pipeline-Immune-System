-- Velocity of Dead-Letter Quarantine Arrivals
SELECT
  TIMESTAMP_TRUNC(quarantined_at, HOUR) AS quarantine_hour,
  rejection_reason,
  COUNT(1) AS quarantined_record_count
FROM `data-pipeline-immune-system.dpis_dev.quarantine_records`
GROUP BY 1, 2
ORDER BY 1 DESC;

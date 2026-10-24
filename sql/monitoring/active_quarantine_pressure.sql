-- Active Unresolved Quarantine Records
SELECT
  pipeline_id,
  rejection_reason,
  COUNT(1) AS pending_records,
  MIN(quarantined_at) AS oldest_pending_record
FROM `data-pipeline-immune-system.dpis_dev.quarantine_records`
WHERE status = 'PENDING'
GROUP BY 1, 2
ORDER BY pending_records DESC;

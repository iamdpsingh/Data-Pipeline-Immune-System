-- Compute Cost Per Self-Healed Incident
SELECT
  incident_type,
  COUNT(1) AS total_healed,
  ROUND(AVG(remediation_duration_seconds), 2) AS avg_duration_sec,
  -- Estimated Cloud Run serverless cost ($0.00002400 / vCPU-sec)
  ROUND(AVG(remediation_duration_seconds) * 0.00005, 5) AS estimated_usd_cost_per_heal
FROM `data-pipeline-immune-system.dpis_dev.audit_log`
WHERE action_type = 'REMEDIATION_COMPLETE'
GROUP BY 1;

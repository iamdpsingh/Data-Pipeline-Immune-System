-- ==============================================================================
-- Data Pipeline Immune System — Incident MTTR & Remediation Analytics
-- Dataset: dpis_{environment}
-- ==============================================================================

WITH resolved_incidents AS (
  SELECT
    incident_id,
    pipeline_id,
    severity,
    detected_at,
    resolved_at,
    TIMESTAMP_DIFF(resolved_at, detected_at, MINUTE) AS resolution_minutes
  FROM
    `{project}.{dataset}.incidents`
  WHERE
    status = 'RESOLVED'
    AND resolved_at IS NOT NULL
),

remediation_breakdown AS (
  SELECT
    incident_id,
    action,
    risk_level,
    CASE WHEN approved_by IS NULL THEN 'AUTONOMOUS' ELSE 'HUMAN_APPROVED' END AS execution_mode,
    execution_status
  FROM
    `{project}.{dataset}.remediation_actions`
)

SELECT
  i.pipeline_id,
  i.severity,
  COUNT(DISTINCT i.incident_id) AS total_resolved_incidents,
  ROUND(AVG(i.resolution_minutes), 1) AS mttr_minutes,
  ROUND(MIN(i.resolution_minutes), 1) AS min_resolution_minutes,
  ROUND(MAX(i.resolution_minutes), 1) AS max_resolution_minutes,
  COUNTIF(r.execution_mode = 'AUTONOMOUS') AS autonomous_remediations_count,
  COUNTIF(r.execution_mode = 'HUMAN_APPROVED') AS human_approved_remediations_count,
  ROUND(SAFE_DIVIDE(COUNTIF(r.execution_mode = 'AUTONOMOUS'), COUNT(DISTINCT i.incident_id)) * 100, 2) AS autonomous_remediation_pct,
  COUNTIF(r.execution_status = 'SUCCESS') AS successful_remediations,
  ROUND(SAFE_DIVIDE(COUNTIF(r.execution_status = 'SUCCESS'), COUNT(r.incident_id)) * 100, 2) AS remediation_success_rate
FROM
  resolved_incidents i
LEFT JOIN
  remediation_breakdown r
ON
  i.incident_id = r.incident_id
GROUP BY
  i.pipeline_id,
  i.severity
ORDER BY
  i.severity ASC,
  total_resolved_incidents DESC;

-- Autonomous Remediation Audit View
CREATE OR REPLACE VIEW `data-pipeline-immune-system.dpis_dev.v_autonomous_audit` AS
SELECT
  incident_id,
  agent_name,
  action_type,
  status,
  timestamp,
  details
FROM `data-pipeline-immune-system.dpis_dev.audit_log`
ORDER BY timestamp DESC;

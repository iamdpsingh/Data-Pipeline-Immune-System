# Platform Troubleshooting Guide

This operational guide provides diagnostic procedures and resolution playbooks for issues encountered within the **Data Pipeline Immune System** infrastructure, agent processes, and lakehouse execution jobs.

---

## 1. Quick Diagnostic Checklist

When investigating an operational incident:
1. **Check Cloud Run Service Health**:
   ```bash
   curl -I http://localhost:8080/health
   # Expected: HTTP 200 OK with {"status": "UP"}
   ```
2. **Inspect Open Incidents in BigQuery**:
   ```sql
   SELECT incident_id, pipeline_id, severity, status, root_cause
   FROM `data-pipeline-immune-system.dpis_dev.incidents`
   WHERE status NOT IN ('RESOLVED', 'BLOCKED')
   ORDER BY detected_at DESC;
   ```
3. **Verify GCP Logging for Cloud Run**:
   ```bash
   gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="dpis-dev-api"' \
     --project="data-pipeline-immune-system" --limit=20 --format="json"
   ```

---

## 2. Common Failure Modes & Resolution Playbooks

### Issue 1: Remediation Action Fails (`execution_status == 'FAILED'`)

**Symptoms**:
- Incident status moves to `ESCALATED`.
- Remediation audit event logs `FAILED` with an error payload.

**Root Causes**:
1. Upstream file is locked or missing from GCS source bucket.
2. Spark job encounters memory limits (OOM) during backfill execution.
3. BigQuery streaming buffer prevents immediate partition replacement.

**Diagnostic Query**:
```sql
SELECT details, timestamp
FROM `data-pipeline-immune-system.dpis_dev.audit_log`
WHERE agent_name = 'RemediationAgent' AND status = 'FAILED'
ORDER BY timestamp DESC
LIMIT 1;
```

**Resolution**:
1. Verify target GCS bucket permissions:
   ```bash
   gcloud storage ls gs://dpis-dev-source/orders/
   ```
2. If the failure was a transient PySpark executor crash, clear the Airflow task state manually:
   ```bash
   airflow tasks clear orders_transformation_dag --task-regex transform_orders_silver --start-date 2026-10-23
   ```

---

### Issue 2: Verification Agent Reports Failed Post-Repair Checks

**Symptoms**:
- Incident transitions to `ESCALATED` instead of `RESOLVED`.
- `all_checks_passed = False` logged by VerificationAgent.

**Root Causes**:
- The remediation action executed successfully (e.g. partition was reprocessed), but the underlying upstream data source is still corrupted or delivers high null rates.

**Diagnostic Query**:
```sql
SELECT
  check_name,
  check_type,
  expected_value,
  actual_value,
  threshold,
  status
FROM `data-pipeline-immune-system.dpis_dev.data_quality_results`
WHERE is_verification = TRUE
ORDER BY timestamp DESC
LIMIT 5;
```

**Resolution**:
1. Check if quarantined records explain the missing row count:
   ```sql
   SELECT _rule_name, COUNT(*) AS count
   FROM `data-pipeline-immune-system.dpis_dev.quarantine_records`
   WHERE _pipeline_id = 'orders'
   GROUP BY _rule_name;
   ```
2. If upstream data is fundamentally corrupt, escalate to the upstream data provider. Do NOT bypass the verification check.

---

### Issue 3: Schema Drift Detected as Breaking (`P1`) When Additive

**Symptoms**:
- Non-breaking column addition enters `ACTION_SELECTED` requiring human sign-off rather than auto-migrating.

**Root Causes**:
- An added column has a non-nullable constraint or conflicts with a reserved SQL keyword.

**Resolution**:
1. Inspect the schema diff:
   ```sql
   SELECT changed_columns, change_type
   FROM `data-pipeline-immune-system.dpis_dev.schema_versions`
   ORDER BY recorded_at DESC
   LIMIT 1;
   ```
2. If confirmed safe and additive, approve the action via the dashboard or add the field definition to `schemas/silver/orders_silver_schema.json`.

---

### Issue 4: Cloud Run Cold Starts Causing Airflow Webhook Timeouts

**Symptoms**:
- Airflow ingestion DAG times out when emitting run completion events to the Cloud Run controller.

**Resolution**:
- For production environments (`data-pipeline-immune-system`), ensure minimum instances is set to 1 in [config/production.yaml](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/config/production.yaml):
  ```yaml
  cloud_run:
    min_instances: 1  # Prevents cold-start latency
  ```
- Adjust Cloud Run concurrency and request timeout via Terraform.

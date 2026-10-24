# ADR-013: Immutable BigQuery Audit Stream & Forensic Lineage

## Status: Accepted (In Production)

## Context
Autonomous self-healing systems introduce a non-negotiable operational and governance requirement: **Every automated decision and state mutation must be forensically auditable.**

If an autonomous agent re-runs an ingestion job, adjusts a schema, or isolates a partition, engineering teams, security officers, and external auditors must be able to verify:
1. What anomaly triggered the action?
2. Which agent evaluated the risk and which deterministic rules or LLM prompts were executed?
3. What exact database queries, API calls, or partition movements were executed?
4. What were the pre- and post-remediation data quality verification metrics?

Storing logs in ephemeral local files or volatile container stdout streams creates audit blindspots and violates compliance standards (SOC 2, ISO 27001, HIPAA, GDPR).

## Decision
We enforce an **Immutable Append-Only Audit Stream** in BigQuery (`dpis_analytics_<env>.incident_audit_log` and `dpis_analytics_<env>.agent_execution_log`):

1. **Structured Audit Event Schema**:
   Every lifecycle event records a standardized JSON schema:
   - `event_id STRING`: Unique UUID for the audit record.
   - `incident_id STRING`: Correlation ID tying detection, diagnosis, remediation, and verification together.
   - `pipeline_id STRING`: Target pipeline (e.g. `orders`).
   - `agent_name STRING`: `DetectionAgent`, `DiagnosisAgent`, `RiskAgent`, `RemediationAgent`, `VerificationAgent`, or `LearningAgent`.
   - `action_type STRING`: Categorized action (e.g. `ANOMALY_DETECTED`, `RISK_ASSESSED`, `REMEDIATION_EXECUTED`, `REPAIR_VERIFIED`).
   - `status STRING`: `SUCCESS`, `FAILURE`, `BLOCKED`, `PENDING_APPROVAL`.
   - `details JSON`: Complete diagnostic evidence, payload parameters, error traces, and SQL expressions.
   - `timestamp TIMESTAMP`: Authoritative UTC event timestamp.
   - `execution_fingerprint STRING`: SHA-256 cryptographic hash of the input parameters to detect state tampering.

2. **Immutable Storage Policies**:
   - The audit table enforces append-only semantics. BigQuery IAM permissions grant autonomous agents `roles/bigquery.dataEditor` restricted exclusively to `INSERT` statements; `DELETE` and `UPDATE` permissions are explicitly denied.
   - Partitioned by `DATE(timestamp)` with clustering on `(pipeline_id, agent_name, status)`.

3. **Dual Buffering & Local Fallback**:
   - The `AuditLogger` ([`src/observability/audit.py`](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/observability/audit.py)) maintains an in-memory queue that flushes in batches to BigQuery to optimize API quotas.
   - In offline or local development environments, events are mirrored locally to structured JSONL files (`logs/audit_events.jsonl`) to preserve the audit trail without external GCP connectivity.

## Consequences

### Positive
- **100% Traceability**: Every autonomous action can be fully reconstructed from the BigQuery audit tables alone.
- **Enterprise Regulatory Compliance**: Satisfies strict financial and healthcare governance requirements for autonomous systems.
- **Root-Cause Forensics**: Engineers can inspect the exact historical sequence of events for any past incident in seconds using standard SQL.

### Negative / Trade-Offs
- Continuous append-only logging adds storage volume over time (managed via long-term partition expiration or archival to Coldline GCS after 365 days).
- Minor latency overhead (approx. 5-15ms) per agent action to structure and buffer audit events.

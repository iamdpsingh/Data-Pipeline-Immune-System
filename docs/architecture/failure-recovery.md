# Failure Recovery Architecture & Self-Healing Strategies

The primary mission of the **Data Pipeline Immune System** is autonomous recovery from pipeline anomalies and data quality defects without requiring human intervention for routine, low-risk failures, while strictly enforcing safety boundaries for high-risk operations.

This document details the recovery mechanisms, idempotency contracts, circuit breakers, and state resumption strategies implemented across the platform.

---

## 1. Failure Scenario Taxonomy & Recovery Strategies

```
┌──────────────────────────────┬──────────┬─────────────────────────────┬──────────────────────────┐
│ Failure Category             │ Severity │ Root Cause Classification   │ Remediation Action       │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Transient Task Crash         │ P2       │ TRANSIENT_TASK_FAILURE      │ RETRY_TASK               │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Upstream Incomplete Load     │ P1       │ UPSTREAM_PARTIAL_LOAD       │ RETRY_SOURCE_EXTRACTION  │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ API 5xx / Gateway Timeout    │ P2       │ API_TIMEOUT                 │ RETRY_SOURCE_EXTRACTION  │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Missing Data Partition       │ P2       │ MISSING_PARTITION           │ REPROCESS_PARTITION      │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Checksum Mismatch / Corrupt  │ P1       │ CORRUPTED_FILE              │ RELOAD_SOURCE_FILE       │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Additive Schema Expansion    │ P3       │ SCHEMA_ADDITIVE_CHANGE      │ ADD_COLUMN_TO_STAGING    │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Breaking Schema Modification │ P1       │ SCHEMA_BREAKING_CHANGE      │ QUARANTINE_BAD_RECORDS*  │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Sensitive PII Exposure       │ P0       │ PII_EXPOSURE_RISK           │ BLOCK_PIPELINE (Hard)    │
├──────────────────────────────┼──────────┼─────────────────────────────┼──────────────────────────┤
│ Systemic Cascading Failures  │ P1       │ REPEATED_FAILURE            │ ESCALATE_TO_HUMAN        │
└──────────────────────────────┴──────────┴─────────────────────────────┴──────────────────────────┘
* Requires human operator sign-off prior to execution.
```

---

## 2. Idempotency Guarantees

Every remediation handler registered in [src/remediation/actions.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/remediation/actions.py) is designed and tested to be strictly **idempotent**:
- Executing an action multiple times produces the exact same final state as executing it once.
- Partial retries do not generate duplicated records in BigQuery.
- Partition backfills operate via `WRITE_TRUNCATE` on specific date partitions, guaranteeing clean replacement rather than duplicate appends.

### Key Remediation Handlers:
1. `RETRY_TASK`: Clears the task execution state in Airflow, triggering a clean task instance retry with exponential backoff (`t = base * 2^attempt`).
2. `RETRY_SOURCE_EXTRACTION`: Re-polls the upstream extraction source after waiting for the upstream API or landing queue to settle.
3. `REPROCESS_PARTITION`: Replaces the affected partition in the lakehouse staging area and re-runs the PySpark transformation job.
4. `QUARANTINE_BAD_RECORDS`: Routes rejected records to the quarantine dead-letter dataset while emitting clean records downstream.
5. `ADD_COLUMN_TO_STAGING`: Executes a safe `ALTER TABLE ADD COLUMN` for backward-compatible nullable attributes in Bronze staging only.

---

## 3. Circuit Breakers & Anti-Flapping

To prevent infinite retry loops and runaway compute costs:
1. **Max Retry Limits**:
   - `RETRY_TASK`: Maximum 3 attempts.
   - `RETRY_SOURCE_EXTRACTION`: Maximum 3 attempts with a base backoff of 30-60 seconds.
2. **Repeated Failure Threshold**:
   - If the same pipeline fails **3 or more times within a 24-hour window**, the deterministic rule engine intercepts the incident as `REPEATED_FAILURE`.
   - Automated remediation is disengaged and the incident is transitioned immediately to `ESCALATED` for human engineering triage.
3. **Quarantine Ratio Threshold**:
   - If the proportion of malformed records in a batch exceeds `quarantine_max_percentage` (10% in dev, 5% in staging/prod), the system stops auto-quarantining and escalates the incident. This prevents silent data loss where a broken pipeline dumps 90% of its data into quarantine unnoticed.

---

## 4. Crash Recovery & Stateless Controller Resumption

The immune system controller runs on **Cloud Run** and is strictly **stateless**:
- All incident states, transitions, timestamps, and audit events are immediately persisted to BigQuery (`dpis_{environment}.incidents` and `audit_log`).
- In the event of a Cloud Run instance restart (e.g., scale-to-zero cold start, container replacement, or out-of-memory crash mid-lifecycle):
  1. The controller polls BigQuery for open incidents (`status NOT IN ('RESOLVED', 'BLOCKED')`).
  2. The controller resumes from the exact state recorded in BigQuery (`resume_incident(incident_id)`).
  3. No in-memory state is required for lifecycle recovery.

---

## 5. Post-Remediation Verification (Closing the Loop)

In accordance with **ADR-005**:
A pipeline run finishing with a zero exit code is **necessary but not sufficient** for incident closure.

Before any incident transitions to `RESOLVED`:
1. The **Verification Agent** re-runs data quality assertions against the repaired target partition.
2. It asserts:
   - Row volume meets or exceeds the baseline threshold.
   - Null ratio on required columns is <= configured threshold.
   - Duplicate key ratio is <= configured threshold.
3. **Outcomes**:
   - **All Checks Passed**: Incident transitions to `RESOLVED`, and the [LearningAgent](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/agents/learning_agent.py) commits the resolution fingerprint to `incident_memory`.
   - **Any Check Failed**: Incident transitions to `ESCALATED`, triggering an alert for human engineering investigation.

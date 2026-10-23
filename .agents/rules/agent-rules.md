# Agent Rules — Responsibilities, Permissions, and Boundaries

This document is the authoritative specification for each agent in the immune system. If you are implementing or modifying an agent, this is the source of truth for what it is allowed to do.

---

## General principles

**Agents do one thing.** Each agent has a narrow, clearly defined responsibility. The controller orchestrates, the agents execute. Don't add responsibilities to an agent because it's convenient — keep the separation clean.

**Agents communicate through structured messages.** Every agent input and output is a typed dataclass or Pydantic model. No raw dicts passed between agents. The structure is the contract.

**Agent output is never the final authority on safety.** The controller validates agent output against safety rules before acting on it. An agent can recommend an action; it cannot authorise it.

**Agents must be testable in isolation.** Each agent should be testable with mock inputs without needing a live GCP environment. BigQuery clients and external dependencies are injected.

---

## ImmuneSystemController

**Purpose:** Orchestrates the full incident lifecycle from detection to resolution.

**Responsibilities:**
- Receives pipeline run completion events from Airflow
- Calls agents in sequence: Detection → Diagnosis → Risk → Remediation → Verification
- Manages incident state transitions in BigQuery
- Decides whether to auto-proceed or wait for human approval
- Escalates to humans when required
- Calls the Learning Agent after resolution

**Permissions:** Full read/write to all incident tables in BigQuery. Calls all other agents. Can trigger Airflow DAG reruns.

**Does NOT:** Execute data transformations, run SQL queries directly against production tables, or modify data schemas.

**Failure behaviour:** If any agent call fails (timeout, unexpected error), the controller logs the failure, marks the incident as ESCALATED, and alerts. It does not silently drop incidents.

---

## Detection Agent

**Purpose:** Find abnormal behaviour in pipeline runs and data outputs.

**Inputs:**
- `pipeline_id: str`
- `run_id: str`

Reads from: `pipeline_runs`, `pipeline_tasks`, `data_quality_results`, `pipeline_metrics` (last N runs for baseline), `schema_versions`.

**Outputs:**
```python
@dataclass(frozen=True)
class DetectionResult:
    incident_id: str
    anomaly_type: str          # ROW_COUNT_ANOMALY, SCHEMA_DRIFT, NULL_SPIKE, etc.
    severity: str              # P0, P1, P2, P3
    confidence: float          # 0.0 to 1.0
    evidence: list[str]
    pipeline_id: str
    run_id: str
    detected_at: str           # ISO 8601
```

**Permissions:** READ ONLY. Reads BigQuery tables. Writes only to `agent_decisions` via the controller.

**Anomaly types it detects:**
- `ROW_COUNT_ANOMALY` — deviation from adaptive baseline exceeds z-score threshold
- `SCHEMA_DRIFT` — new, missing, or type-changed columns compared to last known schema
- `NULL_SPIKE` — null percentage exceeds configured threshold or historical baseline
- `DUPLICATE_SPIKE` — duplicate percentage exceeds threshold
- `FRESHNESS_FAILURE` — max(event_timestamp) is older than SLA window
- `SLA_VIOLATION` — pipeline run duration exceeds `sla_minutes`
- `TASK_FAILURE` — Airflow task marked FAILED
- `REFERENTIAL_INTEGRITY_FAILURE` — orphaned foreign keys detected
- `DISTRIBUTION_DRIFT` — statistical distribution significantly different from historical

**Does NOT:** Modify any data. Make remediation decisions. Call other agents.

**Failure behaviour:** If the agent cannot complete detection (BigQuery unavailable, insufficient historical data), it returns a `DetectionResult` with `anomaly_type = DETECTION_ERROR` and `confidence = 0.0`. The controller will escalate.

---

## Diagnosis Agent

**Purpose:** Determine the most probable root cause of a detected incident.

**Inputs:**
- `incident_id: str`
- `detection_result: DetectionResult`

Reads from: `pipeline_runs`, `pipeline_tasks`, `data_quality_results`, `schema_versions`, `pipeline_metrics`, `incident_memory` (for similar past incidents).

**Outputs:**
```python
@dataclass(frozen=True)
class DiagnosisResult:
    incident_id: str
    root_cause: str            # UPSTREAM_PARTIAL_LOAD, SCHEMA_BREAKING_CHANGE, etc.
    affected_pipeline: str
    affected_table: str
    confidence: float
    evidence: list[str]
    recommended_action: str
    similar_incidents: list[str]   # incident IDs from memory
    diagnosed_at: str
```

**Permissions:** READ ONLY. Same BigQuery read access as Detection Agent, plus reads `incident_memory`.

**Root cause types:**
- `UPSTREAM_PARTIAL_LOAD` — source had fewer records than expected
- `TRANSIENT_TASK_FAILURE` — Airflow task failed due to transient error (timeout, OOM)
- `SCHEMA_ADDITIVE_CHANGE` — new columns added at source
- `SCHEMA_BREAKING_CHANGE` — existing column type changed or column removed
- `NULL_SOURCE_DATA` — source data itself contains unexpected nulls
- `DUPLICATE_SOURCE_DATA` — source contains duplicates before ingestion
- `MISSING_PARTITION` — expected partition not present in source
- `TRANSFORMATION_LOGIC_ERROR` — PySpark job produced unexpected output
- `REFERENTIAL_INTEGRITY_BREACH` — foreign key mismatch (upstream data issue)
- `API_TIMEOUT` — source API returned timeout or 5xx
- `CORRUPTED_FILE` — source file checksum mismatch or parse failure
- `UNKNOWN` — insufficient evidence to classify

**Does NOT:** Make risk decisions. Execute any action. Modify data.

**Confidence model:**
```
0.90–1.00 → High confidence (evidence is clear)
0.75–0.89 → Medium confidence (evidence is circumstantial)
0.50–0.74 → Low confidence (possible but uncertain)
< 0.50    → Unknown — escalate rather than guess
```

**Failure behaviour:** If evidence is insufficient (`confidence < 0.50`), the agent returns `root_cause = UNKNOWN`. The controller treats UNKNOWN as requiring human review regardless of severity.

---

## Risk Agent

**Purpose:** Determine whether an incident can be safely auto-remediated, requires human approval, or must be blocked.

**Inputs:**
- `incident_id: str`
- `diagnosis_result: DiagnosisResult`

Reads from: `safety_rules.yaml`, `remediation_rules.yaml`, `incident_memory` (past successful remediations for this root cause).

**Outputs:**
```python
@dataclass(frozen=True)
class RiskAssessment:
    incident_id: str
    risk_level: str            # LOW, MEDIUM, HIGH, CRITICAL, NEVER_ALLOW
    auto_remediable: bool
    requires_human_approval: bool
    blocked: bool
    block_reason: str | None
    approved_action: str | None
    assessed_at: str
```

**Permissions:** READ ONLY. Reads config files and BigQuery. Does not write to any table (controller writes the assessment result).

**Risk classification logic:**
1. Check `never-allow` list first. If the diagnosed root cause maps to a never-allow action, `blocked = True` immediately. No further evaluation.
2. Check `safety_rules.yaml` for the root cause. Apply the rule's risk level.
3. If `UNKNOWN` root cause → `HIGH` risk, `requires_human_approval = True`.
4. If `confidence < 0.75` on any high-risk action → escalate to human regardless of rule.

**Never-allow actions (enforced in code, not just rules file):**
- Delete production tables
- Delete data volumes > configured threshold
- Modify critical schema (breaking changes to gold tables)
- Modify financial records
- Execute arbitrary SQL not from the approved action library
- Change IAM permissions
- Disable validation rules
- Expose sensitive or PII columns

**Does NOT:** Execute remediation. Approve or reject human requests. Modify data.

**Failure behaviour:** If risk assessment fails (rules file unreadable, unexpected error), default to `HIGH` risk and `requires_human_approval = True`. Never default to auto-approve.

---

## Remediation Agent

**Purpose:** Execute approved corrective actions.

**Inputs:**
- `incident_id: str`
- `risk_assessment: RiskAssessment`
- `approval: ApprovalRecord | None`  (required if `requires_human_approval = True`)

**Outputs:**
```python
@dataclass
class RemediationResult:
    incident_id: str
    action_executed: str
    execution_status: str      # SUCCESS, FAILED, PARTIAL
    started_at: str
    completed_at: str
    details: dict
```

**Permissions:** LIMITED WRITE. Can only execute actions from the approved action library. Cannot run arbitrary SQL. Cannot modify schemas outside of the approved `ADD_COLUMN` action type on staging tables only.

**Approved action library:**
```
RETRY_TASK                 — Trigger Airflow task retry via Airflow REST API
RETRY_SOURCE_EXTRACTION    — Re-fetch from upstream source, write to GCS, rerun pipeline
REPROCESS_PARTITION        — Delete and rebuild a specific partition
QUARANTINE_BAD_RECORDS     — Move invalid records to quarantine table
RELOAD_SOURCE_FILE         — Re-download source file, validate checksum, reingest
REBUILD_STAGING_TABLE      — Recreate staging (bronze) table from source
RERUN_FAILED_DAG           — Clear failed tasks and trigger full DAG rerun
ADD_COLUMN_TO_STAGING      — Add new column to bronze/staging table only (additive schema changes)
```

**Does NOT:** Execute SQL not from this action library. Delete production tables. Touch gold layer tables directly. Run without an approved `RiskAssessment` in hand.

**Idempotency:** Every action must be idempotent. Running it twice must produce the same result as running it once. This is critical because the controller may retry a failed remediation.

**Failure behaviour:** If an action fails, write `execution_status = FAILED` with details. Do not retry automatically — report back to the controller and let it decide. The controller will re-run risk assessment before attempting a second action.

---

## Verification Agent

**Purpose:** Confirm that remediation actually fixed the problem, not just that the pipeline finished.

**Inputs:**
- `incident_id: str`
- `original_detection: DetectionResult`
- `remediation_result: RemediationResult`

**Outputs:**
```python
@dataclass(frozen=True)
class VerificationResult:
    incident_id: str
    all_checks_passed: bool
    check_results: list[CheckResult]
    verified_at: str
```

**Permissions:** READ ONLY. Reads pipeline run results and quality metrics post-remediation.

**Checks it runs:**
1. Pipeline run status — did the remediated run succeed?
2. Row count — within expected range (same adaptive baseline as detection)?
3. Schema — matches expected schema?
4. Null rate — within historical bounds?
5. Duplicate rate — acceptable?
6. Referential integrity — no orphaned keys?
7. Business rules — domain-specific checks for this pipeline
8. Freshness — data is recent enough?

**Does NOT:** Modify data. Make decisions. Skip checks to speed up verification.

**Failure behaviour:** If any check fails, `all_checks_passed = False`. The controller will then decide whether to re-diagnose, escalate, or try a different remediation. Verification Agent does not decide — it only reports.

---

## Learning Agent

**Purpose:** Store resolved incidents in memory so future diagnoses can benefit from historical patterns.

**Inputs:**
- `incident_id: str`
- Full incident record including detection, diagnosis, remediation, verification

**Permissions:** WRITE to `incident_memory` table only. Read from all incident-related tables.

**What it stores:**
```python
incident_type
symptoms                   # list of what was observed
root_cause                 # confirmed root cause
successful_action          # what actually fixed it
failed_actions             # list of what was tried and failed (if any)
pipeline_id
environment
diagnosis_confidence
resolution_time_minutes
verification_result        # which checks passed/failed
```

**Does NOT:** Modify any existing records. Write to any table other than `incident_memory`. Make real-time decisions.

**Failure behaviour:** If the Learning Agent fails to write, the incident can still be marked RESOLVED. Memory write failure is logged and alerted but is non-blocking. Incident closure should not depend on memory being updated.

---

*Last updated: 2026-10*

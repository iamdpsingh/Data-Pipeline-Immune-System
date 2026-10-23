# System Flow — Data Pipeline Immune System

This document describes exactly how data and control flow through the system, from raw source data arriving in GCS to an incident being resolved and stored in memory. It's meant to be the practical reference when debugging the system or tracing why a specific decision was made.

For the architecture rationale behind these design choices, see [decision.md](decisions/decision.md).

---

## 1. Normal pipeline flow (no failures)

This is what happens on a healthy run. Understanding this is important before understanding what breaks.

```
DATA SOURCE (CSV / API / Database)
          │
          ↓
Google Cloud Storage (raw files, partitioned by date)
          │
          ↓
Airflow DAG triggered (scheduled or manual)
          │
          ↓
  ┌───────────────────────────────┐
  │  ingestion_dag                │
  │                               │
  │  1. extract                   │
  │     Pull from source/GCS      │
  │     Write to bronze layer     │
  │                               │
  │  2. validate_raw              │
  │     Schema check              │
  │     Null check                │
  │     Volume sanity check       │
  │                               │
  │  3. transform                 │
  │     PySpark job               │
  │     Clean, standardise, join  │
  │                               │
  │  4. validate_silver           │
  │     Full quality checks       │
  │     Referential integrity     │
  │     Business rules            │
  │                               │
  │  5. load_gold                 │
  │     Aggregate and shape data  │
  │                               │
  │  6. validate_gold             │
  │     Final quality gates       │
  │                               │
  │  7. publish                   │
  │     Mark run complete         │
  │     Update pipeline metrics   │
  └───────────────────────────────┘
          │
          ↓
BigQuery (bronze → silver → gold tables)
          │
          ↓
Observability engine records:
  - run metadata (run_id, pipeline_id, start, end, status)
  - row counts at each stage
  - task-level durations
  - quality check results
  - pipeline health score update
```

At this point the immune system is watching but has nothing to do. The detection engine runs after the DAG finishes, confirms everything is within expected ranges, and writes a clean health record.

---

## 2. Failure detection flow

Detection runs at two points: at the end of every pipeline run (post-run sweep), and continuously for freshness and SLA monitoring (polling loop).

```
Pipeline run completes (success or failure)
          │
          ↓
Detection Agent triggered (via Airflow sensor or Cloud Scheduler)
          │
          ↓
  ┌───────────────────────────────────────┐
  │  Detection Agent                      │
  │  (READ ONLY)                          │
  │                                       │
  │  Reads from BigQuery:                 │
  │    - pipeline_runs                    │
  │    - pipeline_tasks                   │
  │    - data_quality_results             │
  │    - pipeline_metrics (historical)    │
  │    - schema_versions                  │
  │                                       │
  │  Checks:                              │
  │                                       │
  │  1. Task failure check                │
  │     Was any Airflow task marked FAIL? │
  │                                       │
  │  2. Row count anomaly                 │
  │     Compare to adaptive baseline      │
  │     z-score > threshold → anomaly     │
  │                                       │
  │  3. Schema drift                      │
  │     Compare to last known schema      │
  │     New columns? Removed? Type change?│
  │                                       │
  │  4. Null spike                        │
  │     null% vs historical null%         │
  │                                       │
  │  5. Duplicate spike                   │
  │     duplicate% vs threshold           │
  │                                       │
  │  6. Freshness check                   │
  │     max(event_ts) vs SLA              │
  │                                       │
  │  7. Referential integrity             │
  │     Orphaned foreign keys             │
  │                                       │
  │  8. SLA violation                     │
  │     Run duration vs sla_minutes       │
  │                                       │
  │  9. Distribution drift                │
  │     Statistical comparison vs history │
  └───────────────────────────────────────┘
          │
          ↓ (if anomaly found)
  Severity classification:
    P0 → immediately escalate (skip diagnosis, alert human)
    P1 → diagnose with high priority
    P2 → diagnose normally
    P3 → log and monitor
          │
          ↓
  Incident created in BigQuery (incidents table)
  Status: DETECTED
```

If nothing anomalous is found, the agent writes a clean health record and exits. No incident is created.

---

## 3. Diagnosis flow

```
Incident (status: DETECTED)
          │
          ↓
Rules Engine runs first
          │
  ┌───────┴──────────────────────────┐
  │                                  │
Known pattern                   Unknown pattern
  │                                  │
  ↓                                  ↓
Deterministic classification    Diagnosis Agent
  │                             (READ ONLY)
  │                                  │
  │                     Reads:
  │                       - pipeline_runs (current + historical)
  │                       - pipeline_tasks (task-level detail)
  │                       - data_quality_results
  │                       - schema_versions
  │                       - pipeline_metrics
  │                       - incident_memory (similar past incidents)
  │                                  │
  │                     Investigates:
  │                       - Was the Airflow task itself a failure?
  │                       - Did the source file have fewer records?
  │                       - Did the upstream extraction complete?
  │                       - Is the schema unchanged?
  │                       - Did a transformation join produce nulls?
  │                       - Is this a repeated failure pattern?
  │                                  │
  │                     Produces:
  │                       {
  │                         root_cause: "UPSTREAM_PARTIAL_LOAD",
  │                         affected_pipeline: "orders_pipeline",
  │                         affected_table: "silver_orders",
  │                         confidence: 0.91,
  │                         evidence: [...],
  │                         recommended_action: "retry_source_extraction"
  │                       }
  │
  └─────────────────┬────────────────┘
                    ↓
  Diagnosis written to BigQuery (diagnoses table)
  Incident status: DIAGNOSED
```

The Diagnosis Agent doesn't write to the incident table directly — it writes to the `diagnoses` table and the controller updates the incident status. This separation keeps the agent read-only at the data layer.

---

## 4. Risk assessment flow

```
Diagnosis available
          │
          ↓
Risk Agent
(READ ONLY)
          │
  Evaluates:
    - root_cause type (known vs unknown)
    - severity of the incident
    - reversibility of the proposed action
    - blast radius (how many tables/pipelines are affected)
    - whether PII or financial data is involved
    - confidence of the diagnosis
    - whether this exact action has succeeded before (memory)
          │
  Checks against safety_rules.yaml:
    - never-allow actions are blocked immediately
    - high-risk actions require human approval
    - low-risk actions with high confidence → auto-remediate
          │
          ↓
  ┌───────────────────────────────┐
  │  Risk classification:         │
  │                               │
  │  LOW     → auto-remediate     │
  │  MEDIUM  → auto if rule allows│
  │  HIGH    → human approval     │
  │  CRITICAL→ block and escalate │
  └───────────────────────────────┘
          │
          ↓
  Decision written to BigQuery (agent_decisions table)
  Incident status: RISK_ASSESSED
```

The never-allow check happens here in application code, not inside the LLM. Even if the Diagnosis Agent recommends an action that falls under a never-allow rule, the Risk Agent blocks it unconditionally.

---

## 5. Decision branching

```
Risk assessment complete
          │
          ↓
  ┌───────────────────────────────┐
  │  ImmuneSystemController       │
  └───────────────────────────────┘
          │
    ┌─────┴──────────────────┐
    │                        │
 AUTO-REMEDIABLE         HUMAN APPROVAL REQUIRED
    │                        │
    ↓                        ↓
Remediation Agent       Approval request written
(proceed directly)      to BigQuery (approval_requests)
                             │
                             ↓
                        Dashboard shows pending approval
                        with:
                          - incident summary
                          - diagnosis
                          - confidence
                          - proposed action
                          - risk level
                          - evidence
                             │
                        Human reviews and clicks:
                          [ APPROVE ] or [ REJECT ]
                             │
                        Controller notified via webhook
                             │
                    ┌────────┴───────┐
                    │                │
                 APPROVED         REJECTED
                    │                │
                    ↓                ↓
               Remediation       Incident marked
               Agent proceeds    ESCALATED, alert sent
```

For P0 incidents, the controller skips both paths and goes directly to BLOCK + escalation without waiting for user input.

---

## 6. Remediation flow

```
Remediation approved (auto or human)
          │
          ↓
Remediation Agent
(LIMITED WRITE — specific approved actions only)
          │
  Action type determines what happens:
          │
  ┌───────────────────────────────────────────────┐
  │                                               │
  │  RETRY_TASK                                   │
  │    Trigger Airflow task retry via API          │
  │    Max 3 retries with exponential backoff      │
  │                                               │
  │  RETRY_SOURCE_EXTRACTION                      │
  │    Re-fetch from upstream API/source           │
  │    Write fresh file to GCS                    │
  │    Trigger pipeline rerun                     │
  │                                               │
  │  REPROCESS_PARTITION                          │
  │    Identify missing/corrupt partition          │
  │    Delete partition from target table          │
  │    Rerun PySpark job for that partition        │
  │                                               │
  │  QUARANTINE_BAD_RECORDS                       │
  │    Move invalid records to quarantine table   │
  │    Continue pipeline with valid subset        │
  │                                               │
  │  RELOAD_SOURCE_FILE                           │
  │    Re-download source file from origin        │
  │    Validate checksum                          │
  │    Rerun ingestion                            │
  │                                               │
  │  REBUILD_STAGING_TABLE                        │
  │    Recreate staging table from source         │
  │    Only allowed for staging, never production │
  │                                               │
  │  RERUN_FAILED_DAG                             │
  │    Clear failed tasks in Airflow              │
  │    Trigger DAG run                            │
  └───────────────────────────────────────────────┘
          │
  Every action is logged:
    - action type
    - reason
    - risk level
    - started_at
    - completed_at
    - execution status
          │
          ↓
  Remediation result written to BigQuery
  Incident status: REMEDIATION_COMPLETE
```

The Remediation Agent cannot execute arbitrary SQL. It can only call pre-defined action handlers, each of which has its own scope, safety checks, and audit logging.

---

## 7. Verification flow

```
Remediation complete
          │
          ↓
Verification Agent
(READ ONLY)
          │
  Runs the same checks that detected the original anomaly, plus:
          │
  ┌───────────────────────────────────────┐
  │  For every verified incident:         │
  │                                       │
  │  1. Pipeline status                   │
  │     Did the remediated run succeed?   │
  │                                       │
  │  2. Row count                         │
  │     Within expected range?            │
  │                                       │
  │  3. Schema                            │
  │     Matches expected schema?          │
  │                                       │
  │  4. Null rate                         │
  │     Within historical bounds?         │
  │                                       │
  │  5. Duplicate rate                    │
  │     Within acceptable threshold?      │
  │                                       │
  │  6. Referential integrity             │
  │     No orphaned foreign keys?         │
  │                                       │
  │  7. Business rules                    │
  │     Domain-specific checks            │
  │                                       │
  │  8. Freshness                         │
  │     Data is current enough?           │
  └───────────────────────────────────────┘
          │
          ↓
  ALL PASS → Verification SUCCESS
  ANY FAIL → Verification FAILURE
          │
    ┌─────┴──────────────────┐
    │                        │
  SUCCESS                 FAILURE
    │                        │
    ↓                        ↓
Incident marked           Re-diagnose:
RESOLVED                  - was remediation wrong?
    │                     - is it a different problem?
    ↓                     - escalate to human
Stored in                 Incident status: ESCALATED
incident_memory
```

Verification results are written to `verification_results` table. A developer can always query this to see exactly which check passed or failed and what the expected vs actual values were.

---

## 8. Memory and learning flow

```
Incident RESOLVED
          │
          ↓
Learning Agent writes to incident_memory:
  - incident_type
  - symptoms observed
  - root_cause confirmed
  - successful_action
  - failed_actions (if any retries happened)
  - pipeline
  - environment
  - confidence of original diagnosis
  - resolution_time
  - verification_result
          │
          ↓
Future diagnosis:
  Diagnosis Agent queries incident_memory
  Finds similar incidents by symptom similarity
  Uses historical patterns to inform confidence
  and recommended action
```

The memory doesn't replace diagnosis — it informs it. The Diagnosis Agent still goes through the full investigation, but it can weigh its conclusion against what worked before.

---

## 9. Incident lifecycle states

```
DETECTED
    │
CLASSIFIED
    │
DIAGNOSED
    │
RISK_ASSESSED
    │
ACTION_SELECTED
    │
REMEDIATION
    │
    ├── ESCALATED (human needed, waiting)
    │
    ├── BLOCKED (never-allow rule triggered)
    │
VERIFICATION
    │
    ├── RESOLVED (all checks pass)
    │
    └── ESCALATED (verification failed)
```

Every state transition is written to `incident_events` with a timestamp and the reason for the transition. A developer can reconstruct the full incident timeline from this table.

---

## 10. Failure injection flow

Used during testing and demonstration. Not active in production.

```
failure_injection/schema_drift.py --pipeline orders --type additive
          │
          ↓
Injects modified schema file into GCS source path
          │
          ↓
Normal pipeline run triggered
          │
          ↓
Immune system detects schema change
          │
          ↓
System responds according to change type:
  - Additive → risk LOW → auto-handle → verify
  - Breaking → risk HIGH → block → human approval
          │
          ↓
Test validates expected immune response occurred
```

Each failure injection module documents exactly what it simulates, what the expected detection behaviour is, and what the expected remediation is. See `failure_injection/README.md` for the full catalogue.

---

## 11. API flow (Cloud Run)

Airflow DAGs call the immune system via HTTP. The agent service exposes:

```
POST /detect       → triggers detection for a completed run
POST /diagnose     → triggers diagnosis for a detected incident
POST /assess-risk  → triggers risk assessment for a diagnosed incident
POST /remediate    → triggers remediation (must have approval if required)
POST /verify       → triggers verification for a remediated incident
GET  /incidents/{id}  → returns full incident state
GET  /health       → service health check
```

Airflow calls these sequentially via a sensor DAG (`immune_monitor_dag.py`). Each call is authenticated using a service account token. The service account has only the permissions it needs — no more.

---

## 12. Data quality check types

The quality engine checks the following at each pipeline stage:

| Check type | What it verifies |
|---|---|
| Completeness | null_percentage ≤ configured threshold |
| Uniqueness | duplicate_percentage ≤ configured threshold |
| Validity | field-level rules (e.g., amount ≥ 0, age between 0 and 120) |
| Referential integrity | foreign key exists in parent table |
| Freshness | max(event_timestamp) is within SLA window |
| Volume | actual_rows within ±20% of expected (adaptive) |
| Schema | columns, types, and nullable rules match expected schema |
| Distribution | statistical comparison of field distributions vs historical baseline |

Check results are written to `data_quality_results`. Every check has an `expected_value`, `actual_value`, `threshold`, `status` (PASS/FAIL/WARN), and `severity`.

---

## 13. Pipeline health score calculation

After each run, the pipeline's health score is recalculated:

```
health_score = (
    reliability_score    * 0.30 +
    freshness_score      * 0.20 +
    quality_score        * 0.20 +
    schema_stability     * 0.15 +
    sla_compliance       * 0.15
)
```

Each sub-score is calculated from the last N runs (configurable, default 14). The score is stored in `pipeline_metrics` and displayed on the dashboard.

---

*Last updated: 2026-10*

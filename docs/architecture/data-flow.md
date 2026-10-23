# End-to-End Data Flow Architecture

The **Data Pipeline Immune System** operates across two distinct, decoupled planes:
1. **The Primary Data Plane**: The medallion lakehouse architecture carrying source data through Bronze, Silver, and Gold tiers, featuring dead-letter quarantine routing.
2. **The Immune Control Plane**: The event-driven, autonomous monitoring and remediation loop that observes the data plane, diagnoses faults, executes idempotent repairs, verifies data recovery, and updates long-term memory.

---

## 1. Architectural Planes Overview

```
                      PRIMARY DATA PLANE (Medallion Lakehouse)
 ┌─────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
 │ GCS Source  │ ──> │ BigQuery Bronze│ ──> │ BigQuery Silver│ ──> │ BigQuery Gold  │
 │ (JSON Feeds)│     │ (Raw Landed)   │     │ (Validated)    │     │ (Daily Marts)  │
 └─────────────┘     └────────────────┘     └───────┬────────┘     └────────────────┘
                                                    │
                                                    ▼ (ADR-008 Quarantine)
                                            ┌────────────────┐
                                            │ GCS Quarantine │
                                            │ (Dead-Letter)  │
                                            └────────────────┘
 ────────────────────────────────────────────────────────────────────────────────────
                     IMMUNE CONTROL PLANE (Autonomous Loop)
 ┌─────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
 │ Airflow /   │ ──> │ Detection      │ ──> │ Diagnosis      │ ──> │ Risk           │
 │ Run Sensor  │     │ (Z-Score/Rules)│     │ (Rules + LLM)  │     │ (Never-Allow)  │
 └─────────────┘     └────────────────┘     └────────────────┘     └───────┬────────┘
                                                                           │
 ┌─────────────┐     ┌────────────────┐     ┌────────────────┐             │
 │ BigQuery    │ <── │ Verification   │ <── │ Remediation    │ <───────────┘
 │ Memory / Log│     │ (Quality Assert│     │ (Action Lib)   │
 └─────────────┘     └────────────────┘     └────────────────┘
```

---

## 2. Primary Data Plane: Tier Specifications

### Tier 1 — Source Landing (`GCS`)
- **Location**: `gs://dpis-{environment}-source/orders/YYYY-MM-DD/`
- **Format**: JSON newline-delimited (`.json`) or CSV.
- **Contract**: Conforms to [schemas/source/orders_source_schema.json](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/schemas/source/orders_source_schema.json).
- **Ingestion**: Upstream providers drop batch files overnight prior to the 02:00 AM UTC ingestion DAG window.

### Tier 2 — Bronze Raw Stage (`BigQuery / GCS Parquet`)
- **Table**: `data-pipeline-immune-system.dpis_bronze_{environment}.orders`
- **Job**: [spark/jobs/orders_bronze_ingestion.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/spark/jobs/orders_bronze_ingestion.py)
- **Characteristics**:
  - Raw, unmutated landing representation.
  - Appends technical lineage columns: `_source_file`, `_ingested_at`, `_run_id`.
  - Immutable audit record of the raw landing payload.

### Tier 3 — Silver Conformed & Quarantine Routing (`BigQuery`)
- **Table**: `data-pipeline-immune-system.dpis_silver_{environment}.orders`
- **Quarantine Store**: `data-pipeline-immune-system.dpis_{environment}.quarantine_records` and `gs://dpis-{environment}-quarantine/`
- **Job**: [spark/jobs/orders_silver_transformation.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/spark/jobs/orders_silver_transformation.py)
- **Transformations**:
  - Deduplication: Window partitioned by `order_id` ordering by `order_date DESC, _ingested_at DESC`.
  - Currency Normalization: Converts multi-currency transactions (`EUR`, `GBP`, `CAD`, `AUD`) into USD using standard conversion rates.
  - Timestamp parsing: Generates UTC partition date (`order_date_partition`).
- **Quarantine Engine (ADR-008)**:
  - Validates `NON_NULL_ORDER_ID`, `NON_NULL_CUSTOMER_ID`, `POSITIVE_AMOUNT`, and `VALID_STATUS`.
  - Valid records flow to Silver conformed table.
  - Invalid records are diverted to dead-letter quarantine with `_failure_reason`, `_rule_name`, `_raw_record`, and `_quarantined_at`.

### Tier 4 — Gold Business Aggregations (`BigQuery`)
- **Table**: `data-pipeline-immune-system.dpis_gold_{environment}.orders_daily_summary`
- **Job**: [spark/jobs/orders_gold_aggregation.py](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/spark/jobs/orders_gold_aggregation.py)
- **Metrics Computed**:
  - `total_orders`, `completed_orders`, `cancelled_orders`
  - `gross_revenue_usd` (sum of completed orders)
  - `avg_order_value_usd` (AOV)
  - `unique_customers` (active unique customer reference count)
  - Partitioned by `order_date`.

---

## 3. Immune Control Plane: Telemetry & Decision Lifecycle

```
    Pipeline Run
         │
         ▼
[ Detection Agent ] ────── No Anomaly ──────> Log Clean & Exit
         │
   Anomaly Found
         │
         ▼
[ BigQuery: CREATE INCIDENT ] (State: DETECTED -> CLASSIFIED)
         │
         ▼
[ Diagnosis Agent ]
   ├── Deterministic Rules Engine (detection_rules.yaml)
   ├── Incident Memory Similarity Lookup (ADR-006)
   └── LLM Reasoning Fallback (Gemini API)
         │
         ▼
[ Risk Agent ]
   ├── NEVER-ALLOW CHECK (never_allow.py) ── Violation ──> BLOCKED & Alert
   ├── High-Risk Action Check ────────────── Required ───> ACTION_SELECTED (Awaiting Human Sign-off)
   └── Auto-Remediable Action Check
         │
         ▼
[ Remediation Agent ]
   └── Executes Idempotent Handler (actions.py)
         │
         ▼
[ Verification Agent ] (ADR-005)
   └── Re-runs Data Quality Assertions on Repaired Dataset
         ├── FAILED ──> ESCALATED (Alert On-call)
         └── PASSED
               │
               ▼
[ Learning Agent ] (ADR-006)
   └── Commits Fingerprint to BigQuery `incident_memory`
         │
         ▼
[ BigQuery: INCIDENT RESOLVED ] (Lifecycle Complete)
```

---

## 4. Telemetry Schema Mapping

Every state change throughout the flow writes to dedicated BigQuery control tables:

| Lifecycle Stage | BigQuery Table | Primary Recorded Attributes |
|---|---|---|
| **Pipeline Execution** | `pipeline_runs` | `run_id`, `pipeline_id`, `duration_seconds`, `rows_written`, `rows_quarantined`, `status` |
| **Quality Assertions** | `data_quality_results` | `quality_id`, `check_name`, `expected_value`, `actual_value`, `threshold`, `status`, `is_verification` |
| **Incident Tracking** | `incidents` | `incident_id`, `incident_type`, `severity`, `status`, `root_cause`, `confidence`, `detected_at`, `resolved_at` |
| **Audit Trails** | `audit_log` | `event_id`, `incident_id`, `agent_name`, `action_type`, `details`, `timestamp` |
| **Long-Term Memory** | `incident_memory` | `memory_id`, `incident_id`, `pipeline_id`, `root_cause`, `symptoms`, `resolution_action`, `outcome` |

This dual-plane architecture guarantees complete data isolation: pipeline processing continues safely while the immune control plane maintains full auditability and autonomous self-healing.

# System Architecture — Data Pipeline Immune System

This document describes the overall system structure. For the detailed data and control flows, see [`docs/flow.md`](../flow.md). For why things are designed this way, see [`docs/decisions/decision.md`](../decisions/decision.md).

---

## High-level design

The system has three distinct concerns, kept separate intentionally:

1. **The data platform** — ingests, transforms, and stores data (Bronze → Silver → Gold)
2. **The observability layer** — collects metrics, logs, lineage, and quality results
3. **The immune system** — watches the observability layer and acts when something is wrong

This separation means the data pipeline doesn't need to know the immune system exists. The immune system is a reliability wrapper, not a component inside the pipeline.

```
DATA SOURCES
     │
     ↓
Google Cloud Storage
     │
     ↓
┌─────────────────────────────────┐
│ Data Platform                   │
│                                 │
│  Ingestion → Bronze             │
│       ↓                         │
│  Transformation → Silver        │
│       ↓                         │
│  Aggregation → Gold             │
└────────────────┬────────────────┘
                 │
         ┌───────┴───────┐
         ↓               ↓
  Observability     Immune System
  Layer             │
  │                 ├── Detection
  │                 ├── Diagnosis
  └────────────────→├── Risk
  (feeds metrics)   ├── Remediation
                    ├── Verification
                    └── Memory
                         │
                    ┌────┘
                    ↓
             Incident Engine
             (BigQuery)
                    │
                    ↓
             Dashboard / Alerts
```

---

## GCP services

| Service | Role |
|---|---|
| Google Cloud Storage | Raw data landing zone, source files, quarantine storage |
| Dataproc / Serverless Spark | PySpark transformation jobs |
| BigQuery | Data warehouse (all layers) + incident/metadata store |
| Cloud Composer (Airflow) | Pipeline orchestration |
| Cloud Run | Immune system agent API |
| Cloud Logging | Centralised log aggregation |
| Cloud Monitoring | Metrics and alerting |
| Secret Manager | Credentials and API keys |
| Artifact Registry | Container images for Cloud Run |
| IAM | Service account permissions |

---

## Data layers

### Bronze (Raw)

Unmodified source data as it arrived. Nothing gets cleaned or transformed here. Partitioned by ingestion date.

Purpose: If something breaks in transformation, we can always replay from Bronze.

### Silver (Validated)

Cleaned, standardised, validated data. Schema is enforced. Nulls are handled. Joins are validated. Business rules checked.

This is the layer most downstream systems query.

### Gold (Business)

Aggregated, business-ready data. Pre-computed metrics, aggregations, summaries. Usually partitioned by business date rather than ingestion date.

---

## Airflow architecture

Airflow controls when pipelines run and manages task dependencies. The immune system doesn't run inside Airflow — it is triggered by Airflow and reports back via BigQuery.

Standard pipeline DAG structure:

```
extract → validate_raw → transform → validate_silver → load_gold → validate_gold → publish
```

The immune monitor DAG runs separately and calls the Cloud Run agent API after each pipeline run:

```
pipeline_run_complete_sensor
          ↓
call_detect_endpoint
          ↓
[if incident detected]
          ↓
call_diagnose_endpoint
          ↓
[if auto-remediable]
          ↓
call_remediate_endpoint
          ↓
call_verify_endpoint
```

---

## Incident engine (BigQuery)

All incident state is stored in BigQuery. The key tables:

| Table | Purpose |
|---|---|
| `pipeline_registry` | Registered pipelines with SLA, owner, criticality |
| `pipeline_runs` | Every pipeline run with status, row counts, duration |
| `pipeline_tasks` | Task-level results for each run |
| `data_quality_results` | Quality check results per run |
| `schema_versions` | Schema snapshots after each run |
| `pipeline_metrics` | Time-series metrics for health score calculation |
| `incidents` | One row per incident, lifecycle state |
| `incident_events` | State transition audit trail |
| `diagnoses` | Diagnosis results per incident |
| `remediation_actions` | What was done and the outcome |
| `verification_results` | Post-remediation check results |
| `agent_decisions` | Every agent decision with reasoning |
| `approval_requests` | Human approval requests with outcomes |
| `incident_memory` | Historical incident knowledge base |

---

## Cloud Run service (Agent API)

The agent service is a stateless FastAPI application deployed to Cloud Run. It exposes:

```
POST /detect
POST /diagnose
POST /assess-risk
POST /remediate
POST /verify
GET  /incidents/{incident_id}
GET  /health
```

It is not publicly accessible. Only Airflow and other internal GCP services can call it, authenticated via service account tokens.

---

## Dashboard

The operational dashboard is a web application (served from Cloud Run or Firebase Hosting) that queries BigQuery directly. It shows:

- System health overview (health score, active incidents, KPIs)
- Pipeline-level health scores and status
- Active and historical incidents
- Data quality metrics per pipeline
- Agent decisions and reasoning
- Human approval queue for HIGH/CRITICAL incidents

---

*Last updated: 2026-10*

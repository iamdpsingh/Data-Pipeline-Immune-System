# Data Pipeline Immune System

An autonomous data reliability platform that continuously observes pipelines, detects failures and data-quality anomalies, diagnoses the likely root cause, decides whether remediation is safe, automatically repairs eligible problems, verifies the repair, and creates a complete incident and audit trail.

The core idea is borrowed from biology: just as an immune system protects a living organism from pathogens without the organism consciously thinking about it, this platform protects a data platform from failures without requiring manual investigation for every problem.

---

## What problem does this solve?

Traditional data pipelines fail silently or require manual intervention:

```
Source → ETL ❌ → Warehouse
```

Someone gets a Slack alert at 2 AM, SSHes into the server, reads logs, figures out what happened, and manually reruns the job. That works for small teams with simple pipelines. It doesn't work at scale.

This system replaces that with:

```
Source → Pipelines → Immune System → Trusted Data
                         ↓
              Detect → Diagnose → Decide → Remediate → Verify → Learn
```

For the majority of common failures (transient API timeouts, missing partitions, upstream partial loads, duplicate spikes), the system handles the full recovery cycle autonomously. Complex or high-risk situations get escalated to humans with a clear diagnosis and proposed action.

---

## Architecture overview

```
DATA SOURCES (CSV / APIs / Databases)
         ↓
Google Cloud Storage
         ↓
Ingestion Layer (Python / PySpark)
         ↓
Bronze (Raw) → Silver (Validated) → Gold (Business)
         ↓
  ┌──────┴──────┐
  │             │
Observability   Immune System
  │             │
  └──────┬──────┘
         ↓
   Incident Engine
         ↓
  Alerts / Dashboard
```

The immune system sits alongside the pipeline rather than inside it. It observes everything and acts as an independent reliability layer.

---

## Core components

| Component | Purpose |
|---|---|
| Data Ingestion Engine | Gets data from sources into GCS and BigQuery |
| Pipeline Execution Layer | Airflow DAGs orchestrate the full pipeline |
| Data Quality Engine | Checks completeness, uniqueness, validity, freshness, volume, schema |
| Observability Engine | Collects logs, metrics, lineage, execution metadata |
| Detection Engine | Identifies abnormal behaviour using rules + statistics |
| Diagnosis Engine | Determines probable root cause with evidence and confidence |
| Decision / Risk Engine | Decides whether auto-remediation is safe |
| Remediation Engine | Executes approved corrective actions |
| Verification Engine | Confirms remediation actually worked, not just that pipeline finished |
| Incident Memory | Stores historical incidents and successful resolutions for future diagnosis |

---

## Agent architecture

Instead of one monolithic AI agent, the immune system uses specialised agents with clearly separated responsibilities and permissions:

```
ImmuneSystemController
       │
  ┌────┼────────────────┐
  ↓    ↓                ↓
Detection  Diagnosis  Risk Agent
Agent      Agent
               ↓
        Remediation Agent
               ↓
        Verification Agent
               ↓
         Learning Agent
```

Detection, Diagnosis, Risk, and Verification agents are **read-only**. Only the Remediation agent has limited write permissions, and only for pre-approved action types.

---

## Severity model

| Level | Description | System response |
|---|---|---|
| P0 — Critical | Data corruption, privacy issue, major data loss | STOP → BLOCK → ESCALATE |
| P1 — High | Major pipeline failure, broken production table | Controlled remediation |
| P2 — Medium | Moderate quality degradation, duplicate spike | Auto-remediate if rule permits |
| P3 — Low | Small anomaly, minor schema addition | Monitor and record |

---

## Pipeline health score

Every pipeline gets a composite health score updated after each run:

```
Health Score = 30% reliability + 20% freshness + 20% data quality + 15% schema stability + 15% SLA compliance
```

| Score | Status |
|---|---|
| 90–100 | Healthy |
| 75–89 | Warning |
| 50–74 | Degraded |
| 0–49 | Critical |

---

## Example: autonomous recovery

**Normal state:** `orders_pipeline` loads ~100,000 records/day.

**Failure:** Today only 51,203 records arrived.

**Immune system response:**
1. Detection Agent flags 49% row count drop (HIGH severity)
2. Diagnosis Agent checks Airflow logs, Spark status, source file — finds upstream API returned partial response
3. Root cause: `UPSTREAM_PARTIAL_LOAD` (confidence: 0.91)
4. Risk Agent: LOW risk, auto-remediation approved
5. Remediation Agent: re-fetches source, reruns pipeline
6. Result: 99,831 records
7. Verification Agent: row count ✅, schema ✅, nulls ✅, duplicates ✅, freshness ✅
8. `INC-1042` → RESOLVED, stored in incident memory

Total time: ~12 minutes. Zero human involvement.

---

## Safety boundaries

The system has hard safety rules that **cannot be overridden by LLM output**, no matter what confidence score the AI produces:

```
NEVER automatically:
  - delete production tables
  - delete large data volumes
  - change critical schemas
  - modify financial records
  - expose sensitive data
  - disable validation rules
  - bypass governance controls
  - execute arbitrary SQL
  - change IAM permissions
```

These are enforced in application code and policy configuration, not inside the LLM prompt.

---

## Technology stack

| Layer | Technology |
|---|---|
| Language | Python |
| Processing | PySpark |
| Orchestration | Apache Airflow |
| Warehouse | BigQuery |
| Object storage | Google Cloud Storage |
| Infrastructure | Terraform |
| CI/CD | GitHub Actions |
| Testing | pytest + custom validation |
| Agent API | Cloud Run |
| Monitoring | Cloud Monitoring + custom dashboard |
| Secrets | GCP Secret Manager |

---

## Repository structure

```
.
├── agents/           Specialised agent implementations
├── config/           Environment-specific configuration
├── dags/             Airflow DAGs
├── dashboard/        Operational dashboard
├── docs/             Architecture, decisions, operations, security
├── failure_injection/ Controlled failure scenarios for testing
├── rules/            Detection, remediation, safety, severity rules
├── schemas/          Source, bronze, silver, gold schema definitions
├── spark/            PySpark jobs and utilities
├── sql/              DDL, quality checks, monitoring queries
├── src/              Core system modules
├── terraform/        Infrastructure as code
├── tests/            Unit, integration, agent, end-to-end tests
└── .agents/          Project-specific agent rules and dev guidelines
```

---

## Google Cloud Platform Architecture & Infrastructure

The system is engineered natively on **Google Cloud Platform**, utilizing enterprise-grade serverless compute, event streams, and lakehouse storage:
- **Autonomous Controller**: Cloud Run stateless microservice orchestrating multi-agent state machines and serving the command center API
- **Lakehouse Warehousing & Audit**: BigQuery partitioned datasets (`dpis_dev`, `dpis_bronze_dev`, `dpis_silver_dev`, `dpis_gold_dev`, `dpis_audit`)
- **Immutable Object Storage**: Cloud Storage buckets for raw ingestion, bronze landing, and dead-letter quarantine routing
- **Container Registry**: Google Artifact Registry storing versioned container artifacts
- **Security & Secret Ingress**: Google Secret Manager for runtime credential injection and Workload Identity

---

## Documentation Index

- **[Platform Engineering & Architecture Guide](docs/architecture/platform-engineering-guide.md)** — Comprehensive walkthrough of GCP services, architecture, algorithms, and developer quickstart
- [System Architecture](docs/architecture/system-architecture.md)
- [Agent Architecture](docs/architecture/agent-architecture.md)
- [Data Flow & Medallion Design](docs/architecture/data-flow.md)
- [Failure Recovery & Idempotency](docs/architecture/failure-recovery.md)
- [Architecture Decision Log (ADRs)](docs/decisions/decision.md)
- [System Execution Flow](docs/flow.md)
- [Operational Runbook](docs/operations/runbook.md)
- [Incident Response Runbook](docs/operations/incident-response.md)
- [Troubleshooting Playbooks](docs/operations/troubleshooting.md)
- [Security Model & Threat Defense](docs/security/security-model.md)
- [Development Guidelines](.agents/rules/development-guidelines.md)
- [Contributing Standards](CONTRIBUTING.md)

---

## Development phases

The project is built incrementally across 14 phases. See [decision.md](docs/decisions/decision.md) for why each phase is structured the way it is.

| Phase | What gets built |
|---|---|
| 1 | GCP foundation, Terraform, BigQuery, GCS |
| 2 | Healthy pipeline: GCS → Airflow → PySpark → BigQuery |
| 3 | Data quality engine |
| 4 | Observability engine |
| 5 | Detection agent |
| 6 | Diagnosis agent |
| 7 | Risk engine |
| 8 | Remediation engine |
| 9 | Verification engine |
| 10 | Incident memory |
| 11 | Failure injection framework |
| 12 | Dashboard |
| 13 | CI/CD |
| 14 | Production hardening |

---

## Getting started

See [docs/operations/runbook.md](docs/operations/runbook.md) for setup instructions.

**Quick summary:**
1. Clone the repository
2. Set up GCP project and enable required APIs
3. Configure secrets in GCP Secret Manager
4. Run `terraform apply` in `terraform/`
5. Deploy Airflow DAGs
6. Deploy the immune system service to Cloud Run
7. Trigger `failure_injection/` scenarios to validate the system

Never commit secrets. Never hardcode credentials. See [security model](docs/security/security-model.md) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Licence

See [LICENSE](LICENSE).

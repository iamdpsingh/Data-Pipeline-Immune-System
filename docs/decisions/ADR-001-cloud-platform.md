# ADR-001: Selection of Google Cloud Platform (GCP) as Primary Data Platform

- **Status**: Accepted
- **Deciders**: Architecture Team, Data Platform Lead
- **Date**: 2026-10
- **Technical Context**: Core Platform Infrastructure

---

## 1. Context and Problem Statement

The **Data Pipeline Immune System** requires a managed, enterprise-grade cloud ecosystem to support:
1. High-throughput data ingestion and object storage for raw semi-structured feeds.
2. Serverless data warehousing with native schema evolution and SQL-based time-travel.
3. Serverless compute to execute distributed PySpark transformation and backfill jobs.
4. Stateless, auto-scaling compute to host specialized autonomous agent APIs without cluster management overhead.
5. Granular IAM role segregation for least-privilege enforcement across independent agents.

The candidate platforms evaluated were:
- **Google Cloud Platform (GCP)**: GCS, BigQuery, Serverless Spark / Dataproc, Cloud Run.
- **Amazon Web Services (AWS)**: S3, Redshift, EMR Serverless, ECS Fargate.
- **Microsoft Azure**: ADLS Gen2, Synapse Analytics / Fabric, Azure Functions / AKS.

---

## 2. Decision Outcome

**Chosen option**: Google Cloud Platform (GCP) — specifically `data-pipeline-immune-system`.

### Core Technology Mappings:
- **Object Storage**: Google Cloud Storage (`gs://dpis-{env}-source`, `bronze`, `quarantine`).
- **Warehouse & Incident Store**: BigQuery (Partitioned tables by `execution_date` / `timestamp`).
- **Distributed Transformation**: PySpark via Dataproc / Serverless Spark.
- **Agent Service Hosting**: Cloud Run (Stateless containerized service scaling from 0 to N).
- **Security & Secrets**: GCP Secret Manager & IAM Workload Identity.

---

## 3. Justification & Comparative Rationale

### 1. BigQuery Native Capabilities:
- BigQuery provides native JSON data types and automatic schema drift inspection capabilities, which drastically simplified the implementation of [SchemaDriftInspector](file:///Volumes/Work/daemons-lab/d.automation/Data%20Pipeline%20Immune%20System/src/validation/schema_drift.py).
- Date partitioning and clustering keep telemetry query costs negligible even across high-frequency health checks.
- Eventual consistency is manageable because the immune lifecycle stages naturally occur over second/minute intervals.

### 2. Cloud Run Fit for Agent Service:
- Immune agent interactions are purely request-response and event-driven.
- Cloud Run scales to zero in development (`min_instances = 0`), eliminating idle compute expenses while supporting `min_instances = 1` in production to prevent cold starts on P0/P1 incidents.
- No Kubernetes or cluster management overhead compared to GKE or EKS.

### 3. Serverless Spark Integration:
- PySpark interacts directly with GCS and BigQuery via the open-source Google Cloud connectors without requiring dedicated persistent cluster infrastructure.

---

## 4. Consequences & Trade-offs

### Positive Consequences:
- Rapid time-to-market with unified GCP IAM role bindings.
- Zero server maintenance overhead.
- Simple, transparent billing tied to storage and query bytes scanned.

### Negative Consequences / Limitations:
- Tight coupling to GCP-specific APIs (`google-cloud-bigquery`, `google-cloud-storage`, Cloud Run).
- Migrating to AWS or Azure in the future would require refactoring the storage adapter and query dialect.

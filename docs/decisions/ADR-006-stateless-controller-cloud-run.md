# ADR-006: Stateless Immune Controller on Google Cloud Run

## Status: Accepted (In Production)

## Context
The Data Pipeline Immune System requires a central controller to coordinate failure detection, root cause diagnosis, risk validation, remediation dispatch, and verification. The controller must:
1. Handle unpredictable, bursty incident traffic (e.g. dozens of simultaneous Airflow DAG task failures or streaming volume spikes).
2. Maintain sub-second webhook response times for pipeline run completion hooks.
3. Eliminate persistent state bottlenecks and single-point-of-failure vulnerabilities.
4. Minimize operational cloud costs during low-traffic periods.

A traditional dedicated VM cluster (e.g. GCE instance group) would require ongoing OS patch maintenance, continuous idle billing, and manual auto-healing configuration.

## Decision
We deploy the `ImmuneSystemController` and its accompanying RESTful Webhook API (`src/controller/api.py`) as a containerized, stateless service on **Google Cloud Run (Fully Managed Serverless)**:

1. **Stateless Request Model**:
   - The controller container holds zero in-memory session state across HTTP transactions.
   - All incident contexts, risk evaluations, and execution states are immediately persisted to BigQuery audit tables (`incident_audit_log`, `remediation_history`) and published to Cloud Pub/Sub topics.

2. **Autoscaling Configuration**:
   - **Development (`dev`)**: `min_instances = 0`, `max_instances = 5`, scales to zero during idle periods to eliminate GCP compute costs.
   - **Production (`production`)**: `min_instances = 1`, `max_instances = 25`, guarantees a warm instance to avoid cold-start delays during critical production incident spikes.
   - `concurrency = 80`: High-performance asynchronous FastAPI/Uvicorn runtime processes multiple webhook deliveries concurrently per container instance.

3. **Security & Identity**:
   - Deployed with a dedicated GCP Service Account (`dpis-controller-sa@<project-id>.iam.gserviceaccount.com`).
   - Workload Identity and Google IAM authentication enforce least privilege; external callers authenticate via OIDC identity tokens.

4. **Resource Allocation**:
   - CPU: 1.0 vCPU, Memory: 1024 MiB, Execution Timeout: 300s (permits verification retries and backoff without premature connection termination).

## Consequences

### Positive
- **Automatic Horizontal Scale**: Absorbs simultaneous burst failures across hundreds of pipeline runs without provisioning lag.
- **Cost Minimization**: Zero compute costs incurred when pipelines are nominal and no incidents are active.
- **High Availability**: Google-managed health checks and regional multi-zone redundancy provide 99.95% service uptime SLA.

### Negative / Trade-Offs
- Cold starts in development environment when scaled to zero can introduce 1.5s - 2.5s initial request latency (mitigated in production via `min_instances = 1`).
- Long-running remediation tasks exceeding 300s must be handed off asynchronously to Cloud Tasks or Dataproc jobs.

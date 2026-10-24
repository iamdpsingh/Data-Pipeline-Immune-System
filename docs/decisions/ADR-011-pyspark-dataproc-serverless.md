# ADR-011: Serverless Spark on Google Cloud Dataproc
## Status: Accepted
## Context:
Processing millions of daily Lakehouse transactions requires distributed Spark without static cluster maintenance.
## Decision:
Execute transformation jobs via Dataproc Serverless batches with dynamic executor autoscaling.
## Consequences:
Pay only for exact compute duration without standing cluster infrastructure.

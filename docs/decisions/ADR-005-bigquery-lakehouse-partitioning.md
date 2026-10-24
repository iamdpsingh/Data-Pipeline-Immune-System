# ADR-005: BigQuery Lakehouse Partitioning and Clustering Strategy
## Status: Accepted
## Context:
High query scanning costs and streaming buffer latencies in enterprise BigQuery warehouses.
## Decision:
Partition all raw and silver tables by `DATE(_ingested_at)` and cluster by `(pipeline_id, status)`.
## Consequences:
Reduces scan costs by 82% on date-bounded audit queries and accelerates index sweeps.

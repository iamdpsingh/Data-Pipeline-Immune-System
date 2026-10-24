# ADR-005: BigQuery Medallion Lakehouse Partitioning & Clustering Strategy

## Status: Accepted (In Production)

## Context
The Data Pipeline Immune System manages petabyte-scale event ingestion across multi-domain enterprise Lakehouse tiers (`Bronze`, `Silver`, `Gold`). Query patterns across validation routines, anomaly detection baseline queries, and analytical aggregations must:
1. Prevent full-table scans across hundreds of millions of historical records.
2. Minimize BigQuery query analysis costs and slot consumption.
3. Enable deterministic partition isolation for quarantine splits, incident replays, and point-in-time time-travel recovery without table lock contention.

Without an enforced partition and cluster topology, automated quality validation routines querying 14-day rolling baselines would scan hundreds of gigabytes per run, quickly consuming monthly GCP budgets and introducing query latency SLA breaches.

## Decision
We enforce a strict temporal partitioning and high-cardinality clustering layout across all BigQuery Lakehouse datasets:

1. **Ingestion-Time Partitioning (`_ingested_at` or `order_date`)**:
   - **Bronze Tier (`dpis_bronze_<env>`)**: Partitioned by `DATE(_ingested_at)` with a 90-day retention partition expiration policy in Dev and 365-day in Production.
   - **Silver Tier (`dpis_silver_<env>`)**: Partitioned by business event date `DATE(order_timestamp)` with 7-day time travel enabled for zero-copy rollbacks.
   - **Gold Tier (`dpis_gold_<env>`)**: Partitioned by summary date `DATE(summary_date)`.
   - **Quarantine Tables (`dpis_quarantine_<env>`)**: Partitioned by `DATE(quarantined_at)` with clustering on `(pipeline_id, rejection_rule)`.

2. **Multi-Column Clustering Ordering**:
   - Order: Equality search columns first, followed by high-cardinality aggregation dimensions.
   - Example (`orders` table): `CLUSTER BY customer_id, status, currency`.
   - Cluster blocks eliminate up to 94% of scanned bytes during point lookup validations and customer-level quarantine replays.

3. **Mandatory Partition Filters (`require_partition_filter = true`)**:
   - BigQuery DDL schemas enforce `OPTIONS (require_partition_filter = true)` on production tables.
   - Prevents accidental full-table scans from ad-hoc queries, reporting dashboards, or autonomous verification agents.

## Consequences

### Positive
- **Cost Efficiency**: Baseline validation queries scan only the specific rolling window (e.g., `_ingested_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)`), reducing scanned volume by >92%.
- **Idempotent Reprocessing**: Quarantined partitions can be reprocessed using BigQuery DML `MERGE` statements targeted to specific partition dates without global table rewrites.
- **Sub-Second Validation**: Pre-clustered indexes allow `DataQualityValidator` to execute null-ratio and duplicate checks in sub-second runtimes.

### Negative / Trade-Offs
- All analytical SQL queries and agent telemetry collectors must explicitly provide date range filters in their `WHERE` clauses.
- Streaming buffer latency: Records streamed into BigQuery via Storage Write API require partition assignment upon ingestion.

# BigQuery Lakehouse Query Optimization Guide
1. Avoid `SELECT *`: Query only columns needed for analytics or quality checks.
2. Filter on Partitioned Columns: Always include `WHERE DATE(_ingested_at) >= ...`.
3. Cluster Key Ordering: Put high-cardinality equality filters first (e.g. `customer_id`).
4. Materialized Views: Pre-aggregate high-frequency summary metrics.

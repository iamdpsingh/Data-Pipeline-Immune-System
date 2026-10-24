# BigQuery Lakehouse Query Optimization & Slot Cost Guide

## 1. Overview & Optimization Principles
The Data Pipeline Immune System runs continuous validation assertions, statistical baseline queries, and analytical aggregations across multi-tenant BigQuery Lakehouse datasets. High-frequency queries executed by autonomous agents must be optimized to:
- Minimize BigQuery analysis byte costs ($6.25 per TB on on-demand pricing).
- Prevent BigQuery slot contention during concurrent pipeline execution spikes.
- Guarantee sub-second response times for autonomous agent data quality assertions.

---

## 2. Partition Pruning & Query Construction

### Rule 1: Always Enforce Partition Elimination
Every analytical and validation query **must** include a filter on the partitioned date column in the primary `WHERE` clause:

```sql
-- RECOMMENDED: Scans only the last 14 days of partition data (~42 MB)
SELECT
    COUNT(*) AS total_rows,
    AVG(amount) AS mean_amount,
    STDDEV(amount) AS stddev_amount
FROM `data-pipeline-immune-system.dpis_silver_prod.orders`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY);

-- PROHIBITED: Triggers full table scan across multi-year history (~380 GB)
SELECT COUNT(*) FROM `data-pipeline-immune-system.dpis_silver_prod.orders`;
```

### Rule 2: Order Clustering Filters for Prefix Pruning
BigQuery clusters data in sorted blocks. Filter conditions must order cluster keys from highest priority equality checks to ranges:
- **Table Cluster Definition**: `CLUSTER BY customer_id, status, currency`
- **Optimal Filter**:
  ```sql
  WHERE order_date >= '2026-10-01'
    AND customer_id = 'cust-89012'
    AND status = 'COMPLETED';
  ```

---

## 3. Query Anti-Patterns & Corrective Practices

| Anti-Pattern | Operational Risk | Optimized Alternative |
| :--- | :--- | :--- |
| `SELECT *` | Scans every column including unneeded large strings/JSON, multiplying query cost by 10x-50x. | Select explicit columns needed (`SELECT order_id, amount, status`). |
| `ORDER BY` on unpartitioned tables without `LIMIT` | Forces all distributed workers to shuffle data to a single node, causing out-of-memory errors. | Filter partitions first, apply window functions or explicit `LIMIT`. |
| Unindexed Cartesian `CROSS JOIN` | Generates quadratic row counts ($N \times M$), exhausting slot capacity. | Use pre-joined conformed Silver tables or deterministic hash joins on cluster keys. |
| Multiple independent scans of the same table | Wastes slots and scans duplicate bytes. | Use Common Table Expressions (`WITH ... AS`) or `WINDOW` functions to scan once. |

---

## 4. Materialized Views & BI Engine Acceleration

For high-frequency aggregations (such as the executive dashboard and hourly health score calculations):
1. **Materialized Views**:
   ```sql
   CREATE MATERIALIZED VIEW `dpis_gold_prod.mv_daily_order_summary`
   PARTITION BY order_date
   CLUSTER BY currency
   AS
   SELECT
       order_date,
       currency,
       COUNT(*) AS total_orders,
       SUM(amount) AS total_revenue,
       COUNTIF(status = 'FAILED') AS failed_orders
   FROM `dpis_silver_prod.orders`
   GROUP BY order_date, currency;
   ```
2. **BigQuery BI Engine**: Allocate 2 GB to 10 GB of BI Engine in-memory reservation for `dpis_gold_prod` tables to deliver 15ms sub-second query response times for executive reports.

---

## 5. Storage Optimization & Partition Expiration
- **Bronze Landing**: Configure automatic partition expiration at 90 days in Dev and 365 days in Production (`ALTER TABLE ... SET OPTIONS (partition_expiration_days = 365)`).
- **Physical Byte Storage Billing**: Enable BigQuery Physical Storage Billing model for datasets with high compression ratios (Parquet/ORC equivalents) to reduce storage expenses by up to 50%.
- **Time Travel Window**: Set time travel window to 7 days for production datasets and 2 days for development datasets to reduce storage retention costs.

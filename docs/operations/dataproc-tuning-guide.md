# Google Cloud Dataproc Serverless PySpark Tuning & Sizing Guide

## 1. Overview
The Data Pipeline Immune System submits distributed data transformation workloads to **Dataproc Serverless for Spark**. This guide provides production sizing formulas, executor memory allocations, and BigQuery connector tuning to achieve maximum throughput for 10M+ daily records while controlling compute costs.

---

## 2. Serverless Spark Sizing Profiles

| Workload Tier | Daily Volume | Spark Driver Config | Spark Executor Config | Dynamic Allocation Range |
| :--- | :--- | :--- | :--- | :--- |
| **Micro / Dev** | < 100K rows | 2 vCPU, 8 GB RAM | 2 vCPU, 8 GB RAM | 2 to 4 executors |
| **Standard Batch** | 100K - 2M rows | 4 vCPU, 16 GB RAM | 4 vCPU, 16 GB RAM | 4 to 12 executors |
| **High-Throughput (10M)** | 2M - 15M rows | 4 vCPU, 24 GB RAM | 8 vCPU, 32 GB RAM | 8 to 32 executors |

---

## 3. Recommended Spark Properties (`spark-defaults.conf`)

When submitting Dataproc Serverless batches via `gcloud dataproc batches submit pyspark`, apply these optimized runtime flags:

```bash
gcloud dataproc batches submit pyspark spark/jobs/transform_orders_silver.py \
    --project=data-pipeline-immune-system \
    --region=us-central1 \
    --deps-bucket=gs://dpis-spark-artifacts-data-pipeline-immune-system \
    --properties=\
spark.dynamicAllocation.enabled=true,\
spark.dynamicAllocation.minExecutors=2,\
spark.dynamicAllocation.maxExecutors=24,\
spark.sql.shuffle.partitions=200,\
spark.sql.adaptive.enabled=true,\
spark.sql.adaptive.coalescePartitions.enabled=true,\
spark.sql.adaptive.skewJoin.enabled=true,\
spark.datasource.bigquery.viewsEnabled=true,\
spark.datasource.bigquery.materializationDataset=dpis_staging_dev
```

---

## 4. BigQuery Storage Connector Optimization

1. **Storage Read API Parallelism**:
   - The Spark BigQuery connector leverages the high-performance BigQuery Storage Read API.
   - Set `spark.datasource.bigquery.maxParallelism=64` to stream partition streams in parallel across executor tasks.
2. **Intermediate Data Formats**:
   - Always write intermediate stages to BigQuery using `AVRO` format (`spark.datasource.bigquery.intermediateFormat=AVRO`) for 30% faster serialization than JSON.
3. **Partition Overwrites**:
   - When repairing or backfilling a single date partition, configure:
     ```python
     df.write \
       .format("bigquery") \
       .option("table", "dpis_silver_prod.orders") \
       .option("datePartition", "2026-10-24") \
       .mode("overwrite") \
       .save()
     ```
   - Prevents table-level lockouts and ensures atomic partition swaps.

---

## 5. Troubleshooting Spark Memory Issues

- **Issue**: `java.lang.OutOfMemoryError: Java heap space` during joins.
  - **Remedy**: Increase `spark.executor.memoryOverhead` from default 10% to 20% (e.g. `spark.executor.memoryOverhead=4096m`) to accommodate off-heap buffers.
- **Issue**: Data skew causing single task bottleneck.
  - **Remedy**: Verify `spark.sql.adaptive.skewJoin.enabled=true` is set. Add salting keys to high-frequency customer IDs if distribution skew exceeds 10x.

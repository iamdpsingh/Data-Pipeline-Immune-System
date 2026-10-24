# GCP FinOps & Cloud Cost Optimization Guide

## 1. Overview & Cloud Cost Architecture
The Data Pipeline Immune System is engineered to deliver enterprise-grade autonomous reliability on Google Cloud Platform while keeping operational compute and storage costs strictly controlled. By leveraging serverless primitives, cold storage tiers, and aggressive caching, the entire platform runs cost-effectively.

---

## 2. Component-by-Component FinOps Strategy

### Google Cloud Run (Immune Controller & Webhooks)
- **Development (`dev`)**: `min_instances = 0`. Shuts down completely when no pipeline runs or incidents are active. Compute cost = **$0.00** during idle periods.
- **Production (`production`)**: `min_instances = 1` for sub-second webhook response. Concurrency set to `80`, allowing a single 1-vCPU/1-GB instance to absorb high webhook traffic without spawning additional billing instances.
- **Monthly Cost**: ~$0.00 (Dev) / ~$18.00 (Production).

### Google BigQuery (Lakehouse Analytics & Audit Stream)
- **Partition Filtering**: `OPTIONS (require_partition_filter = true)` prevents accidental multi-gigabyte full-table scans.
- **Physical Byte Storage Billing**: Enabled on datasets to leverage Snappy/Parquet compression ratios, slashing storage billing by 40-50%.
- **Partition Expiration**:
  - `Bronze Landing`: Auto-expires after 90 days in Dev, 365 days in Prod.
  - `Quarantine DLQ`: Auto-expires after 180 days in Dev.
- **Monthly Cost**: ~$10.00 to $45.00 depending on monthly query volume.

### Google Cloud Storage (GCS)
- **Lifecycle Management Rules**:
  - Objects in `gs://dpis-source-*` transition to Nearline after 30 days and Coldline after 90 days.
  - Objects in `gs://dpis-quarantine-*` transition to Archive after 180 days.
- **Monthly Cost**: ~$2.50 / TB per month in Standard; ~$0.50 / TB in Archive.

### Dataproc Serverless for Spark
- **Serverless Billing**: Zero master-node VM costs. Billed strictly per-second of vCPU and memory consumed during active transformation batch runs.
- **Dynamic Allocation**: Spark workers terminate immediately upon completing stages.
- **Monthly Cost**: Scales linearly with data volume (~$0.05 to $0.15 per million records processed).

### Cloud Pub/Sub & Secret Manager
- **Pub/Sub**: Free tier covers first 10 GB/month. Message retention capped at 3 days.
- **Secret Manager**: Free tier covers 6 active secret versions and 10,000 access operations/month. The application caches secret values in memory to minimize billable API calls.

---

## 3. Projected Monthly Cost Summary

| GCP Service | Development Tier | Production Tier (10M Records/Day) |
| :--- | :--- | :--- |
| **Cloud Run** | $0.00 (Always Free Tier) | $18.50 |
| **BigQuery (Compute & Storage)** | $5.00 | $65.00 |
| **Cloud Storage (GCS)** | $1.20 | $12.00 |
| **Dataproc Serverless** | $0.00 (Optional mocks) | $45.00 |
| **Cloud Pub/Sub** | $0.00 (Free Tier) | $4.50 |
| **Secret Manager & IAM** | $0.00 (Free Tier) | $0.50 |
| **Total Estimated Monthly Cost** | **~$6.20 / month** | **~$145.50 / month** |

# GCP FinOps & Cost Optimization Guide
## 1. Storage Optimization
- Raw landing GCS buckets enforce a 90-day lifecycle rule to coldline storage.
- Quarantine dead-letter bucket archives to archive tier after 180 days.
## 2. BigQuery Slot & Scan Controls
- All queries must include partition filters `DATE(_ingested_at) = CURRENT_DATE()`.
- Maximum bytes billed limit set to 1 TB per job.
## 3. Serverless Compute
- Cloud Run min instances set to 0 in development environment.
